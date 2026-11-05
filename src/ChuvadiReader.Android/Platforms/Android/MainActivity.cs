using ChuvadiReader.Android.Platform;
using global::Android.App;
using global::Android.Content;
using global::Android.Content.PM;
using global::Android.OS;

namespace ChuvadiReader.Android;

/// <summary>
/// The single activity. It is SingleTask so "Open with" / "Share" from another app reuses the
/// running Reader (a new tab) instead of starting a second copy, and it declares every
/// configuration change so rotation, split screen, resizing and keyboard changes never
/// recreate it — the Blazor UI keeps its state and simply relays out through its own
/// phone / tablet CSS.
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
    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        Deliver(Intent);
    }

    protected override void OnNewIntent(Intent? intent)
    {
        base.OnNewIntent(intent);
        Deliver(intent);
    }

    private static void Deliver(Intent? intent)
    {
        if (intent is null)
        {
            return;
        }

        var import = IPlatformApplication.Current?.Services.GetService<DocumentImport>();
        import?.HandleIntent(intent);
    }
}
