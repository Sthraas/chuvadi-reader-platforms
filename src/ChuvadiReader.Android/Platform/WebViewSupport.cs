namespace ChuvadiReader.Android.Platform;

/// <summary>
/// The Reader's pages are sized with CSS <c>zoom</c>, whose measurement Chromium standardised in
/// version 128; on an older Android System WebView the pages measure wrongly and zoom lands on a
/// blank area (round 5, API 35 emulator, WebView 124). D-105 (a): require 128 or later, and until
/// then show one plain screen asking the person to update it, instead of a broken Reader. Real
/// Android 15+ devices update the WebView through Google Play.
/// </summary>
public static class WebViewSupport
{
    /// <summary>Lowest Chromium major version the Ui works on.</summary>
    public const int MinimumMajor = 128;

    /// <summary>The installed WebView provider (package, version); null if there is none.</summary>
    public static (string Package, string Version)? Current()
    {
        var info = global::Android.Webkit.WebView.CurrentWebViewPackage;
        return info?.PackageName is { } name ? (name, info.VersionName ?? string.Empty) : null;
    }

    /// <summary>True when the Reader can run: a WebView is installed and is version 128 or later.</summary>
    public static bool IsSupported(out string version)
    {
        var current = Current();
        version = current?.Version ?? string.Empty;
        var dot = version.IndexOf('.');
        return current is not null
            && int.TryParse(dot > 0 ? version[..dot] : version, out var major)
            && major >= MinimumMajor;
    }

    /// <summary>The update screen, in the handout's voice; its button opens the WebView's Play page.</summary>
    public static ContentPage UpdatePage(string version)
    {
        var ink = Color.FromArgb("#241B14");
        var soft = Color.FromArgb("#6B5A4A");
        var accent = Color.FromArgb("#9C3B20");

        var have = string.IsNullOrEmpty(version) ? "isn't installed" : $"is version {version}";
        var button = new Button
        {
            Text = "Update Android System WebView",
            BackgroundColor = accent,
            TextColor = Colors.White,
            CornerRadius = 10,
            Padding = new Thickness(18, 12),
            HorizontalOptions = LayoutOptions.Start,
        };
        button.Clicked += (_, _) => OpenPlayPage();

        return new ContentPage
        {
            BackgroundColor = Color.FromArgb("#F2EAD6"),
            Content = new ScrollView
            {
                Content = new VerticalStackLayout
                {
                    Padding = new Thickness(28, 56, 28, 28),
                    Spacing = 16,
                    MaximumWidthRequest = 560,
                    Children =
                    {
                        new Label { Text = "One small update first", FontSize = 26, TextColor = ink },
                        new Label
                        {
                            Text = "Chuvadi shows your documents through Android System WebView, and it needs "
                                 + $"version {MinimumMajor} or newer. On this device it {have}.",
                            FontSize = 16,
                            TextColor = ink,
                        },
                        new Label
                        {
                            Text = "The update is free from Google Play. Your files stay where they are; "
                                 + "nothing leaves this device.",
                            FontSize = 16,
                            TextColor = ink,
                        },
                        button,
                        new Label
                        {
                            Text = "When it's done, come back to Chuvadi and pick up where you left off.",
                            FontSize = 14,
                            TextColor = soft,
                        },
                    },
                },
            },
        };
    }

    private static void OpenPlayPage()
    {
        var package = Current()?.Package ?? "com.google.android.webview";
        var context = global::Android.App.Application.Context;
        foreach (var uri in new[] { $"market://details?id={package}", $"https://play.google.com/store/apps/details?id={package}" })
        {
            try
            {
                var intent = new global::Android.Content.Intent(global::Android.Content.Intent.ActionView, global::Android.Net.Uri.Parse(uri));
                intent.AddFlags(global::Android.Content.ActivityFlags.NewTask);
                context.StartActivity(intent);
                return;
            }
            catch (global::Android.Content.ActivityNotFoundException)
            {
                // No Play Store: try the web page next.
            }
        }
    }
}
