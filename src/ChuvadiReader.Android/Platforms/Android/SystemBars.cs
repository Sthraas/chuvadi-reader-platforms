using ChuvadiReader.Android.Platform;
using global::Android.App;
using global::Android.Views;
using AndroidX.Core.View;
using AColor = global::Android.Graphics.Color;
using AView = global::Android.Views.View;

namespace ChuvadiReader.Android;

/// <summary>
/// Keeps the app clear of the status bar, the gesture / navigation bar, display cut-outs and the
/// on-screen keyboard. Android 15 always draws apps edge-to-edge, and the WebView doesn't apply CSS
/// safe-area insets, so the host pads its root view natively. The padded margin takes the saved
/// theme's page colour — the same mapping the Windows host uses before the first paint — and the
/// status-bar icons are dark on light themes, light on Night paper.
/// </summary>
internal static class SystemBars
{
    public static void Apply(Activity activity)
    {
        var window = activity.Window;
        var root = window?.DecorView.FindViewById(global::Android.Resource.Id.Content);
        if (window is null || root is null)
        {
            return;
        }

        var theme = (IPlatformApplication.Current?.Services.GetService<AndroidAppStorage>()?.GetSync("theme") ?? string.Empty)
            .Trim().ToLowerInvariant();
        root.SetBackgroundColor(PageColour(theme));

        if (WindowCompat.GetInsetsController(window, window.DecorView) is { } controller)
        {
            var light = theme != "dark";
            controller.AppearanceLightStatusBars = light;
            controller.AppearanceLightNavigationBars = light;
        }

        ViewCompat.SetOnApplyWindowInsetsListener(root, new InsetsListener());
        ViewCompat.RequestApplyInsets(root);
    }

    /// <summary>First-paint colours per theme (tokens.css surface colours, as in the Windows host).</summary>
    private static AColor PageColour(string theme) => theme switch
    {
        "dark" => AColor.Rgb(0x1B, 0x14, 0x10),
        "palm" => AColor.Rgb(0xEB, 0xE5, 0xC9),
        "indigo" => AColor.Rgb(0xED, 0xF0, 0xF6),
        "contrast" => AColor.Rgb(0xF5, 0xF5, 0xF2),
        _ => AColor.Rgb(0xF2, 0xEA, 0xD6),
    };

    private sealed class InsetsListener : Java.Lang.Object, IOnApplyWindowInsetsListener
    {
        public WindowInsetsCompat? OnApplyWindowInsets(AView? v, WindowInsetsCompat? insets)
        {
            if (v is null || insets is null)
            {
                return insets;
            }

            var bars = insets.GetInsets(WindowInsetsCompat.Type.SystemBars() | WindowInsetsCompat.Type.DisplayCutout());
            var ime = insets.GetInsets(WindowInsetsCompat.Type.Ime());
            if (bars is not null)
            {
                v.SetPadding(bars.Left, bars.Top, bars.Right, Math.Max(bars.Bottom, ime?.Bottom ?? 0));
            }

            return WindowInsetsCompat.Consumed;
        }
    }
}
