using System.Collections.Concurrent;
using System.Globalization;
using System.Security.Claims;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// Session expiry (D-30): a sign-in ends after 30 minutes with nothing done, or 8 hours after it began,
/// whichever comes first. Five minutes before, every open tab of it shows a warning that offers to
/// download the open work; anything the person does takes the idle warning down. When the time is
/// up the sign-in is revoked (its cookie stops working) and its tabs are ended (files deleted).
/// Runs where the sign-in cookie lives: the single portal process, or the gateway. Singleton.
/// </summary>
public sealed class SessionClock
{
    /// <summary>Claim with the portal sign-in time (Unix seconds); the 8-hour limit counts from it.</summary>
    public const string SignedInClaim = "chvd_signin";

    private readonly ConcurrentDictionary<string, Entry> _entries = new(StringComparer.Ordinal);
    private readonly TimeProvider _time;
    private readonly PortalSessions _sessions;
    private readonly ITabControl _tabs;
    private readonly PortalOptions _portal;
    private readonly TimeSpan _absolute;
    private readonly ILogger<SessionClock> _log;

    public SessionClock(TimeProvider time, PortalSessions sessions, ITabControl tabs, IOptions<PortalOptions> portal,
        IOptions<SangamOptions> sangam, ILogger<SessionClock> log)
    {
        _time = time;
        _sessions = sessions;
        _tabs = tabs;
        _portal = portal.Value;
        _absolute = sangam.Value.AbsoluteSessionLifetime;
        _log = log;
    }

    private sealed class Entry(string sub, string? sid, DateTimeOffset start, DateTimeOffset last)
    {
        public string Sub { get; } = sub;
        public string? Sid { get; } = sid;
        public DateTimeOffset Start { get; } = start;
        public DateTimeOffset Last { get; set; } = last;
        public ExpiryNotice? Shown { get; set; }
    }

    public int Count => _entries.Count;

    /// <summary>The person did something (a page load, a file transfer, input in the page).</summary>
    public void Touch(ClaimsPrincipal user)
    {
        var sub = user.FindFirst("sub")?.Value;
        if (sub is null)
        {
            return;
        }

        var sid = user.FindFirst("sid")?.Value;
        var now = _time.GetUtcNow();
        var start = long.TryParse(user.FindFirst(SignedInClaim)?.Value, NumberStyles.None, CultureInfo.InvariantCulture, out var unix)
            ? DateTimeOffset.FromUnixTimeSeconds(unix)
            : now;
        var entry = _entries.GetOrAdd(Key(sub, sid), _ => new Entry(sub, sid, start, now));
        lock (entry)
        {
            entry.Last = now;
        }
    }

    /// <summary>When the sign-in ends if nothing more happens, or null when it isn't tracked.</summary>
    public (DateTimeOffset EndsAt, ExpiryReason Reason)? EndOf(string sub, string? sid)
        => _entries.TryGetValue(Key(sub, sid), out var e) ? Due(e) : null;

    /// <summary>One pass: warn, take warnings down, end what is due. Run every few seconds.</summary>
    public async Task TickAsync()
    {
        var now = _time.GetUtcNow();
        foreach (var (key, e) in _entries)
        {
            if (_sessions.IsRevoked(e.Sub, e.Sid, e.Start))
            {
                _entries.TryRemove(key, out _); // signed out elsewhere; its tabs were ended there
                continue;
            }

            (DateTimeOffset EndsAt, ExpiryReason Reason) due;
            ExpiryNotice? shown;
            lock (e)
            {
                due = Due(e);
                shown = e.Shown;
            }

            if (now >= due.EndsAt)
            {
                _entries.TryRemove(key, out _);
                var ended = await _sessions.RevokeAsync(e.Sub, e.Sid).ConfigureAwait(false);
                _log.LogInformation("Session ended ({Reason}); {Count} open tab(s) closed", due.Reason, ended);
                continue;
            }

            var notice = now >= due.EndsAt - _portal.ExpiryWarning ? new ExpiryNotice(due.EndsAt, due.Reason) : null;
            if (notice != shown)
            {
                lock (e)
                {
                    e.Shown = notice;
                }

                await _tabs.NoticeAsync(e.Sub, e.Sid, notice).ConfigureAwait(false);
            }
        }
    }

    private (DateTimeOffset EndsAt, ExpiryReason Reason) Due(Entry e)
    {
        var idle = e.Last + _portal.IdleTimeout;
        var absolute = e.Start + _absolute;
        return idle <= absolute ? (idle, ExpiryReason.Idle) : (absolute, ExpiryReason.Absolute);
    }

    private static string Key(string sub, string? sid) => sid ?? "sub:" + sub;
}

/// <summary>Runs <see cref="SessionClock.TickAsync"/> on a timer.</summary>
public sealed class SessionClockService : BackgroundService
{
    private readonly SessionClock _clock;
    private readonly PortalOptions _options;
    private readonly TimeProvider _time;
    private readonly ILogger<SessionClockService> _log;

    public SessionClockService(SessionClock clock, IOptions<PortalOptions> options, TimeProvider time, ILogger<SessionClockService> log)
    {
        _clock = clock;
        _options = options.Value;
        _time = time;
        _log = log;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(_options.ExpiryCheckInterval, _time);
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken).ConfigureAwait(false))
            {
                try
                {
                    await _clock.TickAsync().ConfigureAwait(false);
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    _log.LogError(ex, "Session expiry pass failed");
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
    }
}

/// <summary>
/// Counts a signed-in person's requests as activity: page loads, file transfers and the page's own
/// input reports (<c>POST /portal/activity</c>). Not the circuit's WebSocket, whose keep-alive pings
/// would keep an abandoned tab alive forever, and not static files.
/// </summary>
public static class ActivityTracking
{
    public const string ActivityPath = "/portal/activity";

    public static IApplicationBuilder UseActivityTracking(this IApplicationBuilder app)
        => app.Use(async (http, next) =>
        {
            if (http.User.Identity?.IsAuthenticated == true && CountsAsActivity(http.Request.Path))
            {
                http.RequestServices.GetRequiredService<SessionClock>().Touch(http.User);
            }

            await next(http).ConfigureAwait(false);
        });

    internal static bool CountsAsActivity(PathString path)
        => !(path.StartsWithSegments("/_blazor") || path.StartsWithSegments("/_framework") || path.StartsWithSegments("/_content")
             || path.StartsWithSegments("/css") || path.StartsWithSegments("/js") || path.StartsWithSegments("/favicon.ico")
             || path.StartsWithSegments("/.well-known") || path.StartsWithSegments("/_chvd")); // page images are fetched by themselves

    /// <summary>The page reports input (throttled to once a minute). The request itself is the activity.</summary>
    public static IEndpointRouteBuilder MapActivity(this IEndpointRouteBuilder app)
    {
        app.MapPost(ActivityPath, (HttpContext http) =>
            !Files.FileEndpoints.SameOrigin(http) || http.Request.Headers["X-Chvd-Activity"] != "1"
                ? Results.StatusCode(StatusCodes.Status403Forbidden)
                : Results.NoContent()).RequireAuthorization().DisableAntiforgery();
        return app;
    }
}
