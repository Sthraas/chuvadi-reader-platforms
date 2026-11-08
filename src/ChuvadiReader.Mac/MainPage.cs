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

        var web = new BlazorWebView { HostPage = "wwwroot/index.html", BackgroundColor = BackgroundColor };
        web.RootComponents.Add(new RootComponent
        {
            Selector = "#app",
            ComponentType = typeof(ChuvadiReader.Ui.App),
        });
        web.BlazorWebViewInitialized += OnWebViewInitialized;
        _web = web;
        Content = web;
    }

    private void OnWebViewInitialized(object? sender, BlazorWebViewInitializedEventArgs e)
    {
        StartupTimeline.Mark("webview-ready");
        var view = e.WebView;
        WebKitView = view;

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
