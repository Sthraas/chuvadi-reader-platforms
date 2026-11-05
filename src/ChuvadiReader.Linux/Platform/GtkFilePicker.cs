using System.Collections.Concurrent;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Native file and folder dialogs through GtkFileDialog, which uses the desktop portal: GNOME
/// users get the GNOME dialog and KDE users the KDE one. Titles and filters match the Windows
/// host (WpfFilePicker). GTK's save dialog asks before overwriting.
/// </summary>
public sealed class GtkFilePicker : IFilePicker
{
    private const int Open = 0;
    private const int OpenMultiple = 1;
    private const int Save = 2;
    private const int Folder = 3;

    private static readonly ConcurrentDictionary<int, TaskCompletionSource<string[]>> Pending = new();
    private static int _nextToken;

    private readonly SaveFolderService _saveFolders;

    static GtkFilePicker()
    {
        GtkHost.DialogResult += (token, paths) =>
        {
            if (Pending.TryRemove(token, out var tcs))
            {
                tcs.TrySetResult(paths);
            }
        };
    }

    public GtkFilePicker(SaveFolderService saveFolders) => _saveFolders = saveFolders;

    private const string DocumentFilters =
        "All supported|*.pdf;*.docx;*.xlsx;*.md;*.markdown;*.txt;*.log;*.html;*.htm\n" +
        "Documents|*.pdf;*.docx;*.xlsx\n" +
        "PDF|*.pdf\n" +
        "Word|*.docx\n" +
        "Excel|*.xlsx\n" +
        "Markdown|*.md;*.markdown\n" +
        "Text|*.txt;*.log\n" +
        "HTML|*.html;*.htm\n" +
        "All files|*";

    public async Task<string?> PickDocumentAsync(CancellationToken ct = default) =>
        First(await Show(Open, "Open a document", null, null, DocumentFilters, ct));

    public async Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default) =>
        await Show(OpenMultiple, "Add PDF documents", null, null, "PDF|*.pdf\nAll files|*", ct);

    public async Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default) =>
        WithExtension(First(await Show(Save, "Save PDF", _saveFolders.ResolveSaveFolder(), suggestedName, "PDF|*.pdf", ct)), ".pdf");

    public async Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default) =>
        WithExtension(First(await Show(Save, "Save bench session", _saveFolders.ResolveSaveFolder(), suggestedName, "Chuvadi session|*.json", ct)), ".json");

    public async Task<string?> PickOpenSessionAsync(CancellationToken ct = default) =>
        First(await Show(Open, "Open bench session", null, null, "Chuvadi session|*.json\nAll files|*", ct));

    public async Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default) =>
        WithExtension(First(await Show(Save, "Save image", _saveFolders.ResolveSaveFolder(), suggestedName, "PNG image|*.png", ct)), ".png");

    public async Task<string?> PickFolderAsync(CancellationToken ct = default) =>
        First(await Show(Folder, "Choose output folder", _saveFolders.ResolveSaveFolder(), null, null, ct));

    public async Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default) =>
        await Show(OpenMultiple, "Fetch images", null, null,
            "Images|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff;*.webp\nAll files|*", ct);

    public async Task<string?> PickCertificateAsync(CancellationToken ct = default) =>
        First(await Show(Open, "Choose a signing certificate", null, null,
            "Certificate with private key|*.pfx;*.p12\nAll files|*", ct));

    private static Task<string[]> Show(int kind, string title, string? folder, string? name, string? filters, CancellationToken ct)
    {
        var token = Interlocked.Increment(ref _nextToken);
        var tcs = new TaskCompletionSource<string[]>(TaskCreationOptions.RunContinuationsAsynchronously);
        Pending[token] = tcs;
        if (ct.CanBeCanceled)
        {
            // The dialog stays up until the person answers; a cancelled caller just stops waiting.
            ct.Register(() =>
            {
                if (Pending.TryRemove(token, out var t))
                {
                    t.TrySetCanceled(ct);
                }
            });
        }

        var initialFolder = folder is not null && Directory.Exists(folder) ? folder : null;
        GtkHost.Post(() => Native.FileDialog(kind, token, title, initialFolder, name, filters));
        return tcs.Task;
    }

    private static string? First(string[] paths) => paths.Length > 0 ? paths[0] : null;

    /// <summary>The Windows dialog adds the extension when the person leaves it off; do the same.</summary>
    private static string? WithExtension(string? path, string extension) =>
        path is null || Path.HasExtension(path) ? path : path + extension;
}
