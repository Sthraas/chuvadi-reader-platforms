using ChuvadiReader.Android.Platform;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Theme;
using ChuvadiReader.Core.Window;
using IFilePicker = ChuvadiReader.Core.Reader.IFilePicker;

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

        // App state lives in the app's private files folder (Android's equivalent of %AppData%).
        var appDataDir = Path.Combine(FileSystem.AppDataDirectory, "Chuvadi");
        var storage = new AndroidAppStorage(appDataDir);
        builder.Services.AddSingleton<IAppStorage>(storage);
        builder.Services.AddSingleton(storage);

        // ── Core services: the same set, in the same order, as the Windows host ──
        builder.Services.AddSingleton<SaveFolderService>();
        builder.Services.AddSingleton<CategoryService>();
        builder.Services.AddSingleton<ThemeService>();
        builder.Services.AddSingleton<UserProfileService>();
        builder.Services.AddSingleton<RecentFilesService>();
        builder.Services.AddSingleton<PinnedService>();
        builder.Services.AddSingleton<WatchedFolderService>();
        builder.Services.AddSingleton<LibraryService>();
        builder.Services.AddSingleton<TagService>();
        builder.Services.AddSingleton<FolderSearchService>();
        builder.Services.AddSingleton<DocumentPropertiesService>();
        builder.Services.AddSingleton<ExportService>();
        builder.Services.AddSingleton<RedactService>();
        builder.Services.AddSingleton<StampService>();
        builder.Services.AddSingleton<DocxViewService>();
        builder.Services.AddSingleton<XlsxViewService>();
        builder.Services.AddSingleton<FlattenService>();
        builder.Services.AddSingleton<RecoveryService>();
        builder.Services.AddSingleton<PressService>();
        builder.Services.AddSingleton<IPdfReader, ChuvadiPdfReader>();
        builder.Services.AddSingleton<TabsService>();
        builder.Services.AddSingleton<PdfToolsService>();
        builder.Services.AddSingleton<BenchComposer>();
        builder.Services.AddSingleton<BenchService>();
        builder.Services.AddSingleton<SessionService>();
        builder.Services.AddSingleton<OpenDocumentService>();
        builder.Services.AddSingleton<BenchDropService>();
        builder.Services.AddSingleton<RedactRequestService>();
        builder.Services.AddSingleton<ShellService>();
        builder.Services.AddSingleton<PreferencesService>();
        builder.Services.AddSingleton<TextViewService>();
        builder.Services.AddSingleton<MeasureService>();
        builder.Services.AddSingleton<SignatureCheckService>();
        builder.Services.AddSingleton<PasswordService>();
        builder.Services.AddSingleton<CertificateSignService>();
        builder.Services.AddSingleton<ChuvadiReader.Core.Licensing.IEntitlements, ChuvadiReader.Core.Licensing.DefaultEntitlements>();
        builder.Services.AddSingleton<IAppReadySignal, AppReadySignal>();

        // ── Android platform services ──
        builder.Services.AddSingleton<IUiScale, AndroidUiScale>();
        builder.Services.AddSingleton<IExternalLinks, AndroidExternalLinks>();
        builder.Services.AddSingleton<IPrintService, AndroidPrintService>();
        builder.Services.AddSingleton<DocumentImport>();
        builder.Services.AddSingleton<IFilePicker, AndroidFilePicker>();
        builder.Services.AddSingleton<IImageClipboard, AndroidImageClipboard>();
        builder.Services.AddSingleton<IWindowControls, AndroidWindowControls>();

        return builder.Build();
    }
}
