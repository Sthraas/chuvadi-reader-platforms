using ChuvadiReader.Core.Theme;
using global::Android.App;
using global::Android.Views;
using AndroidX.Core.View;
using AColor = global::Android.Graphics.Color;
using AView = global::Android.Views.View;

namespace ChuvadiReader.Android;

/// <summary>
/// Keeps the app clear of the status bar, the gesture / navigation bar, display cut-outs and the
/// on-screen keyboard. Android 15 always draws apps edge-to-edge, and the WebView doesn't apply CSS
/// safe-area insets, so the host pads its root view natively. The padded margins (the status-bar
/// and navigation-bar areas) take the colour of the Ui's bars that meet them — the phone's top bar
/// and bottom navigation, the tablet's title and status bars, all <c>--chvd-surface-hi</c> — so the
/// app reads edge to edge; icons are dark on the light themes and light on Night paper.
/// AT-08: this follows <see cref="ThemeService"/> while the app runs, not only at start.
/// </summary>
internal static class SystemBars
{
    private static WeakReference<Activity>? _activity;
    private static ThemeService? _themes;

    public static void Apply(Activity activity)
    {
        var window = activity.Window;
        var root = window?.DecorView.FindViewById(global::Android.Resource.Id.Content);
        if (window is null || root is null)
        {
            return;
        }

        _activity = new WeakReference<Activity>(activity);
        var themes = IPlatformApplication.Current?.Services.GetService<ThemeService>();
        if (themes is not null && !ReferenceEquals(themes, _themes))
        {
            // Process lifetime (MauiProgram): one ThemeService for the app, so subscribe once.
            _themes = themes;
            themes.Changed += OnThemeChanged;
        }

        Paint(activity, StoredTheme());
        ViewCompat.SetOnApplyWindowInsetsListener(root, new InsetsListener());
        ViewCompat.RequestApplyInsets(root);
    }

    /// <summary>The bar colour for a theme (tokens.css <c>--chvd-surface-hi</c>).</summary>
    public static AColor BarColour(ChuvadiTheme theme) => theme switch
    {
        ChuvadiTheme.Dark => AColor.Rgb(0x24, 0x1B, 0x15),
        ChuvadiTheme.Palm => AColor.Rgb(0xF6, 0xF2, 0xE1),
        ChuvadiTheme.Indigo => AColor.Rgb(0xF8, 0xF9, 0xFC),
        ChuvadiTheme.Contrast => AColor.Rgb(0xFF, 0xFF, 0xFF),
        _ => AColor.Rgb(0xFB, 0xF7, 0xEC),
    };

    // Before ThemeService has hydrated (first paint), the saved key decides; afterwards the service.
    private static ChuvadiTheme StoredTheme()
    {
        if (_themes is { Current: not ChuvadiTheme.Light } themes)
        {
            return themes.Current;
        }

        var saved = IPlatformApplication.Current?.Services.GetService<ChuvadiReader.Android.Platform.AndroidAppStorage>()?.GetSync("theme");
        return Enum.TryParse<ChuvadiTheme>(saved?.Trim(), ignoreCase: true, out var theme) ? theme : ChuvadiTheme.Light;
    }

    private static void OnThemeChanged()
    {
        if (_activity?.TryGetTarget(out var activity) == true && _themes is { } themes)
        {
            var theme = themes.Current;
            activity.RunOnUiThread(() => Paint(activity, theme));
        }
    }

    private static void Paint(Activity activity, ChuvadiTheme theme)
    {
        var window = activity.Window;
        var root = window?.DecorView.FindViewById(global::Android.Resource.Id.Content);
        if (window is null || root is null)
        {
            return;
        }

        root.SetBackgroundColor(BarColour(theme));
        if (WindowCompat.GetInsetsController(window, window.DecorView) is { } controller)
        {
            var light = !theme.IsDark();
            controller.AppearanceLightStatusBars = light;
            controller.AppearanceLightNavigationBars = light;
        }
    }

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
