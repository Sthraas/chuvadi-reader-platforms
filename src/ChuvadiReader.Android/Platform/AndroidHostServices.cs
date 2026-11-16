using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using global::Android.Content.Res;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Facts about the Android host. The form factor follows Android's own tablet line: the window's
/// smallest width is at least 600 dp (sw600dp). It is re-read on every configuration change, so
/// split screen, freeform windows and foldables move the app between Tablet and Phone live.
/// </summary>
public sealed class AndroidPlatformInfo : IPlatformInfo
{
    public const int TabletSmallestWidthDp = 600;

    private FormFactor _formFactor;

    public AndroidPlatformInfo()
    {
        _formFactor = Classify(global::Android.App.Application.Context.Resources?.Configuration);
    }

    public PlatformKind Kind => PlatformKind.Android;

    public FormFactor FormFactor => _formFactor;

    public event Action? FormFactorChanged;

    public InputKinds Input => InputKinds.Touch | InputKinds.Pen | InputKinds.Keyboard;

    public ShellChrome Chrome { get; } = new(WindowButtons.None, NativeMenuBar: false, AccountMenu: false, TitleBarDrag: false, CornerRadiusPx: 0);

    public PlatformCapabilities Capabilities { get; } = new()
    {
        PickFolders = true,    // Storage Access Framework tree picker
        SaveInPlace = true,    // write-back to the content URI (IFileWriteBack)
        WatchFolders = false,
        RevealInFolder = false,
        DropFiles = false,     // documents arrive by Share / Open with instead
        Share = true,
        MultipleWindows = false,
        ServerSide = false,
    };

    public IKeyLabels Keys { get; } = new CtrlKeyLabels();

    /// <summary>Called by MainActivity on every configuration change (UI thread).</summary>
    public void OnConfigurationChanged(Configuration? configuration)
    {
        var next = Classify(configuration);
        if (next == _formFactor)
        {
            return;
        }

        _formFactor = next;
        FormFactorChanged?.Invoke();
    }

    private static FormFactor Classify(Configuration? configuration)
        => configuration is not null && configuration.SmallestScreenWidthDp >= TabletSmallestWidthDp
            ? FormFactor.Tablet
            : FormFactor.Phone;
}

/// <summary>
/// Android folders: settings in private files; working copies in the cache (the system may reclaim it).
/// AT-23: the default save folder — where Reduce file size, Export pages as images, Scatter, Lift and the
/// other "save into my folder" commands write without asking — is the device's shared **Documents**
/// folder (Core adds "Chuvadi Documents" under it), as on the desktop. Before, there was none, so Core
/// fell back to the app's cache, where the person couldn't see the files and Android may delete them.
/// Android lets an app create its own files in Documents with no permission (scoped storage, Android 11
/// and later; the app needs 15+), and the Files app and others see them. Limit: after the app is
/// reinstalled, files it made before belong to the old install, so a save to the same name gets a new one.
/// </summary>
public sealed class AndroidAppPaths : IAppPaths
{
    public AndroidAppPaths()
    {
        AppDataFolder = Path.Combine(FileSystem.AppDataDirectory, "Chuvadi");
        WorkingFolder = Path.Combine(FileSystem.CacheDirectory, "work");
        Directory.CreateDirectory(AppDataFolder);
        Directory.CreateDirectory(WorkingFolder);
        DefaultSaveFolder = SharedStorage.Root is { } root
            ? Path.Combine(root, global::Android.OS.Environment.DirectoryDocuments!)
            : null;
    }

    public string AppDataFolder { get; }

    public string WorkingFolder { get; }

    public string? DefaultSaveFolder { get; }
}

/// <summary>
/// App lifecycle for the Ui: Suspending when the app leaves the screen (flush drafts — Android may
/// kill a background app without warning), Resumed when it returns, and the system back gesture.
/// </summary>
public sealed class AndroidLifecycle : IAppLifecycle
{
    public event Func<Task>? Suspending;

    public event Action? Resumed;

    public event Func<bool>? BackRequested;

    /// <summary>Runs every Suspending handler; called from MainActivity.OnPause.</summary>
    public async Task RaiseSuspendingAsync()
    {
        if (Suspending is null)
        {
            return;
        }

        foreach (var handler in Suspending.GetInvocationList().Cast<Func<Task>>())
        {
            try
            {
                await handler().ConfigureAwait(true);
            }
            catch (Exception ex) when (ex is not OutOfMemoryException)
            {
                // One failing listener must not stop the others from saving.
                global::Android.Util.Log.Warn("Chuvadi", "Suspending handler failed: " + ex);
            }
        }
    }

    public void RaiseResumed() => Resumed?.Invoke();

    /// <summary>True when a Ui handler consumed the back gesture (closed a sheet, card or drawer).</summary>
    public bool RaiseBackRequested()
    {
        if (BackRequested is null)
        {
            return false;
        }

        foreach (var handler in BackRequested.GetInvocationList().Cast<Func<bool>>())
        {
            if (handler())
            {
                return true;
            }
        }

        return false;
    }
}

/// <summary>Opens http, https and mailto links in the user's browser or mail app.</summary>
public sealed class AndroidExternalLinks : IExternalLinks
{
    public bool IsAvailable => true;

    public async Task<bool> OpenAsync(string url)
    {
        if (!IExternalLinks.IsAllowed(url))
        {
            return false;
        }

        try
        {
            return await MainThread.InvokeOnMainThreadAsync(() => Launcher.Default.OpenAsync(new Uri(url))).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is FeatureNotSupportedException or InvalidOperationException)
        {
            return false;
        }
    }
}

/// <summary>
/// Who is using the app (decision A-10, option a). Android has no person's name to offer: the OS
/// user is the app's sandbox id (e.g. u0_a209), which Home would show as "Good morning, U0_a209".
/// So the display name is empty and Core's UserProfileService shows no name until the person sets
/// one in Settings › Profile. No sign-in on Android yet (Sangam comes later).
/// </summary>
public sealed class AndroidAccount : IAccount
{
    public bool IsSignedIn => false;

    public string DisplayName => string.Empty;

    public string? Email => null;

    public event Action? Changed
    {
        add { }
        remove { }
    }

    public Task<bool> SignInAsync(CancellationToken ct = default) => Task.FromResult(false);

    public Task SignOutAsync(CancellationToken ct = default) => Task.CompletedTask;
}

/// <summary>The device's shared storage as the Files app shows it (/storage/emulated/0 for the owner).</summary>
public static class SharedStorage
{
    public static string? Root { get; } =
        (global::Android.App.Application.Context.GetSystemService(global::Android.Content.Context.StorageService)
            as global::Android.OS.Storage.StorageManager)?.PrimaryStorageVolume.Directory?.AbsolutePath;
}
