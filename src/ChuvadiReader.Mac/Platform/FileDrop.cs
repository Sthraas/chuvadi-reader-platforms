using Foundation;
using UIKit;
using UniformTypeIdentifiers;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Files dropped from Finder anywhere on the window. They are resolved to their real paths (in place,
/// not copies, so saving and Recent files refer to the real document) and handed to
/// the kit's IncomingFiles (via <see cref="MacFileArrivals"/>), which sends them to the Bench or the Reader.
/// </summary>
internal sealed class FileDrop : NSObject, IUIDropInteractionDelegate
{
    private readonly IServiceProvider _services;

    private FileDrop(IServiceProvider services) => _services = services;

    public static void Attach(UIView view, IServiceProvider services)
    {
        // Added to the WKWebView itself so it is consulted before the page's own drop handling.
        view.AddInteraction(new UIDropInteraction(new FileDrop(services)));
    }

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
            items[i].ItemProvider.LoadInPlaceFileRepresentation(UTTypes.Item.Identifier, (url, _, _) =>
            {
                lock (gate)
                {
                    if (url?.Path is { Length: > 0 } p)
                    {
                        resolved[index] = p;
                    }

                    if (--pending == 0)
                    {
                        MacFileArrivals.Route(_services, resolved.OfType<string>());
                    }
                }
            });
        }
    }
}
