using System.Reflection;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>AT-03 made structural (D-146): typed registration, same services as before.</summary>
public sealed class TypedRegistrationTests
{
    /// <summary>The registrations as the (Type, Type) tables made them before this change, in order, plus later seams.</summary>
    private static readonly string[] Before =
    [
        "SaveFolderService = SaveFolderService",
        "CategoryService = CategoryService",
        "ThemeService = ThemeService",
        "UserProfileService = UserProfileService",
        "RecentFilesService = RecentFilesService",
        "PinnedService = PinnedService",
        "WatchedFolderService = WatchedFolderService",
        "LibraryService = LibraryService",
        "TagService = TagService",
        "FolderSearchService = FolderSearchService",
        "DocumentPropertiesService = DocumentPropertiesService",
        "ExportService = ExportService",
        "RedactService = RedactService",
        "StampService = StampService",
        "DocxViewService = DocxViewService",
        "XlsxViewService = XlsxViewService",
        "FlattenService = FlattenService",
        "RecoveryService = RecoveryService",
        "PressService = PressService",
        "IPdfReader = ChuvadiPdfReader",
        "TabsService = TabsService",
        "PdfToolsService = PdfToolsService",
        "BenchComposer = BenchComposer",
        "BenchService = BenchService",
        "SessionService = SessionService",
        "OpenDocumentService = OpenDocumentService",
        "BenchDropService = BenchDropService",
        "RedactRequestService = RedactRequestService",
        "ShellService = ShellService",
        "PreferencesService = PreferencesService",
        "TextViewService = TextViewService",
        "MeasureService = MeasureService",
        "SignatureCheckService = SignatureCheckService",
        "PasswordService = PasswordService",
        "CertificateSignService = CertificateSignService",
        "IEntitlements = DefaultEntitlements",
        "IAppReadySignal = AppReadySignal",
        "IAppCommands = ShellAppCommands",
        "IncomingFiles = IncomingFiles",
        "IUiScale = NoopUiScale",
        "IExternalLinks = NoExternalLinks",
        "IWindowControls = NoopWindowControls",
        "IPrintService = NoopPrintService",
        "IAppInstance = NoAppInstance",
        "IHostNotices = NoHostNotices",
        "IDroppedFiles = NoDroppedFiles",
        "IFileWriteBack = NoFileWriteBack",
        "IAppPaths = DesktopAppPaths",
        "IAccount = LocalAccount",
        "IAppLifecycle = NoAppLifecycle",
        "IFileManager = NoFileManager",
        "IPathLabels = PlainPathLabels", // P-08 (D-146), the first default added after this test
        "IPageImageOwner = LocalPageImageOwner", // D-158
        "PageImages = PageImages",               // D-158: one per process
    ];

    [Theory]
    [InlineData(AppStateLifetime.Process, ServiceLifetime.Singleton)]
    [InlineData(AppStateLifetime.PerConnection, ServiceLifetime.Scoped)]
    public void Same_services_in_the_same_order_with_the_same_lifetime_as_before(AppStateLifetime lifetime, ServiceLifetime expected)
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(lifetime);

        Assert.Equal(Before, services.Select(d => $"{d.ServiceType.Name} = {d.ImplementationType!.Name}"));
        Assert.All(services.Where(d => d.ServiceType != typeof(ChuvadiReader.Core.Reader.PageImages)), d => Assert.Equal(expected, d.Lifetime));
        Assert.Equal(ServiceLifetime.Singleton, services.Single(d => d.ServiceType == typeof(ChuvadiReader.Core.Reader.PageImages)).Lifetime);
    }

    [Fact]
    public void A_seam_the_host_registered_first_keeps_the_hosts_implementation()
    {
        var services = new ServiceCollection();
        services.AddSingleton<IFileManager, HostFileManager>();
        services.AddChuvadiReader(AppStateLifetime.Process);

        Assert.Equal(typeof(HostFileManager), Assert.Single(services, d => d.ServiceType == typeof(IFileManager)).ImplementationType);
    }

    /// <summary>
    /// Guard: no table of Type values may come back. The trim analyser can't follow a Type through an array
    /// (proved: a (Type, Type) table built with 0 errors, and its constructor was trimmed away), so every
    /// registration must stay a typed Core/Seam call.
    /// </summary>
    [Fact]
    public void The_kit_keeps_no_tables_of_types()
    {
        var fields = typeof(ChuvadiReaderServices).GetFields(BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public);
        Assert.Empty(fields);
    }

    private sealed class HostFileManager : IFileManager
    {
        public bool IsAvailable => true;

        public Task<bool> RevealAsync(string localPath, CancellationToken ct = default) => Task.FromResult(true);
    }
}
