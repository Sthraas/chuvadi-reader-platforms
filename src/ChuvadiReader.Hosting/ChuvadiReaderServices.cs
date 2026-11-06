using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Licensing;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Theme;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace ChuvadiReader.Hosting;

/// <summary>How long app state lives.</summary>
public enum AppStateLifetime
{
    /// <summary>One person per process: Windows, macOS, Linux, Android.</summary>
    Process,

    /// <summary>One set of services per browser connection (Blazor Server circuit). Required for Web,
    /// otherwise every signed-in person would share the same tabs, recents and settings.</summary>
    PerConnection,
}

public static class ChuvadiReaderServices
{
    /// <summary>
    /// Registers every Core service exactly as the Windows host does today (App.xaml.cs, chuvadi-reader
    /// main c7b9e44), plus safe defaults for each platform seam. Call it first, then register the
    /// host's own implementations: a later registration of the same interface wins.
    /// </summary>
    public static IServiceCollection AddChuvadiReader(this IServiceCollection services, AppStateLifetime lifetime)
    {
        void Add<TService, TImpl>()
            where TService : class
            where TImpl : class, TService
        {
            if (lifetime == AppStateLifetime.Process) services.AddSingleton<TService, TImpl>();
            else services.AddScoped<TService, TImpl>();
        }

        void Self<T>()
            where T : class => Add<T, T>();

        // Same order and set as App.xaml.cs. Keep in step with it until Windows switches to this method.
        Self<SaveFolderService>();
        Self<CategoryService>();
        Self<ThemeService>();
        Self<UserProfileService>();
        Self<RecentFilesService>();
        Self<PinnedService>();
        Self<WatchedFolderService>();
        Self<LibraryService>();
        Self<TagService>();
        Self<FolderSearchService>();
        Self<DocumentPropertiesService>();
        Self<ExportService>();
        Self<RedactService>();
        Self<StampService>();
        Self<DocxViewService>();
        Self<XlsxViewService>();
        Self<FlattenService>();
        Self<RecoveryService>();
        Self<PressService>();
        Add<IPdfReader, ChuvadiPdfReader>();
        Self<TabsService>();
        Self<PdfToolsService>();
        Self<BenchComposer>();
        Self<BenchService>();
        Self<SessionService>();
        Self<OpenDocumentService>();
        Self<BenchDropService>();
        Self<RedactRequestService>();
        Self<ShellService>();
        Self<PreferencesService>();
        Self<TextViewService>();
        Self<MeasureService>();
        Self<SignatureCheckService>();
        Self<PasswordService>();
        Self<CertificateSignService>();
        Add<IEntitlements, DefaultEntitlements>();
        Add<IAppReadySignal, AppReadySignal>();
        Add<IAppCommands, ShellAppCommands>();

        // Platform seams: harmless defaults. Each host replaces the ones it supports.
        services.TryAdd(Describe<IUiScale, NoopUiScale>(lifetime));
        services.TryAdd(Describe<IExternalLinks, NoExternalLinks>(lifetime));
        services.TryAdd(Describe<IWindowControls, NoopWindowControls>(lifetime));
        services.TryAdd(Describe<IPrintService, NoopPrintService>(lifetime));
        services.TryAdd(Describe<IFileWriteBack, NoFileWriteBack>(lifetime));
        services.TryAdd(Describe<IAppPaths, Desktop.DesktopAppPaths>(lifetime));
        services.TryAdd(Describe<IAccount, LocalAccount>(lifetime));
        services.TryAdd(Describe<IAppLifecycle, NoAppLifecycle>(lifetime));
        return services;
    }

    private static ServiceDescriptor Describe<TService, TImpl>(AppStateLifetime lifetime)
        where TService : class
        where TImpl : class, TService =>
        lifetime == AppStateLifetime.Process
            ? ServiceDescriptor.Singleton<TService, TImpl>()
            : ServiceDescriptor.Scoped<TService, TImpl>();
}
