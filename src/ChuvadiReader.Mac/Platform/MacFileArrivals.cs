using ChuvadiReader.Hosting;
using Foundation;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Hands files that arrive from outside — a Finder drop on the window, Finder "Open With", a double-click,
/// a drop on the Dock icon, files handed over at launch — to the kit's <see cref="IncomingFiles"/>, the one
/// route every platform uses (HANDOFF §2, D-83: Bench shelf when open, otherwise one Reader tab per file,
/// in order; files before the first render wait for it). macOS itself keeps Chuvadi single-instance: a file
/// opened while it runs reaches this running copy through SceneOpenUrl.
/// Delivery runs on the Blazor dispatcher once the WebView exists, so the Ui sees it like a click.
/// </summary>
internal static class MacFileArrivals
{
    public static void Route(IServiceProvider services, IEnumerable<NSUrl> urls)
        => Route(services, urls.Where(u => u.IsFileUrl).Select(u => u.Path).OfType<string>());

    public static void Route(IServiceProvider services, IEnumerable<string> paths)
    {
        var files = paths.ToArray();
        if (files.Length == 0)
        {
            return;
        }

        var incoming = services.GetRequiredService<IncomingFiles>();
        if (MainPage.CanDispatch)
        {
            MainPage.Dispatch(() =>
            {
                incoming.Receive(files);
                return Task.CompletedTask;
            });
        }
        else
        {
            // Before the WebView exists the Ui hasn't rendered, so IncomingFiles only queues them.
            incoming.Receive(files);
        }
    }
}
