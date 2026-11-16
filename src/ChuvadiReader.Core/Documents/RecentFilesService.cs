using System.Text.Json;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Core.Documents;

/// <summary>
/// Tracks recently opened documents. Persists to <see cref="IAppStorage"/>.
/// On first run (nothing persisted yet) it seeds a small sample so the
/// dashboard has something to show during Phase 0.
/// </summary>
public sealed class RecentFilesService
{
    private const string StorageKey = "recents";
    private readonly IAppStorage _storage;
    private readonly List<RecentItem> _items = new();

    private readonly bool _samples;

    /// <param name="platform">The host. No Phase 0 samples on a server (Web H8): every portal session
    /// starts empty and the sample files don't exist there. Only Windows shows them
    /// (<see cref="PhaseZeroSamples"/>): elsewhere a fresh install shows the first-run box.</param>
    public RecentFilesService(IAppStorage storage, IPlatformInfo? platform = null)
    {
        _storage = storage;
        _samples = PhaseZeroSamples.Shown(platform);
    }

    public IReadOnlyList<RecentItem> Items => _items;

    public int EncryptedCount => _items.Count(i => i.IsEncrypted);

    public event Action? Changed;

    public async Task HydrateAsync(CancellationToken ct = default)
    {
        var json = await _storage.GetAsync(StorageKey, ct).ConfigureAwait(false);
        _items.Clear();

        if (!string.IsNullOrWhiteSpace(json))
        {
            try
            {
                var loaded = JsonSerializer.Deserialize<List<RecentItem>>(json);
                if (loaded is not null)
                {
                    _items.AddRange(loaded);
                }
            }
            catch (JsonException)
            {
                // Corrupt store: ignore and start clean.
            }
        }

        if (_items.Count == 0 && _samples)
        {
            SeedSample();
        }

        Changed?.Invoke();
    }

    /// <summary>D-191: the encoding chosen for this text file, or null for Automatic (also when the file is not
    /// in Recents). Give it to <see cref="TextViewService.Load(string, int?)"/>.</summary>
    public int? TextEncodingFor(string path) => Find(path)?.TextCodePage;

    /// <summary>D-191: remembers the encoding chosen for this text file, for as long as it stays in Recents; null
    /// (Automatic) forgets it. On this machine only; the file is not touched. False when the file is not in
    /// Recents, so there is nowhere to remember it.</summary>
    public async Task<bool> SetTextEncodingAsync(string path, int? codePage, CancellationToken ct = default)
    {
        int at = _items.FindIndex(i => string.Equals(i.Path, path, StringComparison.OrdinalIgnoreCase));
        if (at < 0)
        {
            return false;
        }

        if (_items[at].TextCodePage != codePage)
        {
            _items[at] = _items[at] with { TextCodePage = codePage };
            await _storage.SetAsync(StorageKey, JsonSerializer.Serialize(_items), ct).ConfigureAwait(false);
            Changed?.Invoke();
        }

        return true;
    }

    private RecentItem? Find(string path) =>
        _items.Find(i => string.Equals(i.Path, path, StringComparison.OrdinalIgnoreCase));

    public async Task TouchAsync(RecentItem item, CancellationToken ct = default)
    {
        // Opening a file again must not forget the encoding chosen for it (the callers build a fresh entry).
        if (item.TextCodePage is null && Find(item.Path)?.TextCodePage is { } chosen)
        {
            item = item with { TextCodePage = chosen };
        }

        _items.RemoveAll(i => string.Equals(i.Path, item.Path, StringComparison.OrdinalIgnoreCase));
        _items.Insert(0, item);
        if (_items.Count > 20)
        {
            _items.RemoveRange(20, _items.Count - 20);
        }

        await _storage.SetAsync(StorageKey, JsonSerializer.Serialize(_items), ct).ConfigureAwait(false);
        Changed?.Invoke();
    }

    private void SeedSample()
    {
        var now = DateTimeOffset.Now;
        _items.AddRange(new[]
        {
            new RecentItem("patient_chart.pdf", "~/Documents/Chuvadi/patient_chart.pdf", DocumentFormat.Pdf, now.AddMinutes(-9), false),
            new RecentItem("consent_form.pdf", "~/Documents/Chuvadi/consent_form.pdf", DocumentFormat.Pdf, now.AddHours(-1), true),
            new RecentItem("q2_revenue.xlsx", "~/Documents/Chuvadi/q2_revenue.xlsx", DocumentFormat.Xlsx, now.AddHours(-5), false),
            new RecentItem("census_report.docx", "~/Documents/Chuvadi/census_report.docx", DocumentFormat.Docx, now.AddDays(-1), false),
            new RecentItem("aerb_submission.pdf", "~/Documents/Chuvadi/aerb_submission.pdf", DocumentFormat.Pdf, now.AddDays(-2), false),
        });
    }
}
