using System.Diagnostics;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Theme;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Linux.Platform;
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

    private static readonly string LogPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Chuvadi", "startup-error.log");

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

            var appDataDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Chuvadi");
            var storage = new FileAppStorage(appDataDir);
            var services = BuildServices(storage);
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
            WireWindow(services);

            _ = manager.AddRootComponentAsync(typeof(ChuvadiReader.Ui.App), "#app", ParameterView.Empty);
            manager.Navigate("/");
            Native.Show(maximized: 1);
            Mark("shown, navigating");

            if (Timing)
            {
                services.GetRequiredService<IAppReadySignal>().Ready += () => Mark("blazor first render");
                GtkHost.FirstPaint += () => Mark("page loaded");
            }

            OpenFromCommandLine(services, args);

            Native.Run();
            manager.DisposeAsync().AsTask().GetAwaiter().GetResult();
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

    private static ServiceProvider BuildServices(FileAppStorage storage)
    {
        var services = new ServiceCollection();
        services.AddBlazorWebView();

        services.AddSingleton<IAppStorage>(storage);
        services.AddSingleton<SaveFolderService>();
        services.AddSingleton<CategoryService>();
        services.AddSingleton<ThemeService>();
        services.AddSingleton<UserProfileService>();
        services.AddSingleton<RecentFilesService>();
        services.AddSingleton<PinnedService>();
        services.AddSingleton<WatchedFolderService>();
        services.AddSingleton<LibraryService>();
        services.AddSingleton<TagService>();
        services.AddSingleton<FolderSearchService>();
        services.AddSingleton<DocumentPropertiesService>();
        services.AddSingleton<ExportService>();
        services.AddSingleton<RedactService>();
        services.AddSingleton<StampService>();
        services.AddSingleton<DocxViewService>();
        services.AddSingleton<XlsxViewService>();
        services.AddSingleton<FlattenService>();
        services.AddSingleton<RecoveryService>();
        services.AddSingleton<PressService>();
        services.AddSingleton<IPdfReader, ChuvadiPdfReader>();
        services.AddSingleton<TabsService>();
        services.AddSingleton<PdfToolsService>();
        services.AddSingleton<BenchComposer>();
        services.AddSingleton<BenchService>();
        services.AddSingleton<SessionService>();
        services.AddSingleton<OpenDocumentService>();
        services.AddSingleton<BenchDropService>();
        services.AddSingleton<RedactRequestService>();
        services.AddSingleton<ShellService>();
        services.AddSingleton<PreferencesService>();
        services.AddSingleton<TextViewService>();
        services.AddSingleton<MeasureService>();
        services.AddSingleton<SignatureCheckService>();
        services.AddSingleton<PasswordService>();
        services.AddSingleton<CertificateSignService>();
        services.AddSingleton<ChuvadiReader.Core.Licensing.IEntitlements, ChuvadiReader.Core.Licensing.DefaultEntitlements>();
        services.AddSingleton<IAppReadySignal, AppReadySignal>();

        // Linux implementations of the platform interfaces.
        services.AddSingleton<IUiScale, LinuxUiScale>();
        services.AddSingleton<IExternalLinks, LinuxExternalLinks>();
        services.AddSingleton<IWindowControls, LinuxWindowControls>();
        services.AddSingleton<IImageClipboard, LinuxImageClipboard>();
        services.AddSingleton<IFilePicker, GtkFilePicker>();
        services.AddSingleton<IPrintService, NoopPrintService>();

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

    private static readonly string[] OpenExtensions = { ".pdf", ".docx", ".doc", ".xlsx", ".xls" };

    private static bool IsSupportedFile(string path) =>
        OpenExtensions.Contains(Path.GetExtension(path).ToLowerInvariant());

    private static void WireWindow(IServiceProvider services)
    {
        var links = services.GetRequiredService<IExternalLinks>();
        GtkHost.ExternalLinkRequested += url => _ = links.OpenAsync(url);

        // Same rule as the Windows host: files dropped on the window open in the reader,
        // or join the shelf when the Bench is open.
        GtkHost.FilesDropped += paths =>
        {
            var supported = paths.Where(IsSupportedFile).ToArray();
            if (supported.Length == 0)
            {
                return;
            }

            var bench = services.GetRequiredService<BenchDropService>();
            if (bench.IsBenchActive)
            {
                bench.Drop(supported);
                return;
            }

            services.GetRequiredService<OpenDocumentService>().Request(supported[0]);
        };
    }

    /// <summary>"chuvadi-reader file.pdf" (and the desktop entry's %F) opens the first supported file.</summary>
    private static void OpenFromCommandLine(IServiceProvider services, string[] args)
    {
        var first = args.Select(a => a.StartsWith("file://", StringComparison.Ordinal) ? new Uri(a).LocalPath : a)
            .FirstOrDefault(a => File.Exists(a) && IsSupportedFile(a));
        if (first is null)
        {
            return;
        }

        var path = Path.GetFullPath(first);
        services.GetRequiredService<IAppReadySignal>().Ready +=
            () => services.GetRequiredService<OpenDocumentService>().Request(path);
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
