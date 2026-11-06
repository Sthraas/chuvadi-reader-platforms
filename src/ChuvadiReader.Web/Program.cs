using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Components;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Components.Server.Circuits;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web;

public static class Program
{
    public static void Main(string[] args) => Build(args).Run();

    /// <summary>Builds the portal. Separate from <see cref="Main"/> so tests can host it.</summary>
    public static WebApplication Build(string[] args, Action<WebApplicationBuilder>? configure = null)
    {
        // The application name names the static-asset manifest; fixed so a test host finds ours.
        var builder = WebApplication.CreateBuilder(new WebApplicationOptions
        {
            Args = args,
            ApplicationName = typeof(Program).Assembly.GetName().Name,
        });
        configure?.Invoke(builder);
        var env = builder.Environment;
        var devSignIn = env.IsDevelopment() || env.IsEnvironment("Testing");

        // ── settings ────────────────────────────────────────────────────────────────────
        builder.Services.AddOptions<PortalOptions>()
            .Bind(builder.Configuration.GetSection(PortalOptions.Section))
            .Validate(o => !string.IsNullOrWhiteSpace(o.DataRoot), "Portal:DataRoot is required.")
            .Validate(o => devSignIn || Uri.TryCreate(o.PublicOrigin, UriKind.Absolute, out var u) && u.Scheme == Uri.UriSchemeHttps,
                "Portal:PublicOrigin must be the portal's https address outside Development.")
            .Validate(o => o.UploadChunkBytes is >= 64 * 1024 and <= 16 * 1024 * 1024, "Portal:UploadChunkBytes must be 64 KB–16 MB.")
            .ValidateOnStart();

        // ── Kestrel: TLS from a pluggable source, small default body limit ────────────
        var tls = builder.Configuration.GetSection(TlsOptions.Section).Get<TlsOptions>();
        builder.WebHost.ConfigureKestrel((context, k) =>
        {
            k.AddServerHeader = false;
            k.Limits.MaxRequestBodySize = 64 * 1024; // uploads raise it per chunk (FileEndpoints)
            k.Limits.MaxRequestHeadersTotalSize = 32 * 1024;
            k.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(30);
            if (tls is { CertificatePath.Length: > 0 })
            {
                k.ConfigureHttpsDefaults(h =>
                {
                    var source = k.ApplicationServices.GetRequiredService<ICertificateSource>();
                    h.ServerCertificateSelector = (_, _) => source.Current;
                    h.SslProtocols = System.Security.Authentication.SslProtocols.Tls12 | System.Security.Authentication.SslProtocols.Tls13;
                });
            }
        });
        if (tls is { CertificatePath.Length: > 0 })
        {
            builder.Services.AddSingleton<ICertificateSource>(sp =>
                new PemFileCertificateSource(tls, sp.GetRequiredService<ILogger<PemFileCertificateSource>>(), sp.GetRequiredService<TimeProvider>()));
        }

        // ── sign-in ─────────────────────────────────────────────────────────────────────
        if (devSignIn)
        {
            builder.Services.AddAuthentication(DevelopmentSignInHandler.SchemeName)
                .AddScheme<AuthenticationSchemeOptions, DevelopmentSignInHandler>(DevelopmentSignInHandler.SchemeName, null);
        }
        else
        {
            // The Sangam client (our own OpenID Connect code) is the next step; until it exists the
            // portal must not run anywhere but Development or Testing.
            throw new InvalidOperationException("Sangam sign-in is not wired yet; run with ASPNETCORE_ENVIRONMENT=Development.");
        }

        builder.Services.AddAuthorization(o => o.FallbackPolicy = o.DefaultPolicy);
        builder.Services.AddCascadingAuthenticationState();

        // ── Blazor Server ───────────────────────────────────────────────────────────────
        builder.Services.AddRazorComponents().AddInteractiveServerComponents(o =>
        {
            o.DetailedErrors = env.IsDevelopment();
            o.DisconnectedCircuitRetentionPeriod = TimeSpan.FromMinutes(3);
            o.DisconnectedCircuitMaxRetained = 500;
            o.JSInteropDefaultCallTimeout = TimeSpan.FromMinutes(1);
        }).AddHubOptions(o =>
        {
            o.MaximumReceiveMessageSize = 64 * 1024;
        });

        builder.Services.AddSingleton(TimeProvider.System);
        builder.Services.AddSingleton<TransferRegistry>();
        builder.Services.AddHostedService<PortalHousekeeping>();

        // ── per-session (per circuit) services ──────────────────────────────────────────
        builder.Services.AddScoped<SessionSpace>();
        builder.Services.AddScoped<BrowserBridge>();
        builder.Services.AddScoped<OutboxDelivery>();
        builder.Services.AddScoped<CircuitHandler, SessionLifetime>();
        AddReader(builder.Services);

        var app = builder.Build();

        if (!env.IsDevelopment())
        {
            app.UseExceptionHandler("/error", createScopeForErrors: true);
        }

        app.UsePortalSecurityHeaders(hsts: !devSignIn);
        if (!devSignIn)
        {
            app.UseHttpsRedirection();
        }

        app.UseAuthentication();
        app.UseAuthorization();
        app.UseAntiforgery();

        app.MapStaticAssets().AllowAnonymous();
        app.MapPortalFiles();
        app.MapRazorComponents<HostPage>()
            .AddInteractiveServerRenderMode()
            .AddAdditionalAssemblies(typeof(ChuvadiReader.Ui.App).Assembly);

        return app;
    }

    /// <summary>
    /// The Reader's services through the Foundation kit, one set per browser connection
    /// (<see cref="AppStateLifetime.PerConnection"/>), then the portal's own implementation of every
    /// platform seam (a later registration wins). Scoped throughout: a process serves many people.
    /// </summary>
    internal static void AddReader(IServiceCollection s)
    {
        s.AddChuvadiReader(AppStateLifetime.PerConnection);

        s.AddScoped<WebPlatformInfo>();
        s.AddScoped<IPlatformInfo>(sp => sp.GetRequiredService<WebPlatformInfo>());
        s.AddScoped<ViewportReporter>();
        s.AddScoped<WebAccount>();
        s.AddScoped<IAccount>(sp => sp.GetRequiredService<WebAccount>());
        s.AddScoped<IAppPaths, SessionAppPaths>();
        s.AddScoped<IAppStorage, SessionAppStorage>();
        s.AddScoped<IFilePicker, WebFilePicker>();
        s.AddScoped<IFileWriteBack, WebFileWriteBack>();
        s.AddScoped<IPrintService, WebPrintService>();
        s.AddScoped<WebClipboard>();
        s.AddScoped<IClipboard>(sp => sp.GetRequiredService<WebClipboard>());
        s.AddScoped<IImageClipboard>(sp => sp.GetRequiredService<WebClipboard>());
        s.AddScoped<IExternalLinks, WebExternalLinks>();
        s.AddScoped<IUiScale, NoopUiScale>();
        s.AddScoped<IWindowControls, NoopWindowControls>();
    }
}
