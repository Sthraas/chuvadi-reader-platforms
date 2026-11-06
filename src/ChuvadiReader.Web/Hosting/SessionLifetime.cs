using ChuvadiReader.Web.Files;
using Microsoft.AspNetCore.Components.Server.Circuits;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Ends a session cleanly: when the Blazor circuit closes (tab closed and the reconnect window passed,
/// or sign-out), its tickets are forgotten and its folder is deleted. The scoped services' own
/// <c>Dispose</c> does the same as a second line of defence.
/// </summary>
public sealed class SessionLifetime : CircuitHandler
{
    private readonly SessionSpace _space;
    private readonly TransferRegistry _registry;

    public SessionLifetime(SessionSpace space, TransferRegistry registry)
    {
        _space = space;
        _registry = registry;
    }

    public override Task OnCircuitClosedAsync(Circuit circuit, CancellationToken cancellationToken)
    {
        _registry.ForgetSession(_space.SessionId);
        _space.Delete();
        return Task.CompletedTask;
    }
}

/// <summary>Start-up sweep of session folders a previous run left behind, and periodic ticket pruning.</summary>
public sealed class PortalHousekeeping : BackgroundService
{
    private readonly TransferRegistry _registry;
    private readonly Microsoft.Extensions.Options.IOptions<PortalOptions> _options;
    private readonly ILogger<PortalHousekeeping> _log;

    public PortalHousekeeping(TransferRegistry registry, Microsoft.Extensions.Options.IOptions<PortalOptions> options, ILogger<PortalHousekeeping> log)
    {
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
            }
        }
        catch (OperationCanceledException)
        {
        }
    }
}
