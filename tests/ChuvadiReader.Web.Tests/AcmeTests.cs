using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Hosting.Acme;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;

namespace ChuvadiReader.Web.Tests;

public class AcmeJwsTests
{
    [Fact]
    public void Base64url_round_trips_without_padding()
    {
        foreach (var n in new[] { 0, 1, 2, 3, 31, 32, 33 })
        {
            var data = RandomNumberGenerator.GetBytes(n);
            var s = AcmeJws.Base64Url(data);
            Assert.DoesNotContain('=', s);
            Assert.DoesNotContain('+', s);
            Assert.DoesNotContain('/', s);
            Assert.Equal(data, AcmeJws.FromBase64Url(s));
        }
    }

    [Fact]
    public void A_signed_request_verifies_and_carries_jwk_or_kid()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var withJwk = AcmeJws.Sign(key, "https://acme.test/new-account", "n1", null, new System.Text.Json.Nodes.JsonObject { ["a"] = 1 });
        var (h, payload, ok) = AcmeJws.Verify(withJwk, null);
        Assert.True(ok);
        Assert.Equal("ES256", (string)h["alg"]!);
        Assert.Equal("n1", (string)h["nonce"]!);
        Assert.NotNull(h["jwk"]);
        Assert.Null(h["kid"]);
        Assert.Equal("{\"a\":1}", payload);

        var postAsGet = AcmeJws.Sign(key, "https://acme.test/order/1", "n2", "https://acme.test/acct/1", null);
        (h, payload, ok) = AcmeJws.Verify(postAsGet, key);
        Assert.True(ok);
        Assert.Null(h["jwk"]);
        Assert.Equal("https://acme.test/acct/1", (string)h["kid"]!);
        Assert.Equal(string.Empty, payload);

        using var other = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        Assert.False(AcmeJws.Verify(postAsGet, other).SignatureValid);
    }

    [Fact]
    public void Thumbprint_is_stable_and_key_specific()
    {
        using var a = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        using var b = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        Assert.Equal(AcmeJws.Thumbprint(a), AcmeJws.Thumbprint(AcmeJws.ImportJwk(AcmeJws.Jwk(a))));
        Assert.NotEqual(AcmeJws.Thumbprint(a), AcmeJws.Thumbprint(b));
        Assert.Equal(43, AcmeJws.Thumbprint(a).Length);
        Assert.Equal("tok." + AcmeJws.Thumbprint(a), AcmeJws.KeyAuthorization("tok", a));
    }

    [Fact]
    public void Only_p256_account_keys_are_accepted()
    {
        using var p384 = ECDsa.Create(ECCurve.NamedCurves.nistP384);
        Assert.Throws<ArgumentException>(() => AcmeJws.Jwk(p384));
    }

    [Fact]
    public void The_csr_names_every_domain()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var der = AcmeClient.CreateCsr(["chuvadi.in", "www.chuvadi.in"], key);
        var csr = CertificateRequest.LoadSigningRequest(der, HashAlgorithmName.SHA256, CertificateRequestLoadOptions.UnsafeLoadCertificateExtensions);
        var names = csr.CertificateExtensions.OfType<X509SubjectAlternativeNameExtension>().Single().EnumerateDnsNames().ToList();
        Assert.Equal(["chuvadi.in", "www.chuvadi.in"], names);
    }
}

/// <summary>The real portal with ACME on, against the strict fake ACME server.</summary>
public sealed class AcmePortalTests : IAsyncLifetime
{
    private readonly FakeAcmeServer _acme = new();
    private readonly string _dir = SpaceLayoutTests.NewTempDir();
    private WebApplication? _portal;

    public async Task InitializeAsync() => await _acme.StartAsync();

    public async Task DisposeAsync()
    {
        if (_portal is not null) await _portal.DisposeAsync();
        await _acme.DisposeAsync();
    }

    private string CertPath => Path.Combine(_dir, "tls", "fullchain.pem");

    private string KeyPath => Path.Combine(_dir, "tls", "privkey.pem");

    private async Task<(Uri Http, Uri Https)> StartPortalAsync(int renewBeforeDays = 30)
    {
        _portal = Program.Build(
        [
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0;https://127.0.0.1:0",
            "--Portal:DataRoot", Path.Combine(_dir, "data"),
            "--Portal:Tls:CertificatePath", CertPath,
            "--Portal:Tls:KeyPath", KeyPath,
            "--Portal:Tls:Acme:Enabled", "true",
            "--Portal:Tls:Acme:DirectoryUrl", _acme.Directory.ToString(),
            "--Portal:Tls:Acme:Domains:0", "chuvadi.in",
            "--Portal:Tls:Acme:Domains:1", "www.chuvadi.in",
            "--Portal:Tls:Acme:ContactEmails:0", "ops@chuvadi.in",
            "--Portal:Tls:Acme:AgreeToTermsOfService", "true",
            "--Portal:Tls:Acme:AccountFolder", Path.Combine(_dir, "acme"),
            "--Portal:Tls:Acme:RenewBeforeDays", renewBeforeDays.ToString(System.Globalization.CultureInfo.InvariantCulture),
            // The portal's port is known only after it starts, so the first validation can fail; retry fast.
            "--Portal:Tls:Acme:RetryAfterFailure", "00:00:00.300",
            "--Logging:LogLevel:Default", "Warning",
        ]);
        await _portal.StartAsync();
        var addresses = _portal.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses;
        var http = new Uri(addresses.First(a => a.StartsWith("http://", StringComparison.Ordinal)));
        var https = new Uri(addresses.First(a => a.StartsWith("https://", StringComparison.Ordinal)));
        _acme.ValidationBase = http;
        return (http, https);
    }

