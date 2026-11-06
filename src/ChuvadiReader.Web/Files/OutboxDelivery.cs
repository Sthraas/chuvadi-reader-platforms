using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// Turns "the Reader wrote a file" into "the browser downloads it". The desktop Reader saves to a
/// path the person chose; on the portal that path is a folder in the session's outbox, and every file
/// the Reader finishes writing there is offered to the browser once. It stays until the session ends,
/// because the Reader may keep using a file it saved (e.g. open it in a new tab).
/// A file counts as finished when its size has stopped changing and no writer still holds it open.
/// Polling (no inotify) so many sessions don't exhaust the kernel's watch limits. Scoped: one per circuit.
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

    /// <summary>Files handed to the browser so far (for tests and the build log).</summary>
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

    /// <summary>Creates a new, watched folder inside the outbox.</summary>
    public string NewFolder()
    {
        var dir = Path.Combine(_space.Outbox, Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(8)));
        SpaceLayout.CreatePrivateDirectory(dir);
        Watch(dir);
        return dir;
    }

    /// <summary>Watches <paramref name="folder"/> (inside the outbox) until <see cref="PortalOptions.SaveWaitLimit"/>
    /// passes without a new file, or for the whole session when <paramref name="untilSessionEnds"/> is true.</summary>
    public void Watch(string folder, bool untilSessionEnds = false)
    {
        if (!SpaceLayout.IsInside(_space.Outbox, Path.Combine(folder, "x")))
        {
            throw new ArgumentException("Only outbox folders are delivered.", nameof(folder));
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
                if (!IsFinished(file))
                {
                    continue;
                }

                lock (_lock)
                {
                    if (!_delivered.Add(file))
                    {
                        continue;
                    }

                    if (_watched.TryGetValue(folder, out var until) && until != DateTimeOffset.MaxValue)
                    {
                        _watched[folder] = now + _options.SaveWaitLimit;
                    }
                }

                var name = Path.GetFileName(file);
                var ticket = _registry.CreateDownload(_space.UserKey, _space.SessionId, file, name, _options.DownloadLinkLifetime, deleteAfter: false);
                try
                {
                    await _browser.DownloadAsync($"{FileEndpoints.Prefix}/download/{ticket.Id}", name, ct).ConfigureAwait(false);
                }
                catch (Exception ex) when (ex is Microsoft.JSInterop.JSException or Microsoft.JSInterop.JSDisconnectedException or TaskCanceledException)
                {
                    _log.LogInformation("Could not hand {File} to the browser: {Message}", name, ex.Message);
                }
            }
        }
    }

    /// <summary>Finished = present, non-empty, same size as on the previous pass, and openable exclusively.</summary>
    private bool IsFinished(string file)
    {
        long size;
        try
        {
            size = new FileInfo(file).Length;
        }
        catch (IOException)
        {
            return false;
        }

        lock (_lock)
        {
            if (_delivered.Contains(file))
            {
                return false;
            }

            var stable = _lastSize.TryGetValue(file, out var before) && before == size && size > 0;
            _lastSize[file] = size;
            if (!stable)
            {
                return false;
            }
        }

        try
        {
            using var probe = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.None);
            return true;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
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
