using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Components;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Hosting.Acme;
using ChuvadiReader.Web.Hosting.Workers;
using ChuvadiReader.Web.Platform;
using ChuvadiReader.Web.Auth;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.Extensions.DependencyInjection.Extensions;
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
        var mode = builder.Configuration.GetValue("Portal:Mode", PortalMode.Single);

        // ── settings ────────────────────────────────────────────────────────────────────
        builder.Services.AddOptions<PortalOptions>()
            .Bind(builder.Configuration.GetSection(PortalOptions.Section))
            .Validate(o => !string.IsNullOrWhiteSpace(o.DataRoot), "Portal:DataRoot is required.")
            .Validate(o => devSignIn || o.Mode == PortalMode.Worker || Uri.TryCreate(o.PublicOrigin, UriKind.Absolute, out var u) && u.Scheme == Uri.UriSchemeHttps,
                "Portal:PublicOrigin must be the portal's https address outside Development.")
            .Validate(o => o.UploadChunkBytes is >= 64 * 1024 and <= 16 * 1024 * 1024, "Portal:UploadChunkBytes must be 64 KB–16 MB.")
            .Validate(o => o.IdleTimeout > o.ExpiryWarning && o.ExpiryWarning > TimeSpan.Zero, "Portal:IdleTimeout must be longer than Portal:ExpiryWarning.")
            .Validate(o => o.Mode != PortalMode.Worker || !string.IsNullOrEmpty(o.WorkerSocket) && !string.IsNullOrEmpty(o.WorkerOwner),
                "A worker is started by the gateway only.")
            .ValidateOnStart();
        builder.Services.AddOptions<SangamOptions>().Bind(builder.Configuration.GetSection(SangamOptions.Section));
        builder.Services.AddSingleton(TimeProvider.System);

        // D-28: outside Development, working copies must be in RAM and never paged to disk in the clear.
        if (!devSignIn && mode != PortalMode.Worker)
        {
            var portal = builder.Configuration.GetSection(PortalOptions.Section).Get<PortalOptions>() ?? new();
            if (!string.IsNullOrWhiteSpace(portal.DataRoot)
                && StorageCheck.Problems(portal.DataRoot, portal.Storage) is { Count: > 0 } problems)
            {
                throw new InvalidOperationException("The portal won't start: " + string.Join(" ", problems));
            }
        }

        switch (mode)
        {
            case PortalMode.Worker:
                ConfigureWorker(builder);
                break;
            case PortalMode.Gateway:
                ConfigureFront(builder, devSignIn, gateway: true);
                break;
            default:
                ConfigureFront(builder, devSignIn, gateway: false);
                break;
        }

        // Keys for cookies, sign-in flows and circuit state live in memory only: nothing outlives the
        // process, and a restart ends every session anyway (no server storage; D-24, D-28). Sangam signs a
        // person straight back in if their Sangam session is still on.
        builder.Services.Configure<Microsoft.AspNetCore.DataProtection.KeyManagement.KeyManagementOptions>(o =>
        {
            o.XmlRepository = new InMemoryKeyRepository();
            o.XmlEncryptor = new Microsoft.AspNetCore.DataProtection.XmlEncryption.NullXmlEncryptor(); // never written anywhere
        });

        var app = builder.Build();
        var sangam = app.Services.GetRequiredService<IOptions<SangamOptions>>().Value;

        if (mode == PortalMode.Worker)
        {
            // Reached only through the gateway's socket; the gateway did TLS, sign-in and security headers.
            app.UseGatewayForwarding();
            app.UseAuthentication();
            app.UseAuthorization();
            app.UseAntiforgery();
            app.MapStaticAssets().AllowAnonymous();
            app.MapPortalFiles();
            app.MapWorkerControl();
            MapReader(app);
            return app;
        }

        if (!env.IsDevelopment())
        {
            app.UseExceptionHandler("/error", createScopeForErrors: !(mode == PortalMode.Gateway));
        }

        // ACME http-01 answers come first: plain HTTP, no redirect, no sign-in.
        app.UseHttp01Challenges();
        app.UsePortalSecurityHeaders(hsts: !devSignIn);
        if (!devSignIn)
        {
            app.UseHttpsRedirection();
        }

        if (mode == PortalMode.Gateway)
        {
            app.UseWebSockets();
        }

        app.UseAuthentication();
        app.UseActivityTracking();
        app.UseAuthorization();
        if (mode == PortalMode.Single)
        {
            app.UseAntiforgery();
        }

        app.MapStaticAssets().AllowAnonymous();
        app.MapGet("/healthz", () => Results.Text("ok")).AllowAnonymous(); // for the host's monitoring; says nothing else
        app.MapActivity();
        if (sangam.IsConfigured)
        {
            app.MapSangamSignIn();
        }

        app.MapSignedOutPage(withSangam: sangam.IsConfigured);
        if (mode == PortalMode.Gateway)
        {
            app.MapGatewayRelay();
        }
        else
        {
            app.MapPortalFiles();
            MapReader(app);
        }

        return app;
    }

    private static void MapReader(WebApplication app)
        => app.MapRazorComponents<HostPage>()
            .AddInteractiveServerRenderMode()
            .AddAdditionalAssemblies(typeof(ChuvadiReader.Ui.App).Assembly);

    /// <summary>What faces the browser: TLS, sign-in, session expiry. The single process also runs the
    /// Reader; the gateway relays to each person's worker instead (D-24).</summary>
    private static void ConfigureFront(WebApplicationBuilder builder, bool devSignIn, bool gateway)
    {
        // ── Kestrel: TLS from a pluggable source, small default body limit ────────────
        var tls = builder.Configuration.GetSection(TlsOptions.Section).Get<TlsOptions>();
        builder.WebHost.ConfigureKestrel((context, k) =>
        {
            k.AddServerHeader = false;
            k.Limits.MaxRequestBodySize = 64 * 1024; // uploads raise it per chunk (FileEndpoints, GatewayRelay)
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
        var acme = builder.Configuration.GetSection(AcmeOptions.Section).Get<AcmeOptions>() ?? new();
        builder.Services.Configure<AcmeOptions>(builder.Configuration.GetSection(AcmeOptions.Section));
        builder.Services.AddSingleton<Http01ChallengeStore>();
        if (acme.Enabled && (tls is not { CertificatePath.Length: > 0, KeyPath.Length: > 0 } || acme.Domains.Count == 0 || string.IsNullOrWhiteSpace(acme.AccountFolder)))
        {
            throw new InvalidOperationException("ACME needs Portal:Tls:CertificatePath, Portal:Tls:KeyPath, Portal:Tls:Acme:Domains and Portal:Tls:Acme:AccountFolder.");
        }

        if (tls is { CertificatePath.Length: > 0 } && acme.Enabled)
        {
            // Let's Encrypt through our own ACME client: ordered, renewed and hot-swapped in the background.
            builder.Services.TryAddSingleton<IHttpClientFactoryLite, DefaultHttpClientFactoryLite>();
            builder.Services.AddSingleton(sp => new AcmeCertificateManager(tls, acme, sp.GetRequiredService<TimeProvider>(),
                sp.GetRequiredService<ILogger<AcmeCertificateManager>>()));
            builder.Services.AddSingleton<ICertificateSource>(sp => sp.GetRequiredService<AcmeCertificateManager>());
            builder.Services.AddSingleton<AcmeRenewalService>();
            builder.Services.AddHostedService(sp => sp.GetRequiredService<AcmeRenewalService>());
        }
        else if (tls is { CertificatePath.Length: > 0 })
        {
            // A PEM pair renewed by something else; re-read when it changes.
            builder.Services.AddSingleton<ICertificateSource>(sp =>
                new PemFileCertificateSource(tls, sp.GetRequiredService<ILogger<PemFileCertificateSource>>(), sp.GetRequiredService<TimeProvider>()));
        }

        // ── sign-in ─────────────────────────────────────────────────────────────────────
        var sangam = builder.Configuration.GetSection(SangamOptions.Section).Get<SangamOptions>() ?? new();
        builder.Services.TryAddSingleton<IHttpClientFactoryLite, DefaultHttpClientFactoryLite>();
        if (sangam.IsConfigured)
        {
            // Sangam sign-in: our own OpenID Connect client (Auth/), the framework's cookie for the portal session.
            builder.Services.AddSingleton<SangamMetadata>();
            builder.Services.AddSingleton<JwtVerifier>();
            builder.Services.AddSingleton<ClientAuthentication>();
            builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
                .AddCookie(o =>
                {
                    var https = Uri.TryCreate(builder.Configuration["Portal:PublicOrigin"], UriKind.Absolute, out var origin) && origin.Scheme == Uri.UriSchemeHttps;
                    o.Cookie.Name = https ? "__Host-chvd" : "chvd.session";
                    o.Cookie.HttpOnly = true;
                    o.Cookie.SameSite = SameSiteMode.Lax;
                    o.Cookie.SecurePolicy = https ? CookieSecurePolicy.Always : CookieSecurePolicy.SameAsRequest;
                    o.Cookie.Path = "/";
                    o.SlidingExpiration = false;
                    o.ExpireTimeSpan = sangam.AbsoluteSessionLifetime;
                    o.LoginPath = "/signin";
                    o.ReturnUrlParameter = "returnUrl";
                    o.Events.OnValidatePrincipal = SangamSignIn.ValidatePrincipalAsync;
                    o.Events.OnRedirectToLogin = context =>
                    {
                        // Pages go to Sangam; file and circuit requests just get 401.
                        var path = context.Request.Path;
                        if (path.StartsWithSegments("/portal") || path.StartsWithSegments("/_blazor"))
                        {
                            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                        }
                        else
                        {
                            context.Response.Redirect(context.RedirectUri);
                        }

                        return Task.CompletedTask;
                    };
                });
        }
        else if (devSignIn)
        {
            builder.Services.AddAuthentication(DevelopmentSignInHandler.SchemeName)
                .AddScheme<AuthenticationSchemeOptions, DevelopmentSignInHandler>(DevelopmentSignInHandler.SchemeName, null);
        }
        else
        {
            throw new InvalidOperationException("Sangam:Authority and Sangam:ClientId are required outside Development.");
        }

        builder.Services.AddAuthorization(o => o.FallbackPolicy = o.DefaultPolicy);

        // ── sign-ins, their tabs and their expiry (D-30) ────────────────────────────────
        builder.Services.AddSingleton<PortalSessions>();
        builder.Services.AddSingleton<SessionClock>();
        builder.Services.AddHostedService<SessionClockService>();
        if (gateway)
        {
            // Each person's Reader runs in their own worker process (D-24).
            builder.Services.AddSingleton<WorkerPool>();
            builder.Services.AddSingleton<ITabControl>(sp => sp.GetRequiredService<WorkerPool>());
            builder.Services.AddHostedService<WorkerSupervisor>();
            return;
        }

        builder.Services.AddSingleton<OpenTabs>();
        builder.Services.AddSingleton<ITabControl>(sp => sp.GetRequiredService<OpenTabs>());
        AddReaderHost(builder);
    }

    /// <summary>One person's Reader behind the gateway (D-24): a Unix socket, the gateway's identity, no TLS.</summary>
    private static void ConfigureWorker(WebApplicationBuilder builder)
    {
        var socket = builder.Configuration["Portal:WorkerSocket"];
        builder.WebHost.ConfigureKestrel(k =>
        {
            k.AddServerHeader = false;
            k.Limits.MaxRequestBodySize = 64 * 1024;
            k.Limits.MaxRequestHeadersTotalSize = 32 * 1024;
            if (!string.IsNullOrEmpty(socket))
            {
                File.Delete(socket);
                k.ListenUnixSocket(socket);
            }
        });
        builder.Services.AddSingleton(WorkerHost.ReadSecret());
        builder.Services.AddHostedService<GatewayLifeline>();
        builder.Services.AddAuthentication(GatewayIdentityHandler.SchemeName)
            .AddScheme<AuthenticationSchemeOptions, GatewayIdentityHandler>(GatewayIdentityHandler.SchemeName, null);
        builder.Services.AddAuthorization(o => o.FallbackPolicy = o.DefaultPolicy);
        builder.Services.AddSingleton<OpenTabs>();
        builder.Services.AddSingleton<ITabControl>(sp => sp.GetRequiredService<OpenTabs>());
        AddReaderHost(builder);
    }

    /// <summary>Blazor Server and the Reader with its per-session file handling (single process or worker).</summary>
    private static void AddReaderHost(WebApplicationBuilder builder)
    {
        builder.Services.AddCascadingAuthenticationState();
        builder.Services.AddRazorComponents().AddInteractiveServerComponents(o =>
        {
            o.DetailedErrors = builder.Environment.IsDevelopment();
            o.DisconnectedCircuitRetentionPeriod = TimeSpan.FromMinutes(3);
            o.DisconnectedCircuitMaxRetained = 500;
            o.JSInteropDefaultCallTimeout = TimeSpan.FromMinutes(1);
        }).AddHubOptions(o =>
        {
            o.MaximumReceiveMessageSize = 64 * 1024;
        });

        builder.Services.AddSingleton<TransferRegistry>();
        builder.Services.AddSingleton<CircuitCounter>();
        builder.Services.AddHostedService<PortalHousekeeping>();

        // ── per-session (per circuit) services ──────────────────────────────────────────
        builder.Services.AddScoped<SessionSpace>();
        builder.Services.AddScoped<BrowserBridge>();
        builder.Services.AddScoped<OutboxDelivery>();
        builder.Services.AddScoped<CircuitHandler, SessionLifetime>();
        AddReader(builder.Services);
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
        s.AddSingleton(sp =>
        {
            var o = sp.GetRequiredService<IOptions<PortalOptions>>().Value;
            return new ChuvadiReader.Ui.Components.Platform.Portal.PortalLinks(
                o.DesktopAppUrl, NullIfEmpty(o.AccountSettingsUrl), NullIfEmpty(o.ForgotPasswordUrl));
        });
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

    private static string? NullIfEmpty(string? s) => string.IsNullOrWhiteSpace(s) ? null : s;
}
