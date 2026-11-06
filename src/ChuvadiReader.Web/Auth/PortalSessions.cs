using System.Collections.Concurrent;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// Who is signed in where, so a sign-out reaches every browser tab of that sign-in. Sessions are
/// keyed by Sangam's <c>sid</c> (one Sangam sign-in) and <c>sub</c> (the person). A back-channel
/// logout or a portal sign-out revokes the sign-in: its cookie stops working and each open tab is
/// ended (its files deleted, the browser sent to the signed-out page). Singleton.
/// </summary>
public sealed class PortalSessions
{
    private readonly ConcurrentDictionary<string, DateTimeOffset> _revokedSids = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, DateTimeOffset> _subRevokedAt = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<Guid, Entry> _open = new();
    private readonly ConcurrentDictionary<string, DateTimeOffset> _seenLogoutTokens = new(StringComparer.Ordinal);
    private readonly TimeProvider _time;
    private readonly TimeSpan _keep;

    public PortalSessions(TimeProvider time, Microsoft.Extensions.Options.IOptions<SangamOptions> options)
    {
        _time = time;
        _keep = options.Value.AbsoluteSessionLifetime + TimeSpan.FromHours(1);
    }

    private sealed record Entry(string Sub, string? Sid, Func<Task> End);

    /// <summary>Registers an open tab. Dispose the result when the tab's session ends.</summary>
    public IDisposable Open(string sub, string? sid, Func<Task> end)
    {
        var id = Guid.NewGuid();
        _open[id] = new Entry(sub, sid, end);
        return new Registration(this, id);
    }

    public int OpenCount => _open.Count;

    /// <summary>False when the sign-in was revoked after the cookie was issued.</summary>
    public bool IsValid(string? sub, string? sid, DateTimeOffset issuedAt)
    {
        if (sid is not null && _revokedSids.ContainsKey(sid))
        {
            return false;
        }

        return sub is null || !_subRevokedAt.TryGetValue(sub, out var at) || issuedAt > at;
    }

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

        if (!endTabs)
        {
            return 0;
        }

        var ending = _open.Where(e => sid is not null ? e.Value.Sid == sid : e.Value.Sub == sub).ToList();
        foreach (var (id, entry) in ending)
        {
            _open.TryRemove(id, out _);
            try
            {
                await entry.End().ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is ObjectDisposedException or InvalidOperationException or Microsoft.JSInterop.JSDisconnectedException or TaskCanceledException)
            {
                // The tab was already going away; its files go with its session as usual.
            }
        }

        return ending.Count;
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

    private sealed class Registration(PortalSessions owner, Guid id) : IDisposable
    {
        public void Dispose() => owner._open.TryRemove(id, out _);
    }
}
