using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting.Desktop;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Mac.Platform;
using ChuvadiReader.Platform;
using Microsoft.Maui.LifecycleEvents;

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
        services.AddSingleton<IShare, MacShare>();
        services.AddSingleton<IHostNotices, MacHostNotices>();
        services.AddSingleton<IPrintService, MacPrintService>();

        services.AddSingleton<MacWindowControls>();
        services.AddSingleton<IWindowControls>(sp => sp.GetRequiredService<MacWindowControls>());
        services.AddSingleton<MacUiScale>();
        services.AddSingleton<IUiScale>(sp => sp.GetRequiredService<MacUiScale>());

        // Files opened with Chuvadi from Finder: at launch (scene connect) and while running.
        builder.ConfigureLifecycleEvents(events => events.AddiOS(ios => ios
            .SceneWillConnect((_, _, options) => Incoming(options.UrlContexts))
            .SceneOpenUrl((_, contexts) =>
            {
                Incoming(contexts);
                return true;
            })));

        var app = builder.Build();
        _services = app.Services;
        StartupTimeline.Mark("maui-built");
        return app;
    }

    private static IServiceProvider? _services;

    private static void Incoming(Foundation.NSSet<UIKit.UIOpenUrlContext>? contexts)
    {
        if (contexts is null || contexts.Count == 0 || _services is null)
        {
            return;
        }

        MacFileArrivals.Route(_services, contexts.ToArray().Select(c => c.Url));
    }
}
