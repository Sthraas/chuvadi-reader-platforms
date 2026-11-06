using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Mac.Platform;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Mac;

/// <summary>Builds the MAUI app: every Core service through the shared kit (AddChuvadiReader), then the
/// Mac implementations of the platform seams (docs/foundation/HANDOFF.md §2). A later registration wins.</summary>
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        StartupTimeline.Mark("maui-builder");

        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>();

        var services = builder.Services;
        services.AddMauiBlazorWebView();
#if DEBUG
        services.AddBlazorWebViewDeveloperTools();
#endif

        // Every Core service, registered once for all hosts.
        services.AddChuvadiReader(AppStateLifetime.Process);

        // Folders: asked of macOS itself (the kit's desktop default can't tell Mac Catalyst is macOS).
        var paths = new MacAppPaths();
        services.AddSingleton<IAppPaths>(paths);

        var storage = new FileAppStorage(paths.AppDataFolder);
        services.AddSingleton<IAppStorage>(storage);
        services.AddSingleton(storage);

        services.AddSingleton<IPlatformInfo>(new FixedPlatformInfo(
            PlatformKind.MacOS,
            InputKinds.Mouse | InputKinds.Keyboard,
            // Traffic lights drawn by the Ui on the left; the app menu lives in the macOS menu bar.
            new ShellChrome(ChuvadiReader.Platform.WindowButtons.Left, NativeMenuBar: true, AccountMenu: false, TitleBarDrag: true, CornerRadiusPx: 0),
            FixedPlatformInfo.DesktopCapabilities,
            new MacKeyLabels()));

        var clipboard = new MacClipboard();
        services.AddSingleton<IClipboard>(clipboard);
        services.AddSingleton<IImageClipboard>(clipboard);
        services.AddSingleton<IFilePicker, MacFilePicker>();
        services.AddSingleton<IExternalLinks, MacExternalLinks>();
        services.AddSingleton<IFileManager, MacFileManager>();
        services.AddSingleton<IPrintService, MacPrintService>();

        services.AddSingleton<MacWindowControls>();
        services.AddSingleton<IWindowControls>(sp => sp.GetRequiredService<MacWindowControls>());
        services.AddSingleton<MacUiScale>();
        services.AddSingleton<IUiScale>(sp => sp.GetRequiredService<MacUiScale>());

        var app = builder.Build();
        StartupTimeline.Mark("maui-built");
        return app;
    }
}
