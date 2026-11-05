using ChuvadiReader.Core.Reader;
using Foundation;
using UIKit;
using Panel = ChuvadiReader.Mac.Platform.AppKitBridge.PanelOptions;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Native macOS open / save / folder panels (NSOpenPanel, NSSavePanel). Same dialogs, titles
/// and file types as the Windows host's WpfFilePicker. The panels are application-modal, as
/// the Windows dialogs are, and return real file-system paths (the app is not sandboxed —
/// see docs/mac/README.md, "Sandbox").
/// </summary>
public sealed class MacFilePicker : IFilePicker
{
    private static readonly string[] DocumentTypes = { "pdf", "docx", "xlsx", "md", "markdown", "txt", "log", "html", "htm" };
    private static readonly string[] ImageTypes = { "png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp" };

    public Task<string?> PickDocumentAsync(CancellationToken ct = default)
        => Open(new Panel { Title = "Open a document", Extensions = DocumentTypes });

    public Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default)
        => OpenMany(new Panel { Title = "Add PDF documents", Extensions = new[] { "pdf" }, Multiple = true });

    public Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default)
        => Save(new Panel { Title = "Save PDF", Extensions = new[] { "pdf" }, SuggestedName = WithExtension(suggestedName, ".pdf") });

    public Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default)
        => Save(new Panel { Title = "Save bench session", Extensions = new[] { "json" }, SuggestedName = WithExtension(suggestedName, ".json") });

    public Task<string?> PickOpenSessionAsync(CancellationToken ct = default)
        => Open(new Panel { Title = "Open bench session", Extensions = new[] { "json" } });

    public Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default)
        => Save(new Panel { Title = "Save image", Extensions = new[] { "png" }, SuggestedName = WithExtension(suggestedName, ".png") });

    public Task<string?> PickFolderAsync(CancellationToken ct = default)
        => Open(new Panel { Title = "Choose output folder", Folders = true });

    public Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default)
        => OpenMany(new Panel { Title = "Fetch images", Extensions = ImageTypes, Multiple = true });

    public Task<string?> PickCertificateAsync(CancellationToken ct = default)
        => Open(new Panel { Title = "Choose a signing certificate", Extensions = new[] { "pfx", "p12" } });

    private static Task<string?> Open(Panel options)
        => OnMain(() => AppKitBridge.RunOpenPanel(options) is { Count: > 0 } paths ? paths[0] : null);

    private static Task<IReadOnlyList<string>> OpenMany(Panel options)
        => OnMain(() => AppKitBridge.RunOpenPanel(options));

    private static Task<string?> Save(Panel options)
        => OnMain(() => AppKitBridge.RunSavePanel(options));

    private static string WithExtension(string name, string ext)
    {
        var n = string.IsNullOrWhiteSpace(name) ? "Untitled" : name;
        return n.EndsWith(ext, StringComparison.OrdinalIgnoreCase) ? n : n + ext;
    }

    private static Task<T> OnMain<T>(Func<T> func)
    {
        if (NSThread.IsMain)
        {
            return Task.FromResult(func());
        }

        var tcs = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            try
            {
                tcs.SetResult(func());
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        });
        return tcs.Task;
    }
}
