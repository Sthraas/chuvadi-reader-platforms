using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using ChuvadiReader.Core.Storage;

namespace ChuvadiReader.Hosting.Desktop;

/// <summary>
/// Stores app state as a single JSON file (settings.json) in the host's app-data folder
/// (Windows: %AppData%\Chuvadi). No network, no registry — just a file the user owns.
/// Pure BCL (System.Text.Json). Shared by the desktop and Android hosts.
/// Writes go to a temporary file beside it that then replaces settings.json, so a crash or
/// power cut mid-write leaves the previous settings intact instead of a truncated file.
/// <para>B-16: a folder that can't be created or written (a read-only home, a locked-down or kiosk profile, a
/// full disk) never stops the app. Values are kept in memory for the session, settings already on disk are
/// still read, and <see cref="CannotSave"/> is raised once so the host can tell the person.</para>
/// </summary>
public sealed class FileAppStorage : IAppStorage
{
    private readonly string _file;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private Dictionary<string, string> _cache = new();
    private bool _loaded;
    private int _cannotSave;

    public FileAppStorage(string directory)
    {
        _file = Path.Combine(directory, "settings.json");
        try
        {
            Directory.CreateDirectory(directory);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            CannotSaveReason = e.Message;
            _cannotSave = 1;
        }
    }

    /// <summary>False once settings can't be written; they are then kept in memory for this session.</summary>
    public bool CanSave => Volatile.Read(ref _cannotSave) == 0;

    /// <summary>Why settings can't be saved (the system's text), or null while saving works.</summary>
    public string? CannotSaveReason { get; private set; }

    /// <summary>Raised once, on the first save that can't be written (with the reason). Raised on the saving
    /// thread; a folder that couldn't be created is reported by <see cref="CanSave"/> from the start.</summary>
    public event Action<string>? CannotSave;

    public async Task<string?> GetAsync(string key, CancellationToken ct = default)
    {
        await EnsureLoadedAsync(ct).ConfigureAwait(false);
        return _cache.TryGetValue(key, out var v) ? v : null;
    }

    /// <summary>Synchronous read for startup decisions made before the UI loop runs.</summary>
    public string? GetSync(string key)
    {
        if (!_loaded)
        {
            _gate.Wait();
            try
            {
                if (!_loaded)
                {
                    try
                    {
                        if (File.Exists(_file))
                        {
                            _cache = JsonSerializer.Deserialize(File.ReadAllText(_file), SettingsJson.Default.DictionaryStringString) ?? new();
                        }
                    }
                    catch (Exception e) when (e is JsonException or IOException or UnauthorizedAccessException)
                    {
                        _cache = new(); // unreadable: start from defaults
                    }

                    _loaded = true;
                }
            }
            finally
            {
                _gate.Release();
            }
        }

        return _cache.TryGetValue(key, out var v) ? v : null;
    }

    public async Task SetAsync(string key, string value, CancellationToken ct = default)
    {
        await EnsureLoadedAsync(ct).ConfigureAwait(false);
        string? failed = null;
        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _cache[key] = value;
            if (CanSave)
            {
                var json = JsonSerializer.Serialize(_cache, SettingsJson.Default.DictionaryStringString);
                var temp = _file + ".tmp";
                try
                {
                    await File.WriteAllTextAsync(temp, json, ct).ConfigureAwait(false);
                    File.Move(temp, _file, overwrite: true);
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    if (Interlocked.Exchange(ref _cannotSave, 1) == 0)
                    {
                        CannotSaveReason = e.Message;
                        failed = e.Message;
                    }
                }
            }
        }
        finally
        {
            _gate.Release();
        }

        if (failed is not null)
        {
            CannotSave?.Invoke(failed); // outside the gate, so a handler may read settings
        }
    }

    private async Task EnsureLoadedAsync(CancellationToken ct)
    {
        if (_loaded)
        {
            return;
        }

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_loaded)
            {
                return;
            }

            try
            {
                if (File.Exists(_file))
                {
                    var json = await File.ReadAllTextAsync(_file, ct).ConfigureAwait(false);
                    _cache = JsonSerializer.Deserialize(json, SettingsJson.Default.DictionaryStringString) ?? new();
                }
            }
            catch (Exception e) when (e is JsonException or IOException or UnauthorizedAccessException)
            {
                _cache = new(); // unreadable: start from defaults
            }

            _loaded = true;
        }
        finally
        {
            _gate.Release();
        }
    }
}

/// <summary>AT-03: settings.json is read and written by generated code, not reflection, so a trimmed or AOT
/// host can't lose it (and the first read does no reflection at startup). Same JSON as before, byte for byte.</summary>
[JsonSerializable(typeof(Dictionary<string, string>))]
internal sealed partial class SettingsJson : JsonSerializerContext
{
}
