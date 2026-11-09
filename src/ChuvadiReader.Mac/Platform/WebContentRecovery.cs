using Foundation;
using Microsoft.Extensions.Logging;
using ObjCRuntime;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-18 (D-154): when WebKit's content process ends — on macOS 26 an Accessibility press (VoiceOver, Voice
/// Control) on some controls crashes it inside Apple's own accessibility code — the page is gone and the old Blazor
/// session with it. Instead of a blank page with "An error occurred", the host logs it, builds a fresh BlazorWebView
/// at the same screen and shows a plain message. At most <see cref="MaxPerMinute"/> times a minute, so a page that
/// keeps crashing cannot loop.
///
/// MAUI owns the WKWebView's navigation delegate (it decides which links stay in the app). A small proxy takes its
/// place: it answers webViewWebContentProcessDidTerminate: itself and forwards every other message to MAUI's
/// delegate through Objective-C message forwarding, so MAUI's behaviour is unchanged.
/// </summary>
internal static class WebContentRecovery
{
    public const int MaxPerMinute = 3;
    public const string Message = "Part of Chuvadi stopped unexpectedly and was reopened. Your open documents are as you left them.";

    private static readonly Queue<DateTime> Recent = new();
    private static NavigationProxy? _proxy; // WKWebView holds its delegate weakly
    private static IDisposable? _urlWatch;

    /// <summary>The app route the page last showed ("/reader", "/settings?section=…"), for reopening there.</summary>
    public static string LastRoute { get; private set; } = "/";

    /// <summary>Set by MainPage: builds a fresh BlazorWebView at the route and shows the message.</summary>
    public static Action<string>? Reopen { get; set; }

    public static void Attach(WKWebView view, ILogger log)
    {
        _urlWatch?.Dispose();
        _urlWatch = view.AddObserver("URL", NSKeyValueObservingOptions.New, _ =>
        {
            if (view.Url is { } url && url.Scheme == "app")
            {
                LastRoute = (url.Path is { Length: > 0 } p ? p : "/") + (string.IsNullOrEmpty(url.Query) ? string.Empty : "?" + url.Query);
            }
        });
        Wrap(view, log);
        // MAUI may set its own delegate after the WebView is created; wrap again once it has.
        NSTimer.CreateScheduledTimer(2.0, false, t => Wrap(view, log));
    }

    /// <summary>Puts the proxy in front of MAUI's delegate (again, if MAUI set its own after us).</summary>
    public static void Wrap(WKWebView view, ILogger log)
    {
        var current = view.NavigationDelegate as NSObject;
        if (current is NavigationProxy)
        {
            return;
        }

        _proxy = new NavigationProxy(current, log);
        view.NavigationDelegate = _proxy;
        MacSmoke.Log("webcontent-proxy " + (current?.Class.Name ?? "none"));
    }

    private static void Ended(WKWebView view, ILogger log)
    {
        var route = LastRoute;
        log.LogError("WebKit's content process ended; the page was reopened at {Route}", route);
        MacSmoke.Log("webcontent-ended route=" + route);

        var now = DateTime.UtcNow;
        while (Recent.Count > 0 && now - Recent.Peek() > TimeSpan.FromMinutes(1))
        {
            Recent.Dequeue();
        }

        if (Recent.Count >= MaxPerMinute)
        {
            log.LogError("WebKit's content process ended {Count} times in a minute; not reopening again", Recent.Count + 1);
            return;
        }

        Recent.Enqueue(now);
        view.StopLoading();
        Reopen?.Invoke(route);
    }

    /// <summary>Answers the termination callback; everything else goes to MAUI's own delegate.</summary>
    private sealed class NavigationProxy : NSObject, IWKNavigationDelegate
    {
        private readonly NSObject? _inner;
        private readonly ILogger _log;

        public NavigationProxy(NSObject? inner, ILogger log)
        {
            _inner = inner;
            _log = log;
        }

        [Export("webViewWebContentProcessDidTerminate:")]
        public void ContentProcessDidTerminate(WKWebView webView) => Ended(webView, _log);

        public override bool RespondsToSelector(Selector? sel)
        {
            if (sel is null)
            {
                return false;
            }

            return sel.Name == "webViewWebContentProcessDidTerminate:" || base.RespondsToSelector(sel) || (_inner?.RespondsToSelector(sel) ?? false);
        }

        [Export("forwardingTargetForSelector:")]
        public NSObject? ForwardingTargetForSelector(Selector sel) => _inner;
    }
}
