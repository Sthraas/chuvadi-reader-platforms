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
    internal static readonly string[] DocumentTypes = { "pdf", "docx", "xlsx", "md", "markdown", "txt", "log", "html", "htm" };
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

    /// <summary>
    /// Runs a panel on the main thread's next run-loop turn — always, even when called on the main thread.
    /// The Ui calls the picker from a click handler, which runs inside WebKit's script-message callback; a
    /// modal panel run right there nests a run loop inside Blazor's event dispatch, Blazor's next messages
    /// arrive re-entrantly and its renderer fails ("An error occurred" — Mac Test M-16). Posted, the click
    /// handler returns to WebKit first and the panel runs from a clean turn of the loop.
    /// </summary>
    private static Task<T> OnMain<T>(Func<T> func)
    {
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
            finally
            {
                MacPageKeys.Refocus(); // M-08/M-21/M-23: the panel took the keyboard; give it back to the page
            }
        });
        return tcs.Task;
    }
}
