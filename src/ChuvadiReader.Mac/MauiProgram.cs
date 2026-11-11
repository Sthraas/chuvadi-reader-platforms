using Microsoft.Extensions.Logging;
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

        // D-132: warnings and errors to ~/Library/Logs/Chuvadi, scrubbed, about 1 MB, never sent anywhere.
        var errorLog = new MacErrorLog(paths.AppDataFolder);
        errorLog.WatchUnhandled();
        builder.Logging.AddProvider(errorLog);
        if (MacSmoke.Enabled)
        {
            builder.Logging.AddProvider(new SmokeLoggerProvider()); // CI smoke only: Ui exceptions to stdout
        }

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

        // Files opened with Chuvadi from Finder, the Dock or `open` (Mac Test M-02): macOS uses the scene
        // events (SceneDelegate, Info.plist scene manifest) — at launch in the connection options, while
        // running as open-URL contexts. The app-level open-URL and launch options are routed too, in case
        // a macOS version hands a file over that way. All go to the kit's IncomingFiles.
        builder.ConfigureLifecycleEvents(events => events.AddiOS(ios => ios
            .SceneWillConnect((_, _, options) => Incoming(options.UrlContexts?.ToArray().Select(c => c.Url)))
            .SceneOpenUrl((_, contexts) =>
            {
                Incoming(contexts?.ToArray().Select(c => c.Url));
                return true;
            })
            .OpenUrl((_, url, _) =>
            {
                Incoming(new[] { url });
                return true;
            })
            .FinishedLaunching((_, options) =>
            {
                if (options?[UIKit.UIApplication.LaunchOptionsUrlKey] is Foundation.NSUrl url)
                {
                    Incoming(new[] { url });
                }

                return true;
            })));

        var app = builder.Build();
        _services = app.Services;
        StartupTimeline.Mark("maui-built");
        return app;
    }

    private static IServiceProvider? _services;

    private static void Incoming(IEnumerable<Foundation.NSUrl>? urls)
    {
        var list = urls?.Where(u => u is not null).ToArray() ?? Array.Empty<Foundation.NSUrl>();
        if (list.Length == 0 || _services is null)
        {
            return;
        }

        if (list.Length > 1)
        {
            // M-24: macOS hands a batch over as an unordered set; open it in Finder's Name order.
            var order = FileBatchOrder.Sort(list.Select(u => u.Path ?? string.Empty)).ToList();
            list = list.OrderBy(u => order.IndexOf(u.Path ?? string.Empty)).ToArray();
        }

        MacSmoke.Log("files-arrived " + string.Join(" ", list.Select(u => Path.GetFileName(u.Path ?? string.Empty))));
        MacFileArrivals.Route(_services, list);
    }
}
