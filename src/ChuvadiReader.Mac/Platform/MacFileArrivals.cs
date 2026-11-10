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
        // Before the Ui's first render, IncomingFiles only queues — call it directly (Blazor's dispatcher
        // may not exist yet, and a dispatch then is dropped: Mac Test M-02, file given at launch).
        var ready = services.GetRequiredService<ChuvadiReader.Core.Lifecycle.IAppReadySignal>().IsReady;
        if (ready && MainPage.CanDispatch)
        {
            MainPage.Dispatch(() =>
            {
                incoming.Receive(files);
                return Task.CompletedTask;
            });
        }
        else
        {
            incoming.Receive(files);
        }

        // M-08 / M-23: files arrive while another app (Finder) had the keyboard; hand it to the page.
        UIKit.UIApplication.SharedApplication.BeginInvokeOnMainThread(MacPageKeys.Refocus);
    }
}
