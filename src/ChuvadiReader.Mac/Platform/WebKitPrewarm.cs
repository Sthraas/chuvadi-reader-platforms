using Foundation;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-06 — startup. Measured on the Mac runner: WebView ready at ~0.75 s, but the page's
/// navigation only starts ~1.4 s later — WebKit launching its content process on the first load.
/// Every WKWebView in the app shares WebKit's process pool, so a tiny off-screen WKWebView loading an
/// empty page at the very start of launch starts that process while MAUI is still building; the Ui's
/// WebView then finds it running. Released once the Ui has rendered.
/// </summary>
internal static class WebKitPrewarm
{
    private static WKWebView? _warm;

    public static void Start()
    {
        try
        {
            _warm = new WKWebView(CoreGraphics.CGRect.Empty, new WKWebViewConfiguration());
            _warm.LoadHtmlString("<!doctype html><title></title>", new NSUrl("about:blank"));
            StartupTimeline.Mark("webkit-prewarm");
        }
        catch
        {
            _warm = null; // only an optimisation
        }
    }

    public static void Release()
    {
        var w = _warm;
        _warm = null;
        if (w is not null)
        {
            w.StopLoading();
            w.Dispose();
        }
    }
}
