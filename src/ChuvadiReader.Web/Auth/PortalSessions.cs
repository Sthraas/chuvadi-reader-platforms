using System.Collections.Concurrent;

namespace ChuvadiReader.Web.Auth;

/// <summary>Why a session is about to end (D-30).</summary>
public enum ExpiryReason
{
    /// <summary>Nothing happened for the idle limit (30 minutes).</summary>
    Idle,

    /// <summary>The sign-in reached its longest life (8 hours).</summary>
    Absolute,
}

/// <summary>A session is about to end at <paramref name="EndsAt"/>; shown in every open tab of it.</summary>
public sealed record ExpiryNotice(DateTimeOffset EndsAt, ExpiryReason Reason);

/// <summary>A planned restart (updates at quiet hours, announced in advance): shown in every open tab.</summary>
/// <param name="At">When the portal restarts.</param>
/// <param name="Message">The operator's own wording, or null for the standard text.</param>
public sealed record MaintenanceNotice(DateTimeOffset At, string? Message);

/// <summary>
/// Reaches the open browser tabs of a sign-in, wherever they run: in this process (<see cref="OpenTabs"/>)
/// or in the person's worker process (the gateway's worker pool).
/// </summary>
public interface ITabControl
{
    /// <summary>Ends the open tabs of a sign-in (by <c>sid</c>) or of a person (by <c>sub</c> only): their
    /// files are deleted and the browser goes to the signed-out page. Returns how many were ended.</summary>
    Task<int> EndAsync(string? sub, string? sid);

    /// <summary>Shows (or, with null, takes down) the expiry warning in the open tabs of a sign-in.</summary>
    Task NoticeAsync(string sub, string? sid, ExpiryNotice? notice);

    /// <summary>Shows (or, with null, takes down) a planned-restart banner in every open tab, now and later.</summary>
    Task AnnounceAsync(MaintenanceNotice? notice);
}

/// <summary>The browser tabs open in this process, by sign-in. Singleton.</summary>
public sealed class OpenTabs : ITabControl
{
    private readonly ConcurrentDictionary<Guid, Tab> _open = new();
    private readonly ConcurrentDictionary<string, ExpiryNotice> _notices = new(StringComparer.Ordinal);

    private sealed record Tab(string Sub, string? Sid, Func<Task> End, Func<ExpiryNotice?, Task> Notice);

    private readonly Files.SessionStates? _sessions;

    /// <param name="sessions">The sessions this process holds (D-174); null where no Reader runs (the gateway, tests).</param>
    public OpenTabs(Files.SessionStates? sessions = null) => _sessions = sessions;

    /// <summary>Registers an open tab. Dispose the result when the tab's session ends. A warning already
    /// showing for the sign-in is shown in the new tab too.</summary>
    public IDisposable Open(string sub, string? sid, Func<Task> end, Func<ExpiryNotice?, Task> notice)
    {
        var id = Guid.NewGuid();
        _open[id] = new Tab(sub, sid, end, notice);
        if (_notices.TryGetValue(Key(sub, sid), out var current))
        {
            _ = notice(current);
        }

        return new Registration(this, id);
    }

    public int Count => _open.Count;

    /// <summary>The planned restart being announced, or null.</summary>
    public MaintenanceNotice? Maintenance { get; private set; }

    /// <summary>Raised when <see cref="Maintenance"/> changes (tabs show or hide the banner).</summary>
    public event Action? MaintenanceChanged;

    public Task AnnounceAsync(MaintenanceNotice? notice)
    {
        if (Maintenance != notice)
        {
            Maintenance = notice;
            MaintenanceChanged?.Invoke();
        }

        return Task.CompletedTask;
    }

    public async Task<int> EndAsync(string? sub, string? sid)
    {
        var ending = _open.Where(e => Matches(e.Value, sub, sid)).ToList();
        if (sub is not null)
        {
            _notices.TryRemove(Key(sub, sid), out _);
        }

        foreach (var (id, tab) in ending)
        {
            _open.TryRemove(id, out _);
            try
            {
                await tab.End().ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is ObjectDisposedException or InvalidOperationException or Microsoft.JSInterop.JSDisconnectedException or TaskCanceledException)
            {
                // The tab was already going away; its files go with its session, just below.
            }
        }

        // D-174: the session itself ends, whichever connection is open or none: its page images are freed and
        // its files deleted, including what an earlier connection (before a reload) left behind.
        _sessions?.End(sub, sid);
        return ending.Count;
    }