    private static async Task<X509Certificate2> HandshakeAsync(Uri https)
    {
        using var tcp = new TcpClient();
        await tcp.ConnectAsync(https.Host, https.Port);
        X509Certificate2? seen = null;
        await using var ssl = new SslStream(tcp.GetStream(), false, (_, cert, _, _) =>
        {
            seen = new X509Certificate2(cert!);
            return true; // test CA; we only look at which certificate is served
        });
        await ssl.AuthenticateAsClientAsync(new SslClientAuthenticationOptions { TargetHost = "chuvadi.in" });
        return seen!;
    }

    private static async Task WaitForAsync(Func<bool> condition, TimeSpan limit)
    {
        var until = DateTime.UtcNow + limit;
        while (!condition())
        {
            if (DateTime.UtcNow > until) throw new TimeoutException("Condition not met in time.");
            await Task.Delay(100);
        }
    }

    [Fact]
    public async Task First_start_orders_a_certificate_and_swaps_it_in_without_restart()
    {
        var (_, https) = await StartPortalAsync();
        var manager = _portal!.Services.GetRequiredService<AcmeCertificateManager>();
        var renewals = _portal.Services.GetRequiredService<AcmeRenewalService>();

        await WaitForAsync(() => renewals.Renewals == 1, TimeSpan.FromSeconds(30));

        Assert.Empty(_acme.Violations);
        Assert.False(manager.IsTemporary);
        Assert.False(manager.NeedsRenewal());
        Assert.Equal(["chuvadi.in", "www.chuvadi.in"], AcmeCertificateManager.DnsNames(manager.Current));
        Assert.Equal(_acme.CaCertificate.Subject, manager.Current.Issuer);

        // Hot reload: the same listener now serves the issued certificate.
        using var served = await HandshakeAsync(https);
        Assert.Equal(manager.Current.Thumbprint, served.Thumbprint);

        // Stored for the next start, key owner-only; the account key too.
        Assert.True(File.Exists(CertPath));
        Assert.True(File.Exists(KeyPath));
        Assert.True(File.Exists(Path.Combine(_dir, "acme", "account.key.pem")));
        if (!OperatingSystem.IsWindows())
        {
            Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite, File.GetUnixFileMode(KeyPath));
            Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite, File.GetUnixFileMode(Path.Combine(_dir, "acme", "account.key.pem")));
        }

        // No challenge token is left published.
        Assert.Equal(0, _portal.Services.GetRequiredService<Http01ChallengeStore>().Count);
    }

    [Fact]
    public async Task Short_certificates_renew_at_two_thirds_of_their_life()
    {
        await StartPortalAsync();
        var renewals = _portal!.Services.GetRequiredService<AcmeRenewalService>();
        await WaitForAsync(() => renewals.Renewals == 1, TimeSpan.FromSeconds(30));
        var manager = _portal.Services.GetRequiredService<AcmeCertificateManager>();
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var now = DateTimeOffset.UtcNow;
        using var sixDay = new CertificateRequest("CN=chuvadi.in", key, HashAlgorithmName.SHA256).CreateSelfSigned(now, now.AddDays(6));
        using var ninetyDay = new CertificateRequest("CN=chuvadi.in", key, HashAlgorithmName.SHA256).CreateSelfSigned(now, now.AddDays(90));
        Assert.Equal(TimeSpan.FromDays(2), manager.RenewalWindow(sixDay));
        Assert.Equal(TimeSpan.FromDays(30), manager.RenewalWindow(ninetyDay));
    }

    [Fact]
    public async Task A_restart_reuses_the_stored_certificate_and_account()
    {
        await StartPortalAsync();
        var renewals = _portal!.Services.GetRequiredService<AcmeRenewalService>();
        await WaitForAsync(() => renewals.Renewals == 1, TimeSpan.FromSeconds(30));
        var first = _portal.Services.GetRequiredService<AcmeCertificateManager>().Current.Thumbprint;
        await _portal.DisposeAsync();

        await StartPortalAsync();
        var manager = _portal.Services.GetRequiredService<AcmeCertificateManager>();
        Assert.False(manager.IsTemporary);
        Assert.Equal(first, manager.Current.Thumbprint);
        Assert.False(manager.NeedsRenewal());
        await Task.Delay(500);
        Assert.Equal(1, _acme.Issued);
        Assert.Equal(1, _acme.Accounts);
    }

    [Fact]
    public async Task A_certificate_inside_the_renewal_window_is_renewed()
    {
        _acme.Backdate = TimeSpan.FromDays(65); // a 90-day certificate with 25 days left (< 30)
        await StartPortalAsync();
        var renewals = _portal!.Services.GetRequiredService<AcmeRenewalService>();
        await WaitForAsync(() => renewals.Renewals == 1, TimeSpan.FromSeconds(30));
        var manager = _portal.Services.GetRequiredService<AcmeCertificateManager>();
        Assert.True(manager.NeedsRenewal());

        var before = manager.Current.Thumbprint;
        await renewals.RenewOnceAsync(CancellationToken.None);
        Assert.NotEqual(before, manager.Current.Thumbprint);
        Assert.Equal(2, _acme.Issued);
        Assert.Equal(1, _acme.Accounts);
    }
}

