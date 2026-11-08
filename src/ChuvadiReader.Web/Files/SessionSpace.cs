using ChuvadiReader.Web.Hosting;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// One browser session's working folders on the server, inside the signed-in person's own space:
/// <c>{DataRoot}/{userKey}/sessions/{sessionId}/</c> with <c>uploads</c>, <c>outbox</c> and
/// <c>print</c>. Created on first use, deleted when the session (Blazor circuit) ends, and swept at
/// start-up if the process stopped before it could clean up. Scoped: one per circuit.
/// </summary>
public sealed class SessionSpace : IDisposable
{
    private readonly AuthenticationStateProvider _auth;
    private readonly PortalOptions _options;
    private readonly ILogger<SessionSpace> _log;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private string? _userKey;
    private string? _root;
    private bool _deleted;

    public SessionSpace(AuthenticationStateProvider auth, IOptions<PortalOptions> options, ILogger<SessionSpace> log)
    {
        _auth = auth;
        _options = options.Value;
        _log = log;
        SessionId = Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(12));
    }

    /// <summary>Random id of this session; also the folder name.</summary>
    public string SessionId { get; }

    public string UserKey => _userKey ?? throw new InvalidOperationException("The session space is not ready yet.");

    public string Root => _root ?? throw new InvalidOperationException("The session space is not ready yet.");

    public string Uploads => Path.Combine(Root, "uploads");

    public string Outbox => Path.Combine(Root, "outbox");

    public string Print => Path.Combine(Root, "print");

    /// <summary>Resolves the signed-in person and creates the folders (owner-only on Unix).</summary>
    public async Task EnsureAsync(CancellationToken ct = default)
    {
        if (_root is not null)
        {
            return;
        }

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_root is not null)
            {
                return;
            }

            ObjectDisposedException.ThrowIf(_deleted, this);
            var state = await _auth.GetAuthenticationStateAsync().ConfigureAwait(false);
            var key = Files.UserKey.From(state.User)
                ?? throw new UnauthorizedAccessException("Sign in to use the portal.");

            var root = Path.Combine(SpaceLayout.UserFolder(_options.DataRoot, key), "sessions", SessionId);
            foreach (var dir in new[] { root, Path.Combine(root, "uploads"), Path.Combine(root, "outbox"), Path.Combine(root, "print") })
            {
                SpaceLayout.CreatePrivateDirectory(dir);
            }

            _userKey = key;
            _root = root;
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>True when <paramref name="path"/> is inside this session's folder.</summary>
    public bool Contains(string path)
        => _root is not null && SpaceLayout.IsInside(_root, path);

    /// <summary>Deletes every file of this session. Safe to call more than once.</summary>
    public void Delete()
    {
        if (_deleted)
        {
            return;
        }

        _deleted = true;
        if (_root is null)
        {
            return;
        }

        try
        {
            if (Directory.Exists(_root))
            {
                Directory.Delete(_root, recursive: true);
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // A file still open (e.g. a render in flight) — the start-up sweep removes it later.
            _log.LogWarning("Could not delete session folder {Session} yet: {Message}", SessionId, ex.Message);
        }
    }

    public void Dispose()
    {
        Delete();
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
