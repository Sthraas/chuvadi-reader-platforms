using ChuvadiReader.Core.Reader;
using IFilePicker = ChuvadiReader.Core.Reader.IFilePicker;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// File pickers on Android, through the system document picker (Storage Access Framework).
///
/// Open pickers use MAUI's own <see cref="FilePicker"/>, which streams the chosen document into
/// the app's cache and returns that working copy — Core keeps opening by path, and the original
/// is never touched.
///
/// Save and folder pickers are NOT wired yet. Android has no writable path to hand back: a save
/// target is a content URI, so the result has to be copied back after Core writes it. How that
/// write-back works is the platform-interface decision A-02 (docs/android/DECISIONS.md), shared
/// with the Foundation chat. Until then they return null (the UI treats it as "cancelled"), and
/// this gap is listed in the Android status, not hidden.
/// </summary>
public sealed class AndroidFilePicker : IFilePicker
{
    public async Task<string?> PickDocumentAsync(CancellationToken ct = default)
        => (await PickAsync(DocumentTypes.AllSupported, multiple: false).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default)
        => PickAsync(DocumentTypes.PdfOnly, multiple: true);

    public async Task<string?> PickOpenSessionAsync(CancellationToken ct = default)
        => (await PickAsync(new[] { "application/json", "application/octet-stream" }, multiple: false).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default)
        => PickAsync(DocumentTypes.Images, multiple: true);

    public async Task<string?> PickCertificateAsync(CancellationToken ct = default)
        => (await PickAsync(DocumentTypes.Certificates, multiple: false).ConfigureAwait(false)).FirstOrDefault();

    // ── Pending A-02 (write-back to a content URI) ──
    public Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);

    public Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);

    public Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);

    public Task<string?> PickFolderAsync(CancellationToken ct = default) => Task.FromResult<string?>(null);

    private static async Task<IReadOnlyList<string>> PickAsync(string[] mimeTypes, bool multiple)
    {
        var options = new PickOptions
        {
            FileTypes = new FilePickerFileType(new Dictionary<DevicePlatform, IEnumerable<string>>
            {
                [DevicePlatform.Android] = mimeTypes,
            }),
        };

        try
        {
            var picked = await MainThread.InvokeOnMainThreadAsync(async () => multiple
                ? (await FilePicker.Default.PickMultipleAsync(options).ConfigureAwait(true))?.Where(f => f is not null).Select(f => f!.FullPath).ToList()
                : (await FilePicker.Default.PickAsync(options).ConfigureAwait(true)) is { } one ? new List<string> { one.FullPath } : null).ConfigureAwait(false);
            return picked ?? (IReadOnlyList<string>)Array.Empty<string>();
        }
        catch (PermissionException)
        {
            return Array.Empty<string>();
        }
    }
}