/// <summary>The client against the fake server, with a minimal challenge responder.</summary>
public sealed class AcmeClientTests : IAsyncLifetime
{
    private readonly FakeAcmeServer _acme = new();
    private readonly Http01ChallengeStore _store = new();
    private WebApplication _responder = default!;

    public async Task InitializeAsync()
    {
        await _acme.StartAsync();
        var b = WebApplication.CreateSlimBuilder();
        b.WebHost.UseUrls("http://127.0.0.1:0");
        b.Services.AddSingleton(_store);
        _responder = b.Build();
        _responder.UseHttp01Challenges();
        await _responder.StartAsync();
        _acme.ValidationBase = new Uri(_responder.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
    }

    public async Task DisposeAsync()
    {
        await _responder.DisposeAsync();
        await _acme.DisposeAsync();
    }

    private AcmeClient NewClient(ECDsa key) => new(new HttpClient(), _acme.Directory, key, TimeProvider.System, NullLogger.Instance)
    {
        PollInterval = TimeSpan.FromMilliseconds(100),
        PollLimit = TimeSpan.FromSeconds(10),
    };

    [Fact]
    public async Task Bad_nonces_are_retried()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var client = NewClient(key);
        _acme.BadNonceBudget = 2;
        await client.EnsureAccountAsync(["ops@chuvadi.in"], agreeToTerms: true, default);
        var issued = await client.OrderCertificateAsync(["chuvadi.in"], _store, default);
        Assert.Contains("-----BEGIN CERTIFICATE-----", issued.ChainPem, StringComparison.Ordinal);
        Assert.Empty(_acme.Violations);
    }

    [Fact]
    public async Task Too_many_bad_nonces_fail_cleanly()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var client = NewClient(key);
        _acme.BadNonceBudget = 10;
        var ex = await Assert.ThrowsAsync<AcmeException>(() => client.EnsureAccountAsync([], agreeToTerms: true, default));
        Assert.EndsWith(":badNonce", ex.Type, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_failed_validation_reports_the_reason_and_unpublishes_the_token()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var client = NewClient(key);
        _acme.FailValidation = true;
        await client.EnsureAccountAsync([], agreeToTerms: true, default);
        var ex = await Assert.ThrowsAsync<AcmeException>(() => client.OrderCertificateAsync(["chuvadi.in"], _store, default));
        Assert.Contains("invalid", ex.Message, StringComparison.Ordinal);
        Assert.Equal(0, _store.Count);
    }

    [Fact]
    public async Task Terms_must_be_agreed()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var ex = await Assert.ThrowsAsync<AcmeException>(() => NewClient(key).EnsureAccountAsync([], agreeToTerms: false, default));
        Assert.EndsWith(":userActionRequired", ex.Type, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_same_key_finds_the_same_account()
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var a = await NewClient(key).EnsureAccountAsync([], true, default);
        var b = await NewClient(key).EnsureAccountAsync([], true, default);
        Assert.Equal(a, b);
        Assert.Equal(1, _acme.Accounts);
    }

    [Fact]
    public async Task Only_published_tokens_are_answered()
    {
        using var http = new HttpClient { BaseAddress = _acme.ValidationBase };
        _store.Publish("abc", "abc.thumb");
        Assert.Equal("abc.thumb", await http.GetStringAsync("/.well-known/acme-challenge/abc"));
        Assert.Equal(System.Net.HttpStatusCode.NotFound, (await http.GetAsync("/.well-known/acme-challenge/nope")).StatusCode);
        Assert.Equal(System.Net.HttpStatusCode.NotFound, (await http.PostAsync("/.well-known/acme-challenge/abc", null)).StatusCode);
        _store.Remove("abc");
        Assert.Equal(System.Net.HttpStatusCode.NotFound, (await http.GetAsync("/.well-known/acme-challenge/abc")).StatusCode);
    }

    [Fact]
    public void Incomplete_acme_settings_stop_the_portal_at_start()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => Program.Build(
        [
            "--environment", "Testing",
            "--Portal:DataRoot", SpaceLayoutTests.NewTempDir(),
            "--Portal:Tls:Acme:Enabled", "true",
        ]));
        Assert.Contains("ACME needs", ex.Message, StringComparison.Ordinal);
    }
}
