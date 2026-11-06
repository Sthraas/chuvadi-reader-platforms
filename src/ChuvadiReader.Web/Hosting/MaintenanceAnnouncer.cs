using System.Globalization;
using ChuvadiReader.Web.Auth;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Announces a planned restart in advance (updates at quiet hours, with a banner first). The operator
/// writes the restart time into <c>Portal:MaintenanceNoticeFile</c>: line 1 is an ISO 8601 date-time with
/// its offset (e.g. <c>2026-11-08T22:00+05:30</c>), and an optional line 2 replaces the standard text.
/// Every open tab shows the banner until the time passes or the file is deleted. Runs in the single
/// process or the gateway; the gateway passes it to every worker.
/// </summary>
public sealed class MaintenanceAnnouncer : BackgroundService
{
    private readonly ITabControl _tabs;
    private readonly PortalOptions _options;
    private readonly TimeProvider _time;
    private readonly ILogger<MaintenanceAnnouncer> _log;
    private MaintenanceNotice? _current;
    private string? _lastProblem;

    public MaintenanceAnnouncer(ITabControl tabs, IOptions<PortalOptions> options, TimeProvider time, ILogger<MaintenanceAnnouncer> log)
    {
        _tabs = tabs;
        _options = options.Value;
        _time = time;
        _log = log;
    }

    /// <summary>Reads the file and announces any change. Public for tests.</summary>
    public async Task CheckAsync()
    {
        var notice = Read(_options.MaintenanceNoticeFile, _time.GetUtcNow(), out var problem);
        if (problem is not null && problem != _lastProblem)
        {
            _log.LogWarning("Maintenance notice file ignored: {Problem}", problem);
        }

        _lastProblem = problem;
        if (notice != _current)
        {
            _current = notice;
            if (notice is not null)
            {
                _log.LogInformation("Announcing a restart at {At:O}", notice.At);
            }

            await _tabs.AnnounceAsync(notice).ConfigureAwait(false);
        }
    }

    /// <summary>The notice in the file, or null (no file, empty, or the time has passed).</summary>
    internal static MaintenanceNotice? Read(string? path, DateTimeOffset now, out string? problem)
    {
        problem = null;
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            return null;
        }

        string[] lines;
        try
        {
            lines = File.ReadLines(path).Take(2).Select(l => l.Trim()).ToArray();
        }
        catch (IOException ex)
        {
            problem = ex.Message;
            return null;
        }

        if (lines.Length == 0 || lines[0].Length == 0)
        {
            return null;
        }

        if (!DateTimeOffset.TryParse(lines[0], CultureInfo.InvariantCulture, DateTimeStyles.None, out var at) || !HasOffset(lines[0]))
        {
            problem = $"line 1 must be a date and time with its offset, e.g. 2026-11-08T22:00+05:30 (found \"{lines[0]}\")";
            return null;
        }

        if (at <= now)
        {
            return null;
        }

        var message = lines.Length > 1 && lines[1].Length > 0 ? lines[1][..Math.Min(lines[1].Length, 300)] : null;
        return new MaintenanceNotice(at, message);
    }

    /// <summary>The time must say its zone: "22:00" alone would be read in the server's zone (UTC on E2E).</summary>
    private static bool HasOffset(string s) => s.EndsWith('Z') || s.EndsWith('z')
        || s.Length > 6 && (s[^6] is '+' or '-') && s[^3] == ':';

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (string.IsNullOrWhiteSpace(_options.MaintenanceNoticeFile))
        {
            return;
        }

        using var timer = new PeriodicTimer(_options.ExpiryCheckInterval, _time);
        try
        {
            do
            {
                try
                {
                    await CheckAsync().ConfigureAwait(false);
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    _log.LogError(ex, "Maintenance notice check failed");
                }
            }
            while (await timer.WaitForNextTickAsync(stoppingToken).ConfigureAwait(false));
        }
        catch (OperationCanceledException)
        {
        }
    }
}
