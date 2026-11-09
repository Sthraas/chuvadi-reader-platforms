using System.Diagnostics.CodeAnalysis;
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
    /// <summary>
    /// Registers every Core service exactly as the Windows host does today (App.xaml.cs, chuvadi-reader
    /// main c7b9e44), plus safe defaults for each platform seam. Call it first, then register the
    /// host's own implementations: a later registration of the same interface wins.
    /// </summary>
    /// <remarks>
    /// AT-03, structural (D-146): every registration is a typed <c>Core&lt;TService, TImpl&gt;</c> or
    /// <c>Seam&lt;TService, TImpl&gt;</c> call. The compiler checks that the implementation implements the
    /// service, and the trimmer sees each implementation as a generic argument annotated to keep its public
    /// constructors, so a trimmed app (Android Release, Mac Catalyst, any AOT host) can always build it. There is
    /// no table of <see cref="Type"/> values: the trim analyser can't follow Type values through an array, which
    /// is how AT-03 slipped past it. A new seam default is one more <c>Seam</c> line, with nothing else to remember.
    /// </remarks>
    public static IServiceCollection AddChuvadiReader(this IServiceCollection services, AppStateLifetime lifetime)
    {
        var life = lifetime == AppStateLifetime.Process ? ServiceLifetime.Singleton : ServiceLifetime.Scoped;

        // Same set and order as the Windows host registered on chuvadi-reader main c7b9e44 (App.xaml.cs).
        Core<SaveFolderService, SaveFolderService>(services, life);
        Core<CategoryService, CategoryService>(services, life);
        Core<ThemeService, ThemeService>(services, life);
        Core<UserProfileService, UserProfileService>(services, life);
        Core<RecentFilesService, RecentFilesService>(services, life);
        Core<PinnedService, PinnedService>(services, life);
        Core<WatchedFolderService, WatchedFolderService>(services, life);
        Core<LibraryService, LibraryService>(services, life);
        Core<TagService, TagService>(services, life);
        Core<FolderSearchService, FolderSearchService>(services, life);
        Core<DocumentPropertiesService, DocumentPropertiesService>(services, life);
        Core<ExportService, ExportService>(services, life);
        Core<RedactService, RedactService>(services, life);
        Core<StampService, StampService>(services, life);
        Core<DocxViewService, DocxViewService>(services, life);
        Core<XlsxViewService, XlsxViewService>(services, life);
        Core<FlattenService, FlattenService>(services, life);
        Core<RecoveryService, RecoveryService>(services, life);
        Core<PressService, PressService>(services, life);
        Core<IPdfReader, ChuvadiPdfReader>(services, life);
        Core<TabsService, TabsService>(services, life);
        Core<PdfToolsService, PdfToolsService>(services, life);
        Core<BenchComposer, BenchComposer>(services, life);
        Core<BenchService, BenchService>(services, life);
        Core<SessionService, SessionService>(services, life);
        Core<OpenDocumentService, OpenDocumentService>(services, life);
        Core<BenchDropService, BenchDropService>(services, life);
        Core<RedactRequestService, RedactRequestService>(services, life);
        Core<ShellService, ShellService>(services, life);
        Core<PreferencesService, PreferencesService>(services, life);
        Core<TextViewService, TextViewService>(services, life);
        Core<MeasureService, MeasureService>(services, life);
        Core<SignatureCheckService, SignatureCheckService>(services, life);
        Core<PasswordService, PasswordService>(services, life);
        Core<CertificateSignService, CertificateSignService>(services, life);
        Core<IEntitlements, DefaultEntitlements>(services, life);
        Core<IAppReadySignal, AppReadySignal>(services, life);
        Core<IAppCommands, ShellAppCommands>(services, life);
        Core<IncomingFiles, IncomingFiles>(services, life);

        // Platform seams: harmless defaults. Each host replaces the ones it supports.
        Seam<IUiScale, NoopUiScale>(services, life);
        Seam<IExternalLinks, NoExternalLinks>(services, life);
        Seam<IWindowControls, NoopWindowControls>(services, life);
        Seam<IPrintService, NoopPrintService>(services, life);
        Seam<IAppInstance, NoAppInstance>(services, life);
        Seam<IHostNotices, NoHostNotices>(services, life);
        Seam<IDroppedFiles, NoDroppedFiles>(services, life);
        Seam<IFileWriteBack, NoFileWriteBack>(services, life);
        Seam<IAppPaths, Desktop.DesktopAppPaths>(services, life);
        Seam<IAccount, LocalAccount>(services, life);
        Seam<IAppLifecycle, NoAppLifecycle>(services, life);
        Seam<IFileManager, NoFileManager>(services, life);
        Seam<IPathLabels, PlainPathLabels>(services, life);

        return services;
    }

    // Generic methods over reference types share one compiled body, so this adds no per-service JIT work at startup.
    private static void Core<TService, [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TImpl>(
        IServiceCollection services, ServiceLifetime life)
        where TService : class
        where TImpl : class, TService =>
        services.Add(new ServiceDescriptor(typeof(TService), typeof(TImpl), life));

    private static void Seam<TService, [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TImpl>(
        IServiceCollection services, ServiceLifetime life)
        where TService : class
        where TImpl : class, TService =>
        services.TryAdd(new ServiceDescriptor(typeof(TService), typeof(TImpl), life));
}
