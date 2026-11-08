using Microsoft.AspNetCore.Components.WebView;
using Microsoft.AspNetCore.Components.WebView.Maui;

namespace ChuvadiReader.Android;

/// <summary>The MAUI application: one window holding one full-screen BlazorWebView.</summary>
public sealed class App : Microsoft.Maui.Controls.Application
{
    private Microsoft.Maui.Controls.Window? _window;

    protected override Microsoft.Maui.Controls.Window CreateWindow(IActivationState? activationState)
        => _window = new(StartPage()) { Title = "Chuvadi Reader" };

    /// <summary>The Reader, or the "update Android System WebView" screen when the WebView is too old (D-105).</summary>
    private static Page StartPage()
        => Platform.WebViewSupport.IsSupported(out var version) ? new MainPage() : Platform.WebViewSupport.UpdatePage(version);

    /// <summary>Back from Google Play with a new enough WebView: swap the update screen for the Reader.</summary>
    public void RecheckWebView()
    {
        if (_window is { Page: not ChuvadiReader.Android.MainPage } && Platform.WebViewSupport.IsSupported(out _))
        {
            _window.Page = new MainPage();
        }
    }
}

/// <summary>Hosts ChuvadiReader.Ui.App — the same root component the Windows host uses.</summary>
public sealed class MainPage : ContentPage
{
    public MainPage()
    {
        // Pre-paint colour matches the default (Cream paper) theme so there is no white flash.
        BackgroundColor = Color.FromArgb("#F2EAD6");

        var web = new BlazorWebView { HostPage = "wwwroot/index.html" };
        web.RootComponents.Add(new RootComponent
        {
            Selector = "#app",
            ComponentType = typeof(ChuvadiReader.Ui.App),
        });
        web.BlazorWebViewInitialized += OnInitialized;

        // BlazorWebView registers its own Back callback (WebView history) when its handler connects;
        // put the activity's (the Ui's first chance) back in front once that has happened.
        web.HandlerChanged += (_, _) => MainThread.BeginInvokeOnMainThread(
            () => (Microsoft.Maui.ApplicationModel.Platform.CurrentActivity as MainActivity)?.PutBackFirst());
        Content = web;
    }

    private static void OnInitialized(object? sender, BlazorWebViewInitializedEventArgs e)
    {
        // Transparent until the page paints, so a resume or first frame shows the page colour behind
        // it instead of the WebView's default white (round 4: a white frame on relaunch).
        e.WebView.SetBackgroundColor(global::Android.Graphics.Color.Transparent);

        // By now BlazorWebView has registered its Back callback: put the Ui's first chance in front.
        MainThread.BeginInvokeOnMainThread(
            () => (Microsoft.Maui.ApplicationModel.Platform.CurrentActivity as MainActivity)?.PutBackFirst());

        var settings = e.WebView.Settings;

        // Same rule as Windows: the WebView itself never zooms; pinch-zoom on the page canvas is
        // handled by the UI (reader.js) so the app chrome never moves.
        settings.SetSupportZoom(false);
        settings.BuiltInZoomControls = false;
        settings.DisplayZoomControls = false;

        // "Nothing leaves this device": the WebView only ever loads the app's own bundled assets.
        settings.AllowContentAccess = false;
        settings.AllowFileAccess = false;
        settings.SetGeolocationEnabled(false);
        settings.MediaPlaybackRequiresUserGesture = true;

        // Interface size is applied by the UI's CSS fallback (IUiScale.IsSupported = false), so the
        // system font-size setting must not scale the page a second time.
        settings.TextZoom = 100;
    }
}
