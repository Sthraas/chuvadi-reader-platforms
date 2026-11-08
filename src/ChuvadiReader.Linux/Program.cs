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
            // Single instance (D-83: L-A, F-1; the kit's DesktopSingleInstance): the election (a lock file in
            // $XDG_RUNTIME_DIR) runs on its own thread while GTK starts; a launch that handed its files to the
            // running copy ends below, before building anything or showing a window.
            var claim = DesktopSingleInstance.ClaimAsync(args);
            if (!GtkHost.Init())
            {
                Console.Error.WriteLine("Chuvadi needs a graphical session (no display was found).");
                return 1;
            }

            Mark("gtk init");

            // B-15: whether WebKit's sandbox can start, checked in parallel with building the services
            // (~10 ms of bubblewrap); the answer is needed before the web view exists.
            var sandbox = Task.Run(() => (Ok: Native.SandboxCheck(out var detail), Detail: detail));

            var instance = claim.GetAwaiter().GetResult();
            if (instance.Role == InstanceRole.HandedOver)
            {
                Mark("handed over to the running copy");
                instance.Dispose();
                return 0;
            }

            Mark("instance " + instance.Role);

            var paths = new DesktopAppPaths(); // XDG config folder; Documents for saves (the kit's fallback)
            var storage = new FileAppStorage(paths.AppDataFolder); // B-16: the kit keeps settings in memory when home is unwritable
            var services = BuildServices(paths, storage, LinuxPlatformInfo.Create(), instance);
            Mark("services");

            var (sandboxOk, sandboxDetail) = sandbox.GetAwaiter().GetResult();
            if (!sandboxOk)
            {
                // WebKit would abort with no window. Say why, plainly, and end cleanly.
                const string title = "Chuvadi can't start on this computer";
                const string detail =
                    "Chuvadi shows documents inside a protected area (a sandbox) that needs \"user namespaces\", " +
                    "and they're switched off here.\n\n" +
                    "On Ubuntu 24.04 or later, reinstall the chuvadi-reader package (its security profile allows them). " +
                    "Otherwise, ask whoever manages this computer to allow unprivileged user namespaces.";
                Console.Error.WriteLine($"Chuvadi: {title}. The sandbox couldn't start: {sandboxDetail}");
                Native.ShowError(title, detail + "\n\nDetails: " + sandboxDetail);
                return 2;
            }

            Mark("sandbox check");

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
            var incoming = services.GetRequiredService<IncomingFiles>();
            WireWindow(services, incoming, instance);

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

            // "chuvadi-reader a.pdf b.docx …" and the desktop entry's %F (B-04): every file, each in its own tab,
            // in order (the kit's router holds them until the first render).
            incoming.Receive(args.Select(a => a.StartsWith("file://", StringComparison.Ordinal) ? new Uri(a).LocalPath : a));
            // A later launch's files arrive after the first paint (the socket starts then, off the critical path).
            services.GetRequiredService<IAppReadySignal>().Ready += () => instance.StartListening(GtkHost.RunOnMain);
            WarnWhenSettingsCantBeSaved(services, storage, manager);
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
            instance.Dispose(); // frees the lock file and socket for the next launch
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

    private static ServiceProvider BuildServices(IAppPaths paths, FileAppStorage storage, IPlatformInfo platform, IAppInstance instance)
    {
        var services = new ServiceCollection();
        services.AddBlazorWebView();

        // Every Core service and the seam defaults, once for all hosts (ChuvadiReader.Hosting).
        services.AddChuvadiReader(AppStateLifetime.Process);

        // Linux implementations of the platform seams (a later registration wins).
        services.AddSingleton<IAppPaths>(paths);
        services.AddSingleton<IAppStorage>(storage);
        services.AddSingleton<IPlatformInfo>(platform);
        services.AddSingleton(instance);
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
    private static void WireWindow(IServiceProvider services, IncomingFiles incoming, DesktopSingleInstance instance)
    {
        var links = services.GetRequiredService<IExternalLinks>();
        GtkHost.ExternalLinkRequested += url => _ = links.OpenAsync(url);

        // Files dropped on the window (B-06): the kit's router — all onto the shelf when the Bench is open,
        // else each in its own tab, in order.
        GtkHost.FilesDropped += paths => incoming.Receive(paths);

        // A file arrived from another launch (or from outside): bring the window forward, with the launcher's
        // activation token when it sent one (Wayland's xdg-activation; X11 startup id).
        incoming.Delivered += () => GtkHost.Post(() => Native.Present(instance.ActivationToken));
    }

    /// <summary>B-16: one notice when settings can't be written (read-only or full home folder); the app keeps
    /// working with them in memory.</summary>
    private static void WarnWhenSettingsCantBeSaved(IServiceProvider services, FileAppStorage storage, LinuxWebViewManager manager)
    {
        var shell = services.GetRequiredService<ShellService>();
        var warned = 0;
        void Warn(string reason)
        {
            if (Interlocked.Exchange(ref warned, 1) == 0)
            {
                _ = manager.Dispatcher.InvokeAsync(() => shell.Notify(
                    $"Chuvadi can't save its settings on this computer ({reason.TrimEnd('.', ' ')}). Changes last until you close it.",
                    isError: true));
            }
        }

        services.GetRequiredService<IAppReadySignal>().Ready += () =>
        {
            if (!storage.CanSave)
            {
                Warn(storage.CannotSaveReason ?? "the settings folder can't be written");
            }

            storage.CannotSave += Warn;
        };
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
