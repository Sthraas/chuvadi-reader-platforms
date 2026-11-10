using ChuvadiReader.Platform;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// Turns "the Reader wrote a file" into "the browser downloads it" (Foundation F-1: Save and Save as
/// deliver a download). Two ways in:
/// <list type="bullet">
/// <item><see cref="DeliverAsync"/> — the Reader's write-back call after a save (Foundation Group B).</item>
/// <item>Watching the outbox folders the pickers hand out — needed until Group B's write-back calls are
/// in the Ui, and kept as a safety net for any save site without one. A file counts as finished when its
/// size has stopped changing and no writer still holds it open. Polling, not inotify, so many sessions
/// don't exhaust the kernel's watch limits.</item>
/// </list>
/// Each version of a file (path, size, time written) is delivered once, whichever way it arrives first.
/// Files stay until the session ends, because the Reader may keep using a file it saved.
/// Scoped: one per browser connection.
/// </summary>
public sealed class OutboxDelivery : IAsyncDisposable
{
    private static readonly TimeSpan Interval = TimeSpan.FromMilliseconds(750);

    private readonly SessionSpace _space;
    private readonly TransferRegistry _registry;
    private readonly BrowserBridge _browser;
    private readonly PortalOptions _options;
    private readonly TimeProvider _time;
    private readonly ILogger<OutboxDelivery> _log;
    private readonly Dictionary<string, DateTimeOffset> _watched = new(StringComparer.Ordinal);
    private readonly Dictionary<string, long> _lastSize = new(StringComparer.Ordinal);
    private readonly HashSet<string> _delivered = new(StringComparer.Ordinal);
    private readonly object _lock = new();
    private readonly CancellationTokenSource _stop = new();
    private Task? _loop;

    public OutboxDelivery(SessionSpace space, TransferRegistry registry, BrowserBridge browser, IOptions<PortalOptions> options,
        TimeProvider time, ILogger<OutboxDelivery> log)
    {
        _space = space;
        _registry = registry;
        _browser = browser;
        _options = options.Value;
        _time = time;
        _log = log;
    }

    /// <summary>File versions handed to the browser so far.</summary>
    public int DeliveredCount
    {
        get
        {
            lock (_lock)
            {
                return _delivered.Count;
            }
        }
    }

    /// <summary>Creates a new folder inside the outbox. A save folder (<paramref name="collect"/> false) is
    /// watched and each file in it downloads when finished. A folder picked for several files
    /// (<paramref name="collect"/> true, D-129) isn't: its files wait for the write-back call, which
    /// sends them together as one .zip.</summary>
    public string NewFolder(bool collect = false)
    {
        var dir = Path.Combine(_space.Outbox, Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(8)));
        SpaceLayout.CreatePrivateDirectory(dir);
        if (!collect)
        {
            Watch(dir);
        }

