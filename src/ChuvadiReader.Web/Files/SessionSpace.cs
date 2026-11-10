using ChuvadiReader.Web.Hosting;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// One browser connection's view of its session's working folders (D-174):
/// <c>{DataRoot}/{userKey}/sessions/{sessionId}/</c> with <c>uploads</c>, <c>outbox</c> and <c>print</c>.
/// The folders belong to the signed-in session (<see cref="SessionState"/>), so every connection of the same
/// sign-in sees the same files; they are deleted when the session ends, not when a connection does, and swept
/// at start-up if the process stopped before it could clean up. Scoped: one per connection (Blazor circuit).
/// </summary>
public sealed class SessionSpace : IDisposable
{
    private readonly AuthenticationStateProvider _auth;
    private readonly SessionStates _states;
    private readonly TimeProvider _time;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private SessionState? _state;
    private bool _disposed;

    public SessionSpace(AuthenticationStateProvider auth, SessionStates states, TimeProvider time)
    {
        _auth = auth;
        _states = states;
        _time = time;
        ConnectionId = Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(12));
    }

    /// <summary>Random id of this connection: its upload, download and print tickets carry it, and are
    /// forgotten when it closes.</summary>
    public string ConnectionId { get; }

    /// <summary>The session this connection belongs to.</summary>
    public SessionState State => _state ?? throw new InvalidOperationException("The session space is not ready yet.");

    /// <summary>Random id of the session; also the folder name.</summary>
    public string SessionId => State.SessionId;

    public string UserKey => State.UserKey;

    public string Root => State.Root;

    public string Uploads => Path.Combine(Root, "uploads");

    public string Outbox => Path.Combine(Root, "outbox");

    public string Print => Path.Combine(Root, "print");

    /// <summary>Resolves the signed-in person's session and creates its folders (owner-only on Unix).</summary>
    public async Task EnsureAsync(CancellationToken ct = default)
    {
        if (_state is not null)
        {
            return;
        }

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_state is not null)
            {
                return;
            }

            ObjectDisposedException.ThrowIf(_disposed, this);
            var auth = await _auth.GetAuthenticationStateAsync().ConfigureAwait(false);
            var state = _states.For(auth.User);
            state.Attach();
            _state = state;
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>True when <paramref name="path"/> is inside this session's folder.</summary>
    public bool Contains(string path)
        => _state is { Ended: false } s && SpaceLayout.IsInside(s.Root, path);

    /// <summary>The session is over (sign-out, expiry): every file of it is deleted and its page images are
    /// freed, for all its connections. Safe to call more than once.</summary>
    public void Delete()
    {
        if (_state is { } s)
        {
            _states.End(s);
        }
    }

    /// <summary>The connection is gone. The session and its files stay until the session ends.</summary>
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        _state?.Detach(_time.GetUtcNow());
        _gate.Dispose();
    }
}

/// <summary>Folder layout and the safety checks shared by every part of the portal that touches disk.</summary>
public static class SpaceLayout
{
    public static string UserFolder(string dataRoot, string userKey)
    {
        if (string.IsNullOrWhiteSpace(dataRoot))
        {
            throw new InvalidOperationException("Portal:DataRoot is not configured.");
        }

        if (userKey.Length != 32 || !userKey.All(char.IsAsciiHexDigitLower))
        {
            throw new ArgumentException("Not a user key.", nameof(userKey));
        }

        return Path.Combine(Path.GetFullPath(dataRoot), "users", userKey);
    }

    /// <summary>Creates a directory readable only by the service account (0700 on Unix).</summary>
    public static void CreatePrivateDirectory(string path)
    {
        if (OperatingSystem.IsWindows())
        {
            Directory.CreateDirectory(path);
        }
        else
        {
            Directory.CreateDirectory(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        }
    }

    /// <summary>True when <paramref name="path"/> resolves to a location strictly inside <paramref name="root"/>.</summary>
    public static bool IsInside(string root, string path)
    {
        var full = Path.GetFullPath(path);
        var baseDir = Path.TrimEndingDirectorySeparator(Path.GetFullPath(root)) + Path.DirectorySeparatorChar;
        return full.StartsWith(baseDir, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
    }

    /// <summary>A file name safe to store and to show: no folders, no control characters, no bidi
    /// controls (WT-08: U+202E would show "fdp.exe" reversed), no reserved names, at most 120 characters,
    /// extension kept. Joiners (U+200C, U+200D) stay: Malayalam and Tamil names need them.</summary>
    /// <summary>Unicode's bidirectional formatting characters (UAX #9): marks, embeddings, overrides, isolates.</summary>
    public static bool IsBidiControl(char c)
        => c is '\u061C' or '\u200E' or '\u200F' or (>= '\u202A' and <= '\u202E') or (>= '\u2066' and <= '\u2069');

    public static string SafeFileName(string? name, string fallback)
    {
        var n = Path.GetFileName((name ?? string.Empty).Replace('\\', '/'));
        var chars = n.Where(c => !char.IsControl(c) && !IsBidiControl(c) && c != '/' && c != '\\' && c != ':' && c != '*' && c != '?'
                                 && c != '"' && c != '<' && c != '>' && c != '|').ToArray();
        n = new string(chars).Trim().Trim('.').Trim();
        if (n.Length == 0)
        {
            n = fallback;
        }

        if (n.Length > 120)
        {
            var ext = Path.GetExtension(n);
            if (ext.Length > 12)
            {
                ext = string.Empty;
            }

            n = n[..(120 - ext.Length)].TrimEnd() + ext;
        }

        var stem = Path.GetFileNameWithoutExtension(n).ToUpperInvariant();
        if (stem is "CON" or "PRN" or "AUX" or "NUL" || (stem.Length == 4 && (stem.StartsWith("COM", StringComparison.Ordinal) || stem.StartsWith("LPT", StringComparison.Ordinal)) && char.IsAsciiDigit(stem[3])))
        {
            n = "_" + n;
        }

        return n;
    }

    /// <summary>Removes session folders left behind by a previous run (crash, restart).</summary>
    public static int SweepStaleSessions(string dataRoot, TimeSpan olderThan, ILogger log)
    {
        var users = Path.Combine(Path.GetFullPath(dataRoot), "users");
        if (!Directory.Exists(users))
        {
            return 0;
        }

        int removed = 0;
        var cutoff = DateTime.UtcNow - olderThan;
        foreach (var sessions in Directory.EnumerateDirectories(users).Select(u => Path.Combine(u, "sessions")).Where(Directory.Exists))
        {
            foreach (var s in Directory.EnumerateDirectories(sessions))
            {
                try
                {
                    if (Directory.GetLastWriteTimeUtc(s) < cutoff)
                    {
                        Directory.Delete(s, recursive: true);
                        removed++;
                    }
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    log.LogWarning("Could not remove stale session folder {Folder}: {Message}", Path.GetFileName(s), ex.Message);
                }
            }
        }

        return removed;
    }
}
