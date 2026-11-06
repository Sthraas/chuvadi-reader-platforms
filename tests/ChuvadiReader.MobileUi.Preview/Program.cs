using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.MobileUi.Preview;
using ChuvadiReader.Platform;

// TESTING ONLY. CHVD_FF = phone | tablet | desktop | web (default phone). Desktop reports Windows so the
// desktop chrome renders exactly as the WPF host shows it; phone and tablet report Android.
var ff = (Environment.GetEnvironmentVariable("CHVD_FF") ?? "phone").ToLowerInvariant() switch
{
    "tablet" => FormFactor.Tablet,
    "desktop" or "web" => FormFactor.Desktop,
    _ => FormFactor.Phone,
};

var builder = WebApplication.CreateBuilder(args);
// One screenshot = one browser session; app state is process-wide (like the desktop app), so drop a
// session's components the moment its browser closes instead of keeping them registered for minutes.
builder.Services.AddRazorComponents().AddInteractiveServerComponents(o => o.DisconnectedCircuitRetentionPeriod = TimeSpan.Zero);
builder.Services.AddChuvadiReader(AppStateLifetime.Process);
builder.Services.AddSingleton<IAppStorage, MemoryStorage>();
builder.Services.AddSingleton<IFilePicker, FixturePicker>();
builder.Services.AddSingleton<IImageClipboard, NoClipboard>();
builder.Services.AddSingleton<IClipboard, NoClipboard>();
var web = Environment.GetEnvironmentVariable("CHVD_FF") == "web";
builder.Services.AddSingleton<IPlatformInfo>(new PreviewPlatform(ff, web));
if (ff != FormFactor.Desktop)
{
    // Stands in for Android's bundled .NET runtime notices (IHostNotices).
    builder.Services.AddSingleton<IHostNotices, PreviewHostNotices>();
}
if (web)
{
    // The Web host registers these from its configuration; the preview uses the placeholders.
    builder.Services.AddSingleton(new ChuvadiReader.Ui.Components.Platform.Portal.PortalLinks(ChuvadiReader.Ui.Components.Platform.Portal.PortalLinks.PlaceholderDesktopAppUrl, null, TermsUrl: "/licence"));
}

var app = builder.Build();
app.UseAntiforgery();
app.MapStaticAssets();
app.MapRazorComponents<ChuvadiReader.MobileUi.Preview.Components.HostPage>()
   .AddInteractiveServerRenderMode()
   .AddAdditionalAssemblies(typeof(ChuvadiReader.Ui.App).Assembly);

// Two documents open, like 12g ("1 of 2 tabs" here; the frame shows 4).
var tabs = app.Services.GetRequiredService<TabsService>();
var shell = app.Services.GetRequiredService<ShellService>();
// A small library in category folders, so Library's list and shelf have something to show.
var lib = app.Services.GetRequiredService<SaveFolderService>().BaseFolder;
foreach (var (cat, name, pages) in new[]
{
    ("Clinical", "lab-report-meena-r.pdf", 4), ("Clinical", "discharge-summary.pdf", 12), ("Clinical", "ot-checklist-v3.pdf", 3),
    ("Finance", "insurance-claims.pdf", 9), ("Finance", "tariff-2026.pdf", 48), ("Legal", "consent-form-signed.pdf", 2),
    ("Legal", "vendor-agreement.pdf", 18),
})
{
    if (!File.Exists(Path.Combine(lib, cat, name)))
    {
        Fixtures.Document(Path.Combine(lib, cat), name, pages);
    }
}

await tabs.RestoreAsync();   // as Dashboard/Reader do first, so the fixtures aren't added twice
var a = Fixtures.Document("discharge-summary.pdf", 13);
var b = Fixtures.Document("lab-report.pdf", 4);
await tabs.OpenAsync(b, Path.GetFileName(b), DocumentFormat.Pdf);
var first = await tabs.OpenAsync(a, Path.GetFileName(a), DocumentFormat.Pdf);
shell.SetMode(DocMode.Read, first.Id);

app.Run();
