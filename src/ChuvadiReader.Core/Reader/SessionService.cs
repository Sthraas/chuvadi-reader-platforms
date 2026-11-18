using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Core.Reader;

/// <summary>
/// Reads and writes bench session files (a user-chosen <c>.json</c>) and maintains a small library
/// of reusable desk templates in app-data. Pure serialization + file IO — it owns no bench state;
/// <see cref="BenchService"/> produces and consumes the DTOs.
/// </summary>
public sealed class SessionService
{
    private static readonly JsonSerializerOptions Json = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new JsonStringEnumConverter() },
    };

    private readonly IAppPaths? _paths;

    /// <param name="paths">Host folders; desk templates live in its app-data folder.</param>
    public SessionService(IAppPaths? paths = null) => _paths = paths;

    // ── session files (user-chosen path) ───────────────────────────────────────

    public async Task SaveSessionAsync(string path, BenchSessionDto session, CancellationToken ct = default)
    {
        session.SavedAtUtc = DateTimeOffset.UtcNow.ToString("o");
        var json = JsonSerializer.Serialize(session, Json);
        await File.WriteAllTextAsync(path, json, ct).ConfigureAwait(false);
    }

    public async Task<BenchSessionDto> LoadSessionAsync(string path, CancellationToken ct = default)
    {
        var json = await File.ReadAllTextAsync(path, ct).ConfigureAwait(false);
        var dto = JsonSerializer.Deserialize<BenchSessionDto>(json, Json)
                  ?? throw new InvalidDataException("The session file is empty or not valid.");
        return dto;
    }

    // ── desks kept for the next start (D-203) ─────────────────────────────────

    private const string KeptDesksFile = "arrange-kept.json";

    /// <summary>Where Arrange's desks are kept between runs: the app's own data folder (per session on the portal),
    /// never a place the person picks. Null when the host gives no data folder.</summary>
    public string? KeptDesksPath => _paths is null ? null : Path.Combine(_paths.AppDataFolder, KeptDesksFile);

    /// <summary>D-203: the close card's Save. Written to a temporary name and then put in place, so a crash while
    /// writing leaves the last kept desks, never half a file.</summary>
    public async Task KeepDesksAsync(BenchSessionDto session, CancellationToken ct = default)
    {
        if (KeptDesksPath is not { } path) return;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var temp = path + ".writing";
        await SaveSessionAsync(temp, session, ct).ConfigureAwait(false);   // the one serializer call (trimming)
        File.Move(temp, path, overwrite: true);
    }

    /// <summary>The kept desks, or null when there are none (or the file can't be read: it is then left alone).</summary>
    public async Task<BenchSessionDto?> LoadKeptDesksAsync(CancellationToken ct = default)
    {
        if (KeptDesksPath is not { } path || !File.Exists(path)) return null;
        try
        {
            return await LoadSessionAsync(path, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is IOException or JsonException or InvalidDataException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>D-203: the close card's Discard, and Reset: nothing comes back on the next start.</summary>
    public void DiscardKeptDesks()
    {
        if (KeptDesksPath is not { } path) return;
        try { File.Delete(path); } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }

    // ── desk templates (app-data library) ──────────────────────────────────────

    private const string TemplatesFile = "desk-templates.json";

    /// <summary>Where templates were kept before the platform layer (%AppData%\ChuvadiReader on Windows).</summary>
    private static string LegacyTemplatesDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "ChuvadiReader");

    private string TemplatesPath
    {
        get
        {
            var dir = _paths?.AppDataFolder ?? LegacyTemplatesDir;
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, TemplatesFile);

            // One-time carry-over from the old folder; the old file is left in place.
            var legacy = Path.Combine(LegacyTemplatesDir, TemplatesFile);
            if (!File.Exists(path) && File.Exists(legacy)
                && !string.Equals(Path.GetFullPath(path), Path.GetFullPath(legacy), StringComparison.OrdinalIgnoreCase))
            {
                try { File.Copy(legacy, path); } catch (IOException) { /* another instance copied it first */ }
            }

            return path;
        }
    }

    public async Task<List<DeskTemplateDto>> ListTemplatesAsync(CancellationToken ct = default)
    {
        var path = TemplatesPath;
        if (!File.Exists(path))
        {
            return new List<DeskTemplateDto>();
        }

        try
        {
            var json = await File.ReadAllTextAsync(path, ct).ConfigureAwait(false);
            return JsonSerializer.Deserialize<List<DeskTemplateDto>>(json, Json) ?? new List<DeskTemplateDto>();
        }
        catch
        {
            // A corrupt library shouldn't break the bench; start fresh.
            return new List<DeskTemplateDto>();
        }
    }

    /// <summary>Adds or replaces a template (matched by name, case-insensitive) and persists.</summary>
    public async Task SaveTemplateAsync(DeskTemplateDto template, CancellationToken ct = default)
    {
        var list = await ListTemplatesAsync(ct).ConfigureAwait(false);
        list.RemoveAll(t => string.Equals(t.Name, template.Name, StringComparison.OrdinalIgnoreCase));
        list.Add(template);
        list.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
        await PersistTemplatesAsync(list, ct).ConfigureAwait(false);
    }

    public async Task DeleteTemplateAsync(string name, CancellationToken ct = default)
    {
        var list = await ListTemplatesAsync(ct).ConfigureAwait(false);
        if (list.RemoveAll(t => string.Equals(t.Name, name, StringComparison.OrdinalIgnoreCase)) > 0)
        {
            await PersistTemplatesAsync(list, ct).ConfigureAwait(false);
        }
    }

    private async Task PersistTemplatesAsync(List<DeskTemplateDto> list, CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(list, Json);
        await File.WriteAllTextAsync(TemplatesPath, json, ct).ConfigureAwait(false);
    }
}
