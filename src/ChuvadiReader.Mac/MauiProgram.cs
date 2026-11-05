using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Theme;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Mac.Platform;

namespace ChuvadiReader.Mac;

/// <summary>Builds the MAUI app and registers the same Core services as the Windows host,
/// with the Mac implementations of the platform interfaces.</summary>
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

        // ~/Library/Application Support/Chuvadi — the macOS home for app state. Asked of the OS
        // directly: .NET's SpecialFolder.ApplicationData maps to ~/.config on macOS.
        var storage = new FileAppStorage(MacPaths.AppSupportDirectory);
        services.AddSingleton<IAppStorage>(storage);
        services.AddSingleton(storage);

        // Core services — identical list and order to the Windows host (App.xaml.cs).
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

        // Mac platform layer.
        services.AddSingleton<MacUiScale>();
        services.AddSingleton<IUiScale>(sp => sp.GetRequiredService<MacUiScale>());
        services.AddSingleton<IExternalLinks, MacExternalLinks>();
        services.AddSingleton<IFilePicker, MacFilePicker>();
        services.AddSingleton<IImageClipboard, MacImageClipboard>();
        services.AddSingleton<MacWindowControls>();
        services.AddSingleton<IWindowControls>(sp => sp.GetRequiredService<MacWindowControls>());

        // Printing: the Mac print path is an open decision for Arun (native macOS print panel fed
        // by Chuvadi.Pdf's rasteriser, as on Windows, vs Chuvadi.Print.Ipp over CUPS). Until he
        // decides, the Print card shows "unavailable" rather than a half-built path.
        services.AddSingleton<IPrintService, NoopPrintService>();

        var app = builder.Build();
        StartupTimeline.Mark("maui-built");
        return app;
    }
}
