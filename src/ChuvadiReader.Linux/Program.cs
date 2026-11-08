using System.Diagnostics;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Hosting.Desktop;
using ChuvadiReader.Linux.Platform;
using ChuvadiReader.Platform;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;

namespace ChuvadiReader.Linux;

/// <summary>
/// Entry point. Mirrors ChuvadiReader.Windows/App.xaml.cs: the same services, with the Linux
/// implementations of the platform interfaces. Set CHUVADI_TIMING=1 to print each startup stage.
/// </summary>
public static class Program
{
    public const string AppId = "in.chuvadi.Reader";

    private static readonly Stopwatch Clock = Stopwatch.StartNew();
    private static readonly bool Timing = Environment.GetEnvironmentVariable("CHUVADI_TIMING") == "1";

    private static readonly string LogPath = Path.Combine(new DesktopAppPaths().AppDataFolder, "startup-error.log");

    [STAThread]
    public static int Main(string[] args)
    {
        Mark("managed main");
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
        {
            if (e.ExceptionObject is Exception ex)
            {
                Report(ex);
            }
        };

        try
        {
            if (!GtkHost.Init())
            {
                Console.Error.WriteLine("Chuvadi needs a graphical session (no display was found).");
                return 1;
            }

            Mark("gtk init");

            var paths = new LinuxAppPaths(); // XDG config folder; Documents for saves
            var storage = new FileAppStorage(paths.AppDataFolder);
            var services = BuildServices(paths, storage, LinuxPlatformInfo.Create());
            Mark("services");

            var theme = (storage.GetSync("theme") ?? string.Empty).Trim().ToLowerInvariant();
            if (Native.CreateWindow("Chuvadi", AppId, 1100, 720, PrePaintColour(theme), DevTools ? 1 : 0) == 0)
            {
                Console.Error.WriteLine("Chuvadi couldn't create its window.");
                return 1;
            }

            Mark("window + web view");

            var wwwroot = Path.Combine(AppContext.BaseDirectory, "wwwroot");
            // A published app has its assets in wwwroot; a development build serves them from the
            // static-web-assets manifest beside the app, which WebViewManager reads itself.
            IFileProvider files = Directory.Exists(wwwroot) ? new PhysicalFileProvider(wwwroot) : new NullFileProvider();
            var manager = new LinuxWebViewManager(services, files);
            GtkHost.Attach(manager);
            var opener = new DocumentOpener(services.GetRequiredService<OpenDocumentService>(), manager.Dispatcher);
            WireWindow(services, opener);

            _ = manager.AddRootComponentAsync(typeof(ChuvadiReader.Ui.App), "#app", ParameterView.Empty);
            Mark("root component added");
            manager.Navigate("/");
            Mark("navigation started");
            Native.Show(maximized: 1);
            Mark("shown");

            if (Timing)
            {
                services.GetRequiredService<IAppReadySignal>().Ready += () => Mark("blazor first render");
                GtkHost.FirstPaint += () => Mark("page loaded");
            }

            OpenFromCommandLine(services, opener, args);
#if CHUVADI_UITEST
            UiTestDriver.Start(services, manager);
#endif

            Native.Run();
            Mark("main loop ended");

            // The window is gone, so the page can no longer answer. Components that dispose through
            // JS interop would wait for it forever and keep the process alive with no window. Give
            // disposal a moment, then end, as the Windows app ends when its window closes.
            var disposed = manager.DisposeAsync().AsTask().Wait(TimeSpan.FromSeconds(1));
            Mark(disposed ? "disposed" : "disposal still waiting on the page; exiting");
            return 0;
        }
        catch (Exception ex)
        {
            Report(ex);
            return 1;
        }
    }

#if DEBUG
    private const bool DevTools = true;
#else
    private const bool DevTools = false;
#endif

    private static ServiceProvider BuildServices(IAppPaths paths, FileAppStorage storage, IPlatformInfo platform)
    {
        var services = new ServiceCollection();
        services.AddBlazorWebView();

        // Every Core service and the seam defaults, once for all hosts (ChuvadiReader.Hosting).
        services.AddChuvadiReader(AppStateLifetime.Process);

        // Linux implementations of the platform seams (a later registration wins).
        services.AddSingleton<IAppPaths>(paths);
        services.AddSingleton<IAppStorage>(storage);
        services.AddSingleton<IPlatformInfo>(platform);
        services.AddSingleton<IUiScale, LinuxUiScale>();
        services.AddSingleton<IExternalLinks, LinuxExternalLinks>();
        services.AddSingleton<IWindowControls, LinuxWindowControls>();
        services.AddSingleton<IImageClipboard, LinuxImageClipboard>();
        services.AddSingleton<IClipboard, LinuxClipboard>();
        services.AddSingleton<IFileManager, LinuxFileManager>();
        services.AddSingleton<IFilePicker, GtkFilePicker>();
        services.AddSingleton<IPrintService, CupsPrintService>();

        return services.BuildServiceProvider();
    }

    /// <summary>The theme's surface-mid colour (tokens.css), painted before the page, as on Windows.</summary>
    private static string PrePaintColour(string theme) => theme switch
    {
        "dark" => "#1B1410",
        "palm" => "#EBE5C9",
        "indigo" => "#EDF0F6",
        "contrast" => "#F5F5F2",
        _ => "#F2EAD6",
    };

    // Same list as the Open dialog (Core: DocumentFormatExtensions.OpenableExtensions), as on Windows.
    private static void WireWindow(IServiceProvider services, DocumentOpener opener)
    {
        var links = services.GetRequiredService<IExternalLinks>();
        GtkHost.ExternalLinkRequested += url => _ = links.OpenAsync(url);

        // Files dropped on the window: each in its own tab (B-06), or all onto the shelf when the Bench is
        // open (the Windows host's rule for the Bench).
        GtkHost.FilesDropped += paths =>
        {
            var supported = DocumentOpener.Openable(paths);
            if (supported.Count == 0)
            {
                return;
            }

            var bench = services.GetRequiredService<BenchDropService>();
            if (bench.IsBenchActive)
            {
                bench.Drop([.. supported]);
                return;
            }

            _ = opener.OpenAsync(supported);
        };
    }

    /// <summary>"chuvadi-reader a.pdf b.docx …" (and the desktop entry's %F): every openable file, each in
    /// its own tab, in the order given (B-04).</summary>
    private static void OpenFromCommandLine(IServiceProvider services, DocumentOpener opener, string[] args)
    {
        var files = DocumentOpener.Openable(args);
        if (files.Count == 0)
        {
            return;
        }

        services.GetRequiredService<IAppReadySignal>().Ready += () => _ = opener.OpenAsync(files);
    }

    internal static void Mark(string stage)
    {
        if (Timing)
        {
            var sinceStart = (DateTime.Now - Process.GetCurrentProcess().StartTime).TotalMilliseconds;
            Console.Error.WriteLine($"[timing] {sinceStart,7:F1} ms since process start  {Clock.Elapsed.TotalMilliseconds,7:F1} ms in managed  {stage}");
        }
    }

    internal static void Report(Exception ex)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath)!);
            File.WriteAllText(LogPath, DateTimeOffset.Now + Environment.NewLine + ex);
        }
        catch
        {
            // logging must never throw
        }

        Console.Error.WriteLine("Chuvadi error: " + ex);
    }
}
