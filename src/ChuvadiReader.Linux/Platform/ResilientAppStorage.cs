using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting.Desktop;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Settings that survive a home folder Chuvadi can't write (B-16: kiosk and locked-down profiles, a full
/// disk, a read-only home). Wraps the host kit's <see cref="FileAppStorage"/>; when its folder can't be
/// created or a save fails, the values are kept in memory for this session and <see cref="CannotSave"/> is
/// raised once, so the host can tell the person. Settings already on disk are still read.
/// </summary>
internal sealed class ResilientAppStorage : IAppStorage
{
    private readonly FileAppStorage? _file;
    private readonly Dictionary<string, string> _memory = new(StringComparer.Ordinal);
    private readonly object _lock = new();
    private int _failed;

    public ResilientAppStorage(string directory)
    {
        try
        {
            _file = new FileAppStorage(directory);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            Reason = ex.Message;
            _failed = 1;
        }
    }

    /// <summary>Raised once, the first time settings can't be written (with the reason).</summary>
    public event Action<string>? CannotSave;

    /// <summary>Why settings can't be saved, once known (null while saving works).</summary>
    public string? Reason { get; private set; }

    public bool Saving => Volatile.Read(ref _failed) == 0;

    public string? GetSync(string key)
    {
        lock (_lock)
        {
            if (_memory.TryGetValue(key, out var v))
            {
                return v;
            }
        }

        try
        {
            return _file?.GetSync(key);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    public async Task<string?> GetAsync(string key, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_memory.TryGetValue(key, out var v))
            {
                return v;
            }
        }

        try
        {
            return _file is null ? null : await _file.GetAsync(key, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    public async Task SetAsync(string key, string value, CancellationToken ct = default)
    {
        lock (_lock)
        {
            _memory[key] = value;
        }

        if (_file is null || !Saving)
        {
            return;
        }

        try
        {
            await _file.SetAsync(key, value, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            if (Interlocked.Exchange(ref _failed, 1) == 0)
            {
                Reason = ex.Message;
                CannotSave?.Invoke(ex.Message);
            }
        }
    }
}
