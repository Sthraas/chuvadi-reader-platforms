using ChuvadiReader.Web.Files;
using Microsoft.AspNetCore.Components.Server.Circuits;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Starts and ends a connection (Blazor circuit). When it closes (a reload, the tab closed and the reconnect
/// window passed, or sign-out), its tickets are forgotten and the documents it had open are closed, so their
/// memory and page images are freed at once (WT-22). The session's files and its tab list stay (D-174): the
/// next connection of the same sign-in shows the same tabs again.
/// </summary>
public sealed class SessionLifetime : CircuitHandler
{
    private readonly SessionSpace _space;
    private readonly TransferRegistry _registry;
    private readonly Platform.WebAccount _account;
    private readonly Workers.CircuitCounter _circuits;
    private readonly ChuvadiReader.Core.Reader.TabsService _tabs;
    private readonly ILogger<SessionLifetime> _log;

    public SessionLifetime(SessionSpace space, TransferRegistry registry, Platform.WebAccount account, Workers.CircuitCounter circuits,
        ChuvadiReader.Core.Reader.TabsService tabs, ILogger<SessionLifetime> log)
    {
        _tabs = tabs;
        _log = log;
        _space = space;
        _registry = registry;
        _account = account;
        _circuits = circuits;
    }

    /// <summary>A session starts: its folders exist before any Reader service asks for a path, and the
    /// signed-in person is known.</summary>
    public override async Task OnCircuitOpenedAsync(Circuit circuit, CancellationToken cancellationToken)
    {
        _circuits.Opened();
        await _space.EnsureAsync(cancellationToken).ConfigureAwait(false);
        await _account.LoadAsync().ConfigureAwait(false);
    }

    public override Task OnCircuitClosedAsync(Circuit circuit, CancellationToken cancellationToken)
    {
        _circuits.Closed();
        _registry.ForgetSession(_space.ConnectionId);
        var closed = CloseDocuments(_tabs);
        _log.LogInformation("Connection {Connection} closed; {Documents} open document(s) closed", _space.ConnectionId[..8], closed);
        return Task.CompletedTask;
    }

    /// <summary>Closes the documents a connection has open, without touching the session's saved tab list
    /// (closing them through the tab strip would save "no tabs", and a reload would then find nothing).</summary>
    internal static int CloseDocuments(ChuvadiReader.Core.Reader.TabsService tabs)
    {
        var closed = 0;
        foreach (var tab in tabs.Tabs.ToArray())
        {
            if (tab.Session is { } open)
            {
                tab.Session = null;
                open.Dispose();
                closed++;
            }
        }

        return closed;
    }
}

/// <summary>Start-up sweep of session folders a previous run left behind, and periodic ticket pruning.</summary>
public sealed class PortalHousekeeping : BackgroundService
{
    private readonly TransferRegistry _registry;
    private readonly Microsoft.Extensions.Options.IOptions<PortalOptions> _options;
    private readonly ILogger<PortalHousekeeping> _log;
    private readonly SessionStates? _sessions;

    public PortalHousekeeping(TransferRegistry registry, Microsoft.Extensions.Options.IOptions<PortalOptions> options, ILogger<PortalHousekeeping> log,
        SessionStates? sessions = null)
    {
        _sessions = sessions;
        _registry = registry;
        _options = options;
        _log = log;
    }

    public override Task StartAsync(CancellationToken cancellationToken)
    {
        // Every session of a previous run is over: its circuits died with the process.
        var removed = SpaceLayout.SweepStaleSessions(_options.Value.DataRoot, TimeSpan.Zero, _log);
        if (removed > 0)
        {
            _log.LogInformation("Removed {Count} session folder(s) left by a previous run", removed);
        }

        return base.StartAsync(cancellationToken);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(1));
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken).ConfigureAwait(false))
            {
                _registry.Prune();
                // A safety net behind the session clock: a session nobody is connected to, well past the idle limit.
                _sessions?.EndAbandoned(_options.Value.IdleTimeout + TimeSpan.FromMinutes(5));
            }
        }
        catch (OperationCanceledException)
        {
        }
    }
}
