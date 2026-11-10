using System.Collections.Concurrent;
using System.Security.Claims;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// What one signed-in session holds on the server (D-174): its working folder and its saved settings, the
/// open-tab list among them. It belongs to the person and their sign-in (Sangam's <c>sid</c>), not to a
/// browser connection, so a reload, a dropped connection or a second browser tab finds the same documents.
/// </summary>
public sealed class SessionState
{
    private int _connections;
    private long _lastDetachedTicks;

    internal SessionState(string owner, string userKey, string? sid, string root, DateTimeOffset now)
    {
        Owner = owner;
        UserKey = userKey;
        Sid = sid;
        Root = root;
        SessionId = Path.GetFileName(root);
        _lastDetachedTicks = now.UtcTicks;
    }

    /// <summary>Person and sign-in: the same value page images are owned by (<c>PortalPageImageOwner</c>).</summary>
    public string Owner { get; }

    public string UserKey { get; }

    public string? Sid { get; }

    /// <summary>Random id; also the folder name.</summary>
    public string SessionId { get; }

    public string Root { get; }

    /// <summary>The Reader's settings for this session (in memory only): open tabs, recents, preferences.</summary>
    public ConcurrentDictionary<string, string> Values { get; } = new(StringComparer.Ordinal);

    /// <summary>True once the session has ended: its files are gone and nothing new may be kept.</summary>
    public bool Ended { get; internal set; }

    /// <summary>Browser connections using this session right now.</summary>
    public int Connections => Volatile.Read(ref _connections);

    internal DateTimeOffset LastDetached => new(Volatile.Read(ref _lastDetachedTicks), TimeSpan.Zero);

    internal void Attach() => Interlocked.Increment(ref _connections);

    internal void Detach(DateTimeOffset now)
    {
        Volatile.Write(ref _lastDetachedTicks, now.UtcTicks);
        Interlocked.Decrement(ref _connections);
    }
}

/// <summary>
/// The sessions this process holds (D-174). A session starts with its first connection and ends when the
/// sign-in ends (sign-out, expiry, a Sangam sign-out), whichever connection is open or none: its page images
/// are freed, its folder is deleted, its settings are dropped. Singleton; in gateway mode each person's
/// worker has its own.
/// </summary>
public sealed class SessionStates : IDisposable
{
    private readonly ConcurrentDictionary<string, SessionState> _sessions = new(StringComparer.Ordinal);
    private readonly PortalOptions _options;
    private readonly PageImages _images;
    private readonly TimeProvider _time;
    private readonly ILogger<SessionStates> _log;
    private readonly object _gate = new();

    public SessionStates(IOptions<PortalOptions> options, PageImages images, TimeProvider time, ILogger<SessionStates> log)
    {
        _options = options.Value;
        _images = images;
        _time = time;
        _log = log;
    }

    /// <summary>Sessions held right now.</summary>
    public int Count => _sessions.Count;

    /// <summary>The session of <paramref name="user"/>'s sign-in, created (with its folders, owner-only) on first use.</summary>
    public SessionState For(ClaimsPrincipal user)
    {
        var key = Files.UserKey.From(user) ?? throw new UnauthorizedAccessException("Sign in to use the portal.");
        var sid = user.FindFirst("sid")?.Value;
        var owner = key + "/" + (sid ?? "-"); // as PortalPageImageOwner.For
        lock (_gate)
        {
            if (_sessions.TryGetValue(owner, out var existing))
            {
                return existing;
            }

            var id = Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(12));
            var root = Path.Combine(SpaceLayout.UserFolder(_options.DataRoot, key), "sessions", id);
            foreach (var dir in new[] { root, Path.Combine(root, "uploads"), Path.Combine(root, "outbox"), Path.Combine(root, "print") })
            {
                SpaceLayout.CreatePrivateDirectory(dir);
            }

            return _sessions[owner] = new SessionState(owner, key, sid, root, _time.GetUtcNow());
        }
    }

    /// <summary>Ends the sessions of a sign-in (by <paramref name="sid"/>) or of a person (by
    /// <paramref name="sub"/> only), as <see cref="OpenTabs.EndAsync"/> matches tabs. Returns how many ended.</summary>
    public int End(string? sub, string? sid)
    {
        var key = sub is null ? null : Files.UserKey.FromSub(sub);
        var ended = 0;
        foreach (var s in _sessions.Values)
        {
            if (sid is not null ? s.Sid == sid : key is not null && s.UserKey == key)
            {
                ended += End(s) ? 1 : 0;
            }
        }

        return ended;
    }

    /// <summary>Ends one session: frees every page image it drew, deletes its files, drops its settings.
    /// Safe to call more than once.</summary>
    public bool End(SessionState session)
    {
        lock (_gate)
        {
            if (session.Ended)
            {
                return false;
            }

            session.Ended = true;
            _sessions.TryRemove(new KeyValuePair<string, SessionState>(session.Owner, session));
        }

        var freed = _images.RemoveOwner(session.Owner); // WT-21: whichever page or connection drew them
        session.Values.Clear();
        try
        {
            if (Directory.Exists(session.Root))
            {
                Directory.Delete(session.Root, recursive: true);
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // A file still open (e.g. a render in flight): the start-up sweep removes it later.
            _log.LogWarning("Could not delete session folder {Session} yet: {Message}", session.SessionId, ex.Message);
        }

        _log.LogInformation("Session {Session} ended; {Images} page image(s) freed", session.SessionId, freed);
        return true;
    }

    /// <summary>A safety net: ends sessions nobody has been connected to for <paramref name="longerThan"/>
    /// (the session clock normally ends them first). Returns how many ended.</summary>
    public int EndAbandoned(TimeSpan longerThan)
    {
        var now = _time.GetUtcNow();
        var ended = 0;
        foreach (var s in _sessions.Values)
        {
            if (s.Connections <= 0 && now - s.LastDetached > longerThan)
            {
                ended += End(s) ? 1 : 0;
            }
        }

        return ended;
    }

    public void Dispose()
    {
        foreach (var s in _sessions.Values)
        {
            End(s);
        }
    }
}
