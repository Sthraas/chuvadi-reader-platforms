using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Ui.Components.Platform.Portal;
using ChuvadiReader.WebUi.Preview;
using ChuvadiReader.WebUi.Preview.Components;

var builder = WebApplication.CreateBuilder(args);
var platformName = Environment.GetEnvironmentVariable("PREVIEW_PLATFORM");

builder.Services.AddRazorComponents().AddInteractiveServerComponents();
builder.Services.AddChuvadiReader(AppStateLifetime.PerConnection);
builder.Services.AddScoped<IAppStorage, MemoryStorage>();
builder.Services.AddScoped<IFilePicker, NoPicker>();
builder.Services.AddScoped<NoClipboard>();
builder.Services.AddScoped<IImageClipboard>(sp => sp.GetRequiredService<NoClipboard>());
builder.Services.AddScoped<IClipboard>(sp => sp.GetRequiredService<NoClipboard>());
builder.Services.AddScoped<IAccount, FakeSangamAccount>();
builder.Services.AddSingleton(PreviewPlatforms.From(platformName, Environment.GetEnvironmentVariable("PREVIEW_FORMFACTOR")));
builder.Services.AddSingleton(new PortalLinks(PortalLinks.PlaceholderDesktopAppUrl, "https://sangam.example/account", "/terms", "/privacy"));

var app = builder.Build();
app.UseStaticFiles();
app.UseAntiforgery();
app.MapStaticAssets();
app.MapRazorComponents<App>().AddInteractiveServerRenderMode()
    .AddAdditionalAssemblies(typeof(ChuvadiReader.Ui.Layout.MainLayout).Assembly);
app.Run();
