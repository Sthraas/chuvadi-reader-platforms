using ChuvadiReader.Core.Reader;
using Foundation;
using UIKit;
using UniformTypeIdentifiers;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Files dropped from Finder anywhere on the window open in the reader — or join the Bench shelf
/// when the Bench is open — exactly as in the Windows host (MainWindow.OnFileDrop). The web layer
/// never sees real paths; the host resolves them and hands them to Core.
/// </summary>
internal sealed class FileDrop : NSObject, IUIDropInteractionDelegate
{
    // The same types as the Open panel (HANDOFF §2; fixes finding F1 for the Mac).
    private static readonly string[] DropExtensions = MacFilePicker.DocumentTypes.Select(e => "." + e).ToArray();

    private readonly IServiceProvider _services;

    private FileDrop(IServiceProvider services) => _services = services;

    public static void Attach(UIView view, IServiceProvider services)
    {
        // Added to the WKWebView itself so it is consulted before the page's own drop handling.
        view.AddInteraction(new UIDropInteraction(new FileDrop(services)));
    }

    private static bool IsSupported(string path)
        => DropExtensions.Contains(Path.GetExtension(path).ToLowerInvariant());

    [Export("dropInteraction:canHandleSession:")]
    public bool CanHandleSession(UIDropInteraction interaction, IUIDropSession session)
        => session.HasConformingItems(new[] { UTTypes.FileUrl.Identifier, UTTypes.Item.Identifier });

    [Export("dropInteraction:sessionDidUpdate:")]
    public UIDropProposal SessionDidUpdate(UIDropInteraction interaction, IUIDropSession session)
        => new(session.Items.Length > 0 ? UIDropOperation.Copy : UIDropOperation.Forbidden);

    [Export("dropInteraction:performDrop:")]
    public void PerformDrop(UIDropInteraction interaction, IUIDropSession session)
    {
        var items = session.Items;
        var pending = items.Length;
        // Indexed so the order matches the drag order, whatever order the callbacks return in.
        var resolved = new string?[items.Length];
        var gate = new object();

        for (var i = 0; i < items.Length; i++)
        {
            var index = i;
            // In-place: Finder hands us the original file's URL, not a temporary copy, so saving
            // and Recent files refer to the real document (as on Windows).
            items[i].ItemProvider.LoadInPlaceFileRepresentation(UTTypes.Item.Identifier, (url, _, _) =>
            {
                lock (gate)
                {
                    if (url?.Path is { Length: > 0 } p && IsSupported(p))
                    {
                        resolved[index] = p;
                    }

                    if (--pending == 0)
                    {
                        var found = resolved.Where(r => r is not null).Select(r => r!).ToArray();
                        UIApplication.SharedApplication.BeginInvokeOnMainThread(() => Deliver(found));
                    }
                }
            });
        }
    }

    private void Deliver(string[] supported)
    {
        if (supported.Length == 0)
        {
            return;
        }

        if (_services.GetService(typeof(BenchDropService)) is BenchDropService bench && bench.IsBenchActive)
        {
            bench.Drop(supported);
            return;
        }

        if (_services.GetService(typeof(OpenDocumentService)) is OpenDocumentService open)
        {
            open.Request(supported[0]);
        }
    }
}
