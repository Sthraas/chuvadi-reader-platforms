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
    public static IServiceCollection AddChuvadiReader(this IServiceCollection services, AppStateLifetime lifetime)
    {
        // Non-generic descriptors on purpose: no generic instantiations to JIT at startup.
        var life = lifetime == AppStateLifetime.Process ? ServiceLifetime.Singleton : ServiceLifetime.Scoped;

        // Same set as the Windows host registered on chuvadi-reader main c7b9e44 (App.xaml.cs).
        foreach (var r in CoreServices)
        {
            services.Add(new ServiceDescriptor(r.Service, r.Impl, life));
        }

        // Platform seams: harmless defaults. Each host replaces the ones it supports.
        foreach (var r in SeamDefaults)
        {
            services.TryAdd(new ServiceDescriptor(r.Service, r.Impl, life));
        }

        return services;
    }

    /// <summary>
    /// One registration. AT-03: the implementation type carries <see cref="DynamicallyAccessedMembersAttribute"/>
    /// (public constructors), so a trimmed app (Android Release, Mac Catalyst, any AOT host) keeps the
    /// constructors the container calls. As an untyped (Type, Type) tuple the trimmer couldn't see that use and
    /// removed them from the trimmable Platform assembly, and the Android Release app died at launch.
    /// Still non-generic: nothing extra to JIT at startup.
    /// </summary>
    private readonly record struct Registration(
        Type Service,
        [property: DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)]
        [param: DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)]
        Type Impl);

    private static readonly Registration[] CoreServices =
    {
        new(typeof(SaveFolderService), typeof(SaveFolderService)),
        new(typeof(CategoryService), typeof(CategoryService)),
        new(typeof(ThemeService), typeof(ThemeService)),
        new(typeof(UserProfileService), typeof(UserProfileService)),
        new(typeof(RecentFilesService), typeof(RecentFilesService)),
        new(typeof(PinnedService), typeof(PinnedService)),
        new(typeof(WatchedFolderService), typeof(WatchedFolderService)),
        new(typeof(LibraryService), typeof(LibraryService)),
        new(typeof(TagService), typeof(TagService)),
        new(typeof(FolderSearchService), typeof(FolderSearchService)),
        new(typeof(DocumentPropertiesService), typeof(DocumentPropertiesService)),
        new(typeof(ExportService), typeof(ExportService)),
        new(typeof(RedactService), typeof(RedactService)),
        new(typeof(StampService), typeof(StampService)),
        new(typeof(DocxViewService), typeof(DocxViewService)),
        new(typeof(XlsxViewService), typeof(XlsxViewService)),
        new(typeof(FlattenService), typeof(FlattenService)),
        new(typeof(RecoveryService), typeof(RecoveryService)),
        new(typeof(PressService), typeof(PressService)),
        new(typeof(IPdfReader), typeof(ChuvadiPdfReader)),
        new(typeof(TabsService), typeof(TabsService)),
        new(typeof(PdfToolsService), typeof(PdfToolsService)),
        new(typeof(BenchComposer), typeof(BenchComposer)),
        new(typeof(BenchService), typeof(BenchService)),
        new(typeof(SessionService), typeof(SessionService)),
        new(typeof(OpenDocumentService), typeof(OpenDocumentService)),
        new(typeof(BenchDropService), typeof(BenchDropService)),
        new(typeof(RedactRequestService), typeof(RedactRequestService)),
        new(typeof(ShellService), typeof(ShellService)),
        new(typeof(PreferencesService), typeof(PreferencesService)),
        new(typeof(TextViewService), typeof(TextViewService)),
        new(typeof(MeasureService), typeof(MeasureService)),
        new(typeof(SignatureCheckService), typeof(SignatureCheckService)),
        new(typeof(PasswordService), typeof(PasswordService)),
        new(typeof(CertificateSignService), typeof(CertificateSignService)),
        new(typeof(IEntitlements), typeof(DefaultEntitlements)),
        new(typeof(IAppReadySignal), typeof(AppReadySignal)),
        new(typeof(IAppCommands), typeof(ShellAppCommands)),
        new(typeof(IncomingFiles), typeof(IncomingFiles)),
    };

    private static readonly Registration[] SeamDefaults =
    {
        new(typeof(IUiScale), typeof(NoopUiScale)),
        new(typeof(IExternalLinks), typeof(NoExternalLinks)),
        new(typeof(IWindowControls), typeof(NoopWindowControls)),
        new(typeof(IPrintService), typeof(NoopPrintService)),
        new(typeof(IAppInstance), typeof(NoAppInstance)),
        new(typeof(IHostNotices), typeof(NoHostNotices)),
        new(typeof(IDroppedFiles), typeof(NoDroppedFiles)),
        new(typeof(IFileWriteBack), typeof(NoFileWriteBack)),
        new(typeof(IAppPaths), typeof(Desktop.DesktopAppPaths)),
        new(typeof(IAccount), typeof(LocalAccount)),
        new(typeof(IAppLifecycle), typeof(NoAppLifecycle)),
        new(typeof(IFileManager), typeof(NoFileManager)),
    };
}
