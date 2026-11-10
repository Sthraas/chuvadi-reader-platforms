using global::Android.OS;
using AWebView = global::Android.Webkit.WebView;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// AT-11: when Android ends the app in the background (memory pressure) and the person comes back,
/// Android recreates the activity with the state it saved — and the app must come back on the screen
/// they left, as every Android app does. The tabs themselves already survive (TabsService saves them
/// on every change and Home rebuilds them), but a fresh WebView starts on Home, so on the phone the
/// Reader, its tab and its page were gone from view (11 of 11 in Android Test's runs).
///
/// The activity's saved state carries the Ui's route; a recreated activity starts the WebView there
/// (<c>BlazorWebView.StartPath</c>), and the Reader reopens the active tab at its page. A cold start (no
/// saved state — the person closed the app, or rebooted) still opens on Home, as on Windows.
/// </summary>
public static class SessionRoute
{
    private const string Key = "chuvadi.route";
    private static WeakReference<AWebView>? _webView;
    private static string? _pending;

    /// <summary>The WebView whose route is saved (MainPage, on BlazorWebViewInitialized).</summary>
    public static void Track(AWebView webView) => _webView = new WeakReference<AWebView>(webView);

    /// <summary>MainActivity.OnSaveInstanceState: the route the Ui is on, if it isn't Home.</summary>
    public static void Save(Bundle state)
    {
        if (_webView?.TryGetTarget(out var web) == true && RouteOf(web.Url) is { } route)
        {
            state.PutString(Key, route);
        }
    }

    /// <summary>MainActivity.OnCreate, before the window is made: the route to come back to, if any.</summary>
    public static void Restore(Bundle? state) => _pending = state?.GetString(Key);

    /// <summary>The WebView's start path: the saved route once, then Home.</summary>
    public static string TakeStartPath()
    {
        var route = _pending;
        _pending = null;
        return route ?? "/";
    }

    /// <summary>The app-relative route of a page URL on the app's own origin ("/reader", "/settings?s=x"); null for Home or anything else.</summary>
    public static string? RouteOf(string? url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || uri.Host != "0.0.0.1")
        {
            return null;
        }

        var route = uri.PathAndQuery;
        return route.Length > 1 && route.StartsWith('/') && !route.StartsWith("//", StringComparison.Ordinal)
            && !route.StartsWith("/_", StringComparison.Ordinal) && !route.EndsWith(".html", StringComparison.OrdinalIgnoreCase)
            ? route
            : null;
    }
}
