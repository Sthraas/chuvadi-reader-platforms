using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting.Desktop;
using ChuvadiReader.Mac.Platform;
using Microsoft.AspNetCore.Components.WebView;
using Microsoft.AspNetCore.Components.WebView.Maui;
using WebKit;

namespace ChuvadiReader.Mac;

/// <summary>The single page: a BlazorWebView showing ChuvadiReader.Ui.App, exactly as the
/// Windows host does, plus the Mac-side wiring (zoom, file drop, window chrome).</summary>
public sealed class MainPage : ContentPage
{
    private static BlazorWebView? _web;

    /// <summary>The page's WKWebView, once BlazorWebView has created it.</summary>
    public static WKWebView? WebKitView { get; private set; }
    private readonly IServiceProvider _services;

    /// <summary>Runs <paramref name="action"/> on the Blazor renderer's dispatcher — used by the
    /// native menu bar so a menu item behaves exactly like the same click inside the Ui.</summary>
    /// <summary>True once the BlazorWebView exists, so <see cref="Dispatch"/> can run work.</summary>
    public static bool CanDispatch => _web is not null;

    public static void Dispatch(Func<Task> action)
    {
        var web = _web;
        if (web is null)
        {
            return;
        }

        _ = DispatchAsync(web, action);
    }

    /// <summary>TryDispatchAsync is false until Blazor has started in the WebView; anything asked for
    /// before then runs on the main thread instead of being dropped.</summary>
    private static async Task DispatchAsync(BlazorWebView web, Func<Task> action)
    {
        if (!await web.TryDispatchAsync(sp => { _ = action(); }))
        {
            UIKit.UIApplication.SharedApplication.BeginInvokeOnMainThread(() => _ = action());
        }
    }

    internal static IDisposable? LoadingMarks; // kept alive for the app's life

    public MainPage(IServiceProvider services)
    {
        _services = services;

        // Pre-paint background matches the saved theme, so there's no flash before the
        // WebView content paints (same colours as the Windows host, tokens.css surface-mid).
        var theme = (_services.GetService<FileAppStorage>()?.GetSync("theme") ?? string.Empty).Trim().ToLowerInvariant();
        BackgroundColor = Color.FromArgb(theme switch
        {
            "dark" => "#1B1410",
            "palm" => "#EBE5C9",
            "indigo" => "#EDF0F6",
            "contrast" => "#F5F5F2",
            _ => "#F2EAD6",
        });

        // Edge to edge: the page runs under the (transparent, hidden) title bar (Mac Test M-04).
        SafeAreaEdges = SafeAreaEdges.None;

        _web = CreateWebView(null);
        Content = _web;

        // M-18 (D-154): if WebKit's content process ends, a fresh BlazorWebView reopens the same screen.
        WebContentRecovery.Reopen = route => UIKit.UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            var old = _web;
            _web = CreateWebView(route);
            Content = _web;
            if (old is not null)
            {
                old.BlazorWebViewInitialized -= OnWebViewInitialized;
                old.UrlLoading -= OnUrlLoading;
            }

            _services.GetService<ShellService>()?.Notify(WebContentRecovery.Message);
        });
    }

    private BlazorWebView CreateWebView(string? startPath)
    {
        var web = new BlazorWebView { HostPage = "wwwroot/index.html", BackgroundColor = BackgroundColor };
        if (!string.IsNullOrEmpty(startPath) && startPath != "/")
        {
            web.StartPath = startPath;
        }

        web.RootComponents.Add(new RootComponent
        {
            Selector = "#app",
            ComponentType = typeof(ChuvadiReader.Ui.App),
        });
        web.BlazorWebViewInitialized += OnWebViewInitialized;
        web.UrlLoading += OnUrlLoading;
        return web;
    }

    /// <summary>
    /// The HTML viewer shows a document in an &lt;iframe srcdoc&gt; (sandboxed, no scripts). MAUI's Mac handler
    /// treats any URL outside the app's origin as a link to open in the browser — including the frame's own
    /// about:srcdoc — so the frame was cancelled and stayed blank. WebView2 on Windows loads it in place;
    /// so does this. Real links still go to the browser.
    /// </summary>
    private static void OnUrlLoading(object? sender, UrlLoadingEventArgs e)
    {
        if (e.Url.Scheme == "about" && e.Url.OriginalString is "about:srcdoc" or "about:blank")
        {
            e.UrlLoadingStrategy = UrlLoadingStrategy.OpenInWebView;
        }
    }

    private void OnWebViewInitialized(object? sender, BlazorWebViewInitializedEventArgs e)
    {
        StartupTimeline.Mark("webview-ready");
        var view = e.WebView;
        WebKitView = view;
        PageErrorBridge.Attach(view, _services); // M-19: page errors to the D-132 log
        MacImmersive.Attach(view); // M-21: Esc leaves Immersive
        MacPageKeys.WatchWindow(); // M-08/M-23: the page has the keyboard whenever the window is key
        WebContentRecovery.Attach(view, _services.GetRequiredService<Microsoft.Extensions.Logging.ILoggerFactory>().CreateLogger("ChuvadiReader.Mac.WebContent"));

        // No page zoom gestures — only the Interface size setting zooms (as on Windows).
        // (Catalyst's WKWebView zooms through its scroll view.) The reader's own pinch-to-zoom of
        // pages is handled inside the UI and still reaches it as wheel/gesture events.
        view.ScrollView.MinimumZoomScale = 1;
        view.ScrollView.MaximumZoomScale = 1;
        view.ScrollView.BouncesZoom = false;
        // No automatic inset for the title-bar area: the Ui's own top bar sits at the top edge (M-04).
        view.ScrollView.ContentInsetAdjustmentBehavior = UIKit.UIScrollViewContentInsetAdjustmentBehavior.Never;
        // Don't let the WKWebView paint white before the first frame.
        view.Opaque = false;
        view.BackgroundColor = UIKit.UIColor.Clear;

        _services.GetService<MacUiScale>()?.Attach(view);
        FileDrop.Attach(view, _services);
        LoadingMarks = WebKitPrewarm.MarkLoading(view, "wk-ui"); // M-06: when the Ui's page load is asked for and done
        _services.GetService<MacWindowControls>()?.ApplyChrome();
    }
}
