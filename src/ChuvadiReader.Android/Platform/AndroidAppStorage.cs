using System.Text.Json;
using ChuvadiReader.Core.Storage;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// App settings as one JSON file in the app's private files folder — the same format and
/// behaviour as the Windows host's FileAppStorage, so a settings file moves between platforms.
/// Pure BCL (System.Text.Json); no SharedPreferences, nothing leaves the device.
/// </summary>
public sealed class AndroidAppStorage : IAppStorage
{
    private readonly string _file;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private Dictionary<string, string> _cache = new();
    private bool _loaded;

    public AndroidAppStorage(string directory)
    {
        Directory.CreateDirectory(directory);
        _file = Path.Combine(directory, "settings.json");
    }

    public async Task<string?> GetAsync(string key, CancellationToken ct = default)
    {
        await EnsureLoadedAsync(ct).ConfigureAwait(false);
        return _cache.TryGetValue(key, out var v) ? v : null;
    }

    /// <summary>Synchronous read for start-up decisions made before the UI loop runs.</summary>
    public string? GetSync(string key)
    {
        if (!_loaded)
        {
            _gate.Wait();
            try
            {
                if (!_loaded)
                {
                    _cache = ReadFile(File.Exists(_file) ? File.ReadAllText(_file) : null);
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
        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _cache[key] = value;
            var json = JsonSerializer.Serialize(_cache, StorageJson.Default.DictionaryStringString);

            // Write-then-replace, so a phone killed mid-write never leaves a half file.
            var temp = _file + ".tmp";
            await File.WriteAllTextAsync(temp, json, ct).ConfigureAwait(false);
            File.Move(temp, _file, overwrite: true);
        }
        finally
        {
            _gate.Release();
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

            _cache = ReadFile(File.Exists(_file) ? await File.ReadAllTextAsync(_file, ct).ConfigureAwait(false) : null);
            _loaded = true;
        }
        finally
        {
            _gate.Release();
        }
    }

    private static Dictionary<string, string> ReadFile(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return new();
        }

        try
        {
            return JsonSerializer.Deserialize(json, StorageJson.Default.DictionaryStringString) ?? new();
        }
        catch (JsonException)
        {
            return new();
        }
    }
}

/// <summary>Source-generated JSON for the settings file: safe under trimming.</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(Dictionary<string, string>))]
internal sealed partial class StorageJson : System.Text.Json.Serialization.JsonSerializerContext
{
}