        return dir;
    }

    /// <summary>Watches <paramref name="folder"/> (inside the outbox) until <see cref="PortalOptions.SaveWaitLimit"/>
    /// passes without a new file, or for the whole session when <paramref name="untilSessionEnds"/> is true.</summary>
    public void Watch(string folder, bool untilSessionEnds = false)
    {
        if (!SpaceLayout.IsInside(_space.Outbox, Path.Combine(folder, "x")))
        {
            throw new ArgumentException("Only outbox folders are watched.", nameof(folder));
        }

        lock (_lock)
        {
            var until = untilSessionEnds ? DateTimeOffset.MaxValue : _time.GetUtcNow() + _options.SaveWaitLimit;
            if (!_watched.TryGetValue(folder, out var current) || current < until)
            {
                _watched[folder] = until;
            }

            _loop ??= Task.Run(() => RunAsync(_stop.Token));
        }
    }

    /// <summary>Delivers a file, or a folder's files, now (the write-back call). A folder with two or more
    /// new files goes as one .zip (D-129); a single new file goes as itself. A version already delivered
    /// is not sent again.</summary>
    public async Task<WriteBackResult> DeliverAsync(string path, CancellationToken ct = default)
    {
        var isFolder = Directory.Exists(path);
        var files = isFolder
            ? Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories).ToList()
            : File.Exists(path) ? [path] : [];
        if (files.Count == 0)
        {
            return new WriteBackResult(WriteBackOutcome.Failed, "There was nothing to download.");
        }

        if (isFolder)
        {
            var fresh = new List<(string File, string Key)>();
            foreach (var file in files)
            {
                if (VersionKey(file) is { } key)
                {
                    lock (_lock)
                    {
                        if (!_delivered.Contains(key))
                        {
                            fresh.Add((file, key));
                        }
                    }
                }
            }

            if (fresh.Count >= 2)
            {
                return await SendZipAsync(path, fresh, ct).ConfigureAwait(false);
            }

            files = fresh.Select(f => f.File).ToList();
        }

        foreach (var file in files)
        {
            var key = VersionKey(file);
            if (key is null)
            {
                continue;
            }

            lock (_lock)
            {
                if (!_delivered.Add(key))
                {
                    continue;
                }
            }

            if (!await SendAsync(file, ct).ConfigureAwait(false))
            {
                lock (_lock)
                {
                    _delivered.Remove(key);
                }

                return new WriteBackResult(WriteBackOutcome.Failed, "The browser didn't take the download.");
            }
        }

        return new WriteBackResult(WriteBackOutcome.Done);
    }

    private async Task RunAsync(CancellationToken ct)
    {
        using var timer = new PeriodicTimer(Interval, _time);
        try
        {
            while (await timer.WaitForNextTickAsync(ct).ConfigureAwait(false))
            {
                await ScanOnceAsync(ct).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    /// <summary>One pass over the watched folders. Public for tests.</summary>
    public async Task ScanOnceAsync(CancellationToken ct = default)
    {
        List<string> folders;
        var now = _time.GetUtcNow();
        lock (_lock)
        {
            foreach (var expired in _watched.Where(w => w.Value <= now).Select(w => w.Key).ToList())
            {
                _watched.Remove(expired);
            }

            folders = _watched.Keys.ToList();
        }

        foreach (var folder in folders.Where(Directory.Exists))
        {
            foreach (var file in Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories))
            {
                ct.ThrowIfCancellationRequested();
                var key = FinishedVersion(file);
                if (key is null)
                {
                    continue;
                }

                lock (_lock)
                {
                    if (!_delivered.Add(key))
                    {
                        continue;
                    }

                    if (_watched.TryGetValue(folder, out var until) && until != DateTimeOffset.MaxValue)
                    {
                        _watched[folder] = now + _options.SaveWaitLimit;
                    }
                }

                await SendAsync(file, ct).ConfigureAwait(false);
            }
        }
    }

    private async Task<WriteBackResult> SendZipAsync(string folder, List<(string File, string Key)> fresh, CancellationToken ct)
    {
        lock (_lock)
        {
            if (fresh.Any(f => !_delivered.Add(f.Key)))
            {
                fresh.ForEach(f => _delivered.Remove(f.Key));
                return new WriteBackResult(WriteBackOutcome.Done); // the same files are going out already
            }
        }

        var into = Path.Combine(_space.Outbox, "zip-" + Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(8)));
        try
        {
            SpaceLayout.CreatePrivateDirectory(into); // not watched: the zip goes out once, here
            var zip = await ZipBundle.WriteAsync(folder, fresh.Select(f => f.File).ToList(), into, ct).ConfigureAwait(false);
            if (await SendAsync(zip, ct).ConfigureAwait(false))
            {
                return new WriteBackResult(WriteBackOutcome.Done);
            }
        }
        catch (IOException ex)
        {
            _log.LogWarning("Could not build the zip for {Count} files: {Message}", fresh.Count, ex.Message);
        }

        lock (_lock)
        {
            fresh.ForEach(f => _delivered.Remove(f.Key));
        }

        return new WriteBackResult(WriteBackOutcome.Failed, "The browser didn't take the download.");
    }

    private async Task<bool> SendAsync(string file, CancellationToken ct)
    {
        var name = Path.GetFileName(file);
        var ticket = _registry.CreateDownload(_space.UserKey, _space.ConnectionId, file, name, _options.DownloadLinkLifetime, deleteAfter: false);
        try
        {
            await _browser.DownloadAsync($"{FileEndpoints.Prefix}/download/{ticket.Id}", name, ct).ConfigureAwait(false);
            return true;
        }
        catch (Exception ex) when (ex is Microsoft.JSInterop.JSException or Microsoft.JSInterop.JSDisconnectedException or TaskCanceledException)
        {
            _log.LogInformation("Could not hand {File} to the browser: {Message}", name, ex.Message);
            return false;
        }
    }

    /// <summary>The version key of a file that has finished being written, or null: present, non-empty,
    /// the same size as on the previous pass, and openable exclusively.</summary>
    private string? FinishedVersion(string file)
    {
        var key = VersionKey(file);
        if (key is null)
        {
            return null;
        }

        long size = new FileInfo(file).Length;
        lock (_lock)
        {
            if (_delivered.Contains(key))
            {
                return null;
            }

            var stable = _lastSize.TryGetValue(file, out var before) && before == size && size > 0;
            _lastSize[file] = size;
            if (!stable)
            {
                return null;
            }
        }

        try
        {
            using var probe = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.None);
            return key;
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }
    }

    private static string? VersionKey(string file)
    {
        try
        {
            var info = new FileInfo(file);
            return info.Exists ? $"{info.FullName}|{info.Length}|{info.LastWriteTimeUtc.Ticks}" : null;
        }
        catch (IOException)
        {
            return null;
        }
    }

    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync().ConfigureAwait(false);
        if (_loop is not null)
        {
            try
            {
                await _loop.ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
            }
        }

        _stop.Dispose();
    }
}
