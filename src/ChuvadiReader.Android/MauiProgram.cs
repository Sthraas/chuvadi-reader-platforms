using ChuvadiReader.Android.Platform;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Android;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>();

        builder.Services.AddMauiBlazorWebView();
#if DEBUG
        builder.Services.AddBlazorWebViewDeveloperTools();
#endif

        // Every Core service plus safe defaults (Foundation's shared host kit). One person per process.
        // Defaults kept on Android: IUiScale (the Ui's CSS zoom) and IWindowControls (none: Android
        // owns the window; the Ui hides its buttons from IPlatformInfo.Chrome.Buttons = None).
        builder.Services.AddChuvadiReader(AppStateLifetime.Process);

        // ── Android implementations (a later registration wins) ──
        var paths = new AndroidAppPaths();
        var storage = new AndroidAppStorage(paths.AppDataFolder);
        builder.Services.AddSingleton<IAppPaths>(paths);
        builder.Services.AddSingleton<IAppStorage>(storage);
        builder.Services.AddSingleton(storage);

        builder.Services.AddSingleton<IAccount, AndroidAccount>();
        builder.Services.AddSingleton<AndroidPlatformInfo>();
        builder.Services.AddSingleton<IPlatformInfo>(sp => sp.GetRequiredService<AndroidPlatformInfo>());
        builder.Services.AddSingleton<AndroidLifecycle>();
        builder.Services.AddSingleton<IAppLifecycle>(sp => sp.GetRequiredService<AndroidLifecycle>());

        builder.Services.AddSingleton<DocumentLinks>();
        builder.Services.AddSingleton<IFileWriteBack, AndroidFileWriteBack>();
        builder.Services.AddSingleton<IPathLabels, AndroidPathLabels>();
        builder.Services.AddSingleton<DocumentImport>();
        builder.Services.AddSingleton<IFilePicker, AndroidFilePicker>();

        builder.Services.AddSingleton<AndroidClipboard>();
        builder.Services.AddSingleton<IClipboard>(sp => sp.GetRequiredService<AndroidClipboard>());
        builder.Services.AddSingleton<IImageClipboard>(sp => sp.GetRequiredService<AndroidClipboard>());
        builder.Services.AddSingleton<IShare, AndroidShare>();
        builder.Services.AddSingleton<IExternalLinks, AndroidExternalLinks>();
        builder.Services.AddSingleton<IPrintService, AndroidPrintService>();
        builder.Services.AddSingleton<ChuvadiReader.Platform.IHostNotices, AndroidHostNotices>();

        return builder.Build();
    }
}