    public async Task NoticeAsync(string sub, string? sid, ExpiryNotice? notice)
    {
        if (notice is null)
        {
            _notices.TryRemove(Key(sub, sid), out _);
        }
        else
        {
            _notices[Key(sub, sid)] = notice;
        }

        foreach (var tab in _open.Values.Where(t => Matches(t, sub, sid)).ToList())
        {
            try
            {
                await tab.Notice(notice).ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is ObjectDisposedException or InvalidOperationException or Microsoft.JSInterop.JSDisconnectedException or TaskCanceledException)
            {
            }
        }
    }

    private static bool Matches(Tab t, string? sub, string? sid)
        => sid is not null ? t.Sid == sid : sub is not null && t.Sub == sub;

    private static string Key(string sub, string? sid) => sid ?? "sub:" + sub;

    private sealed class Registration(OpenTabs owner, Guid id) : IDisposable
    {
        public void Dispose() => owner._open.TryRemove(id, out _);
    }
}

/// <summary>
/// Which sign-ins still count. Sessions are keyed by Sangam's <c>sid</c> (one Sangam sign-in) and
/// <c>sub</c> (the person). A back-channel logout, a portal sign-out or expiry revokes the sign-in: its
/// cookie stops working at once and each open tab of it is ended through <see cref="ITabControl"/>. Singleton.
/// </summary>
public sealed class PortalSessions
{
    private readonly ConcurrentDictionary<string, DateTimeOffset> _revokedSids = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, DateTimeOffset> _subRevokedAt = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, DateTimeOffset> _seenLogoutTokens = new(StringComparer.Ordinal);
    private readonly TimeProvider _time;
    private readonly ITabControl _tabs;
    private readonly TimeSpan _keep;

    public PortalSessions(TimeProvider time, Microsoft.Extensions.Options.IOptions<SangamOptions> options, ITabControl tabs)
    {
        _time = time;
        _tabs = tabs;
        _keep = options.Value.AbsoluteSessionLifetime + TimeSpan.FromHours(1);
    }

    /// <summary>False when the sign-in was revoked after the cookie was issued.</summary>
    public bool IsValid(string? sub, string? sid, DateTimeOffset issuedAt)
    {
        if (sid is not null && _revokedSids.ContainsKey(sid))
        {
            return false;
        }

        return sub is null || !_subRevokedAt.TryGetValue(sub, out var at) || issuedAt > at;
    }

    /// <summary>True when this sign-in was revoked (by <c>sid</c>, or every sign-in of the person since <paramref name="since"/>).</summary>
    public bool IsRevoked(string? sub, string? sid, DateTimeOffset since) => !IsValid(sub, sid, since);

    /// <summary>Revokes a sign-in (by <c>sid</c>), or every sign-in of a person (by <c>sub</c> only), and
    /// ends their open tabs unless <paramref name="endTabs"/> is false (the tab that started a sign-out
    /// is leaving for Sangam and must not be navigated away mid-redirect; its tabs end on the way back).</summary>
    public async Task<int> RevokeAsync(string? sub, string? sid, bool endTabs = true)
    {
        var now = _time.GetUtcNow();
        Prune(now);
        if (sid is not null)
        {
            _revokedSids[sid] = now + _keep;
        }
        else if (sub is not null)
        {
            _subRevokedAt[sub] = now;
        }

        return endTabs ? await _tabs.EndAsync(sub, sid).ConfigureAwait(false) : 0;
    }

    /// <summary>Records a logout token's <c>jti</c>; false if it was already used (replay).</summary>
    public bool FirstUse(string jti)
    {
        var now = _time.GetUtcNow();
        Prune(now);
        return _seenLogoutTokens.TryAdd(jti, now + TimeSpan.FromHours(1));
    }

    private void Prune(DateTimeOffset now)
    {
        foreach (var (k, v) in _revokedSids)
        {
            if (v < now) _revokedSids.TryRemove(k, out _);
        }

        foreach (var (k, v) in _subRevokedAt)
        {
            if (v + _keep < now) _subRevokedAt.TryRemove(k, out _);
        }

        foreach (var (k, v) in _seenLogoutTokens)
        {
            if (v < now) _seenLogoutTokens.TryRemove(k, out _);
        }
    }
}
