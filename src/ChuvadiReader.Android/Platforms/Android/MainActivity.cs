using ChuvadiReader.Android.Platform;
using global::Android.App;
using global::Android.Content;
using global::Android.Content.PM;
using global::Android.Content.Res;
using global::Android.OS;
using AndroidX.Activity;

namespace ChuvadiReader.Android;

/// <summary>
/// The single activity. SingleTask, so "Open with" / "Share" from another app reuses the running
/// Reader (a new tab) instead of starting a second copy. It declares every configuration change, so
/// rotation, split screen, resizing and keyboard changes never recreate it: the Blazor UI keeps its
/// state, relays out, and the form factor (phone / tablet) is re-evaluated.
/// </summary>
[Activity(
    Theme = "@style/Maui.SplashTheme",
    MainLauncher = true,
    Exported = true,
    LaunchMode = LaunchMode.SingleTask,
    ResizeableActivity = true,
    ConfigurationChanges = ConfigChanges.ScreenSize | ConfigChanges.Orientation | ConfigChanges.UiMode
                         | ConfigChanges.ScreenLayout | ConfigChanges.SmallestScreenSize | ConfigChanges.Density
                         | ConfigChanges.Keyboard | ConfigChanges.KeyboardHidden | ConfigChanges.Navigation)]
// Open with… (file managers, mail, browsers' downloads).
[IntentFilter(
    new[] { Intent.ActionView },
    Categories = new[] { Intent.CategoryDefault, Intent.CategoryBrowsable },
    DataSchemes = new[] { "content" },
    DataMimeTypes = new[] { DocumentTypes.Pdf, DocumentTypes.Docx, DocumentTypes.Xlsx })]
// Share to Chuvadi.
[IntentFilter(
    new[] { Intent.ActionSend },
    Categories = new[] { Intent.CategoryDefault },
    DataMimeTypes = new[] { DocumentTypes.Pdf, DocumentTypes.Docx, DocumentTypes.Xlsx })]
public sealed class MainActivity : MauiAppCompatActivity
{
    private BackCallback? _back;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        SystemBars.Apply(this);

        // Back gesture: the Ui gets the first chance (close a sheet, card or drawer); otherwise the
        // next handler: BlazorWebView's (back through the WebView's history), then Android's
        // default (leave the app). The dispatcher asks the most recently added callback first, and
        // BlazorWebView adds its own when its handler connects, after this; so ours is re-added
        // then (MainPage) and on every resume (PutBackFirst). Round 4 found Back going to the
        // WebView history while a card stayed open.
        _back = new BackCallback(this);
        OnBackPressedDispatcher.AddCallback(this, _back);

        Deliver(Intent);
    }

    protected override void OnNewIntent(Intent? intent)
    {
        base.OnNewIntent(intent);
        Deliver(intent);
    }

    protected override void OnActivityResult(int requestCode, Result resultCode, Intent? data)
    {
        if (!ActivityResults.Complete(requestCode, resultCode, data))
        {
            base.OnActivityResult(requestCode, resultCode, data);
        }
    }

    public override void OnConfigurationChanged(Configuration newConfig)
    {
        base.OnConfigurationChanged(newConfig);
        Service<AndroidPlatformInfo>()?.OnConfigurationChanged(newConfig);
    }

    protected override void OnPause()
    {
        // Android may end a background app without warning: let the Ui save drafts and the session now.
        _ = Service<AndroidLifecycle>()?.RaiseSuspendingAsync();
        base.OnPause();
    }

    protected override void OnResume()
    {
        base.OnResume();
        PutBackFirst();
        Service<AndroidLifecycle>()?.RaiseResumed();
    }

    /// <summary>Makes our Back callback the first one asked again (see OnCreate).</summary>
    internal void PutBackFirst()
    {
        if (_back is null)
        {
            return;
        }

        _back.Remove();
        OnBackPressedDispatcher.AddCallback(this, _back);
    }

    private static T? Service<T>()
        where T : class
        => IPlatformApplication.Current?.Services.GetService<T>();

    private static void Deliver(Intent? intent)
    {
        if (intent is not null)
        {
            Service<DocumentImport>()?.HandleIntent(intent);
        }
    }

    private sealed class BackCallback(MainActivity activity) : OnBackPressedCallback(true)
    {
        public override void HandleOnBackPressed()
        {
            if (Service<AndroidLifecycle>()?.RaiseBackRequested() == true)
            {
                return;
            }

            // Nobody consumed it: hand the gesture to the next handler (MAUI / system default).
            Enabled = false;
            activity.OnBackPressedDispatcher.OnBackPressed();
            Enabled = true;
        }
    }
}
