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
    private readonly IServiceProvider _services;

    /// <summary>Runs <paramref name="action"/> on the Blazor renderer's dispatcher — used by the
    /// native menu bar so a menu item behaves exactly like the same click inside the Ui.</summary>
    public static void Dispatch(Func<Task> action)
    {
        var web = _web;
        if (web is null)
        {
            return;
        }

        _ = web.TryDispatchAsync(services => { _ = action(); });
    }

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

        // No page zoom gestures — only the Interface size setting zooms (as on Windows).
        // (Catalyst's WKWebView zooms through its scroll view.) The reader's own pinch-to-zoom of
        // pages is handled inside the UI and still reaches it as wheel/gesture events.
        view.ScrollView.MinimumZoomScale = 1;
        view.ScrollView.MaximumZoomScale = 1;
        view.ScrollView.BouncesZoom = false;
        // Don't let the WKWebView paint white before the first frame.
        view.Opaque = false;
        view.BackgroundColor = UIKit.UIColor.Clear;

        _services.GetService<MacUiScale>()?.Attach(view);
        FileDrop.Attach(view, _services.GetRequiredService<MacIncomingFiles>());
        _services.GetService<MacWindowControls>()?.ApplyChrome();
    }
}
