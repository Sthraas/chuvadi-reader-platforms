using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting.Acme;

/// <summary>Settings for Let's Encrypt certificates (section <c>Portal:Tls:Acme</c>).</summary>
public sealed class AcmeOptions
{
    public const string Section = "Portal:Tls:Acme";
    public const string LetsEncryptProduction = "https://acme-v02.api.letsencrypt.org/directory";
    public const string LetsEncryptStaging = "https://acme-staging-v02.api.letsencrypt.org/directory";

    /// <summary>Turns ACME on. Off: the PEM files in <see cref="TlsOptions"/> are served as they are.</summary>
    public bool Enabled { get; set; }

    /// <summary>ACME directory. Default Let's Encrypt staging, so a misconfigured first run can't hit production rate limits.</summary>
    public string DirectoryUrl { get; set; } = LetsEncryptStaging;

    /// <summary>Names on the certificate, e.g. <c>chuvadi.in</c>. Config, never code.</summary>
    public List<string> Domains { get; set; } = new();

    /// <summary>Where Let's Encrypt sends expiry and policy mail.</summary>
    public List<string> ContactEmails { get; set; } = new();

    /// <summary>Arun's explicit agreement to the ACME server's terms of service. Required.</summary>
    public bool AgreeToTermsOfService { get; set; }

    /// <summary>Folder for the account key (PEM, owner-only). Losing it only means a new account.</summary>
    public string AccountFolder { get; set; } = string.Empty;

    /// <summary>Renew when fewer days than this remain, capped at a third of the certificate's lifetime
    /// (90-day certificates: 30 days; 45-day: 15 days).</summary>
    public int RenewBeforeDays { get; set; } = 30;

    /// <summary>How often to check.</summary>
    public TimeSpan CheckInterval { get; set; } = TimeSpan.FromHours(12);

    /// <summary>After a failed attempt, wait this long before the next one (doubling, up to <see cref="CheckInterval"/>).</summary>
    public TimeSpan RetryAfterFailure { get; set; } = TimeSpan.FromMinutes(10);
}

/// <summary>
/// The certificate Kestrel serves when ACME is on. At start it loads the last issued certificate from
/// the PEM files (so a restart needs no new order); while none exists yet it serves a short-lived
/// self-signed one, so HTTPS comes up and the first order can run. A new certificate is swapped in
/// at once (hot reload) and written to the PEM files for the next start.
/// </summary>
public sealed class AcmeCertificateManager : ICertificateSource, IDisposable
{
    private readonly TlsOptions _tls;
    private readonly AcmeOptions _acme;
    private readonly TimeProvider _time;
    private readonly ILogger<AcmeCertificateManager> _log;
    private X509Certificate2 _current;

    public AcmeCertificateManager(TlsOptions tls, AcmeOptions acme, TimeProvider time, ILogger<AcmeCertificateManager> log)
    {
        _tls = tls;
        _acme = acme;
        _time = time;
        _log = log;
        _current = TryLoad() ?? TemporarySelfSigned();
    }

    public X509Certificate2 Current => Volatile.Read(ref _current);

    /// <summary>True while the temporary self-signed certificate is served.</summary>
    public bool IsTemporary { get; private set; }

    /// <summary>True when there is no real certificate, or it covers other names, or it expires within the renewal window.</summary>
    public bool NeedsRenewal()
    {
        var c = Current;
        if (IsTemporary)
        {
            return true;
        }

        var names = DnsNames(c);
        if (!_acme.Domains.All(d => names.Contains(d, StringComparer.OrdinalIgnoreCase)))
        {
            return true;
        }

        return c.NotAfter.ToUniversalTime() - _time.GetUtcNow().UtcDateTime < RenewalWindow(c);
    }

    /// <summary>Renew when less than this remains: <see cref="AcmeOptions.RenewBeforeDays"/>, but never more than a
    /// third of the certificate's lifetime (Let's Encrypt's advice), so shorter certificates (45-day, 6-day) are
    /// renewed at two thirds of their life instead of continuously.</summary>
    public TimeSpan RenewalWindow(X509Certificate2 cert)
    {
        var lifetime = cert.NotAfter.ToUniversalTime() - cert.NotBefore.ToUniversalTime();
        var configured = TimeSpan.FromDays(_acme.RenewBeforeDays);
        var third = TimeSpan.FromTicks(lifetime.Ticks / 3);
        return configured < third ? configured : third;
    }

    /// <summary>Swaps in a newly issued certificate and stores it for restarts (atomic file replace).</summary>
    public void Install(IssuedCertificate issued)
    {
        var cert = Load(issued.ChainPem, issued.PrivateKeyPem);
        WriteAtomically(_tls.KeyPath, issued.PrivateKeyPem);
        WriteAtomically(_tls.CertificatePath, issued.ChainPem);
        var old = Interlocked.Exchange(ref _current, cert);
        IsTemporary = false;
        _log.LogInformation("TLS certificate installed: {Subject}, valid until {NotAfter:u}", cert.Subject, cert.NotAfter.ToUniversalTime());
        // Handshakes in flight may still hold the old certificate; it is not disposed here.
        GC.KeepAlive(old);
    }

    private X509Certificate2? TryLoad()
    {
        try
        {
            if (File.Exists(_tls.CertificatePath) && File.Exists(_tls.KeyPath))
            {
                var c = Load(File.ReadAllText(_tls.CertificatePath), File.ReadAllText(_tls.KeyPath));
                _log.LogInformation("TLS certificate loaded: {Subject}, valid until {NotAfter:u}", c.Subject, c.NotAfter.ToUniversalTime());
                return c;
            }
        }
        catch (Exception ex) when (ex is CryptographicException or IOException or UnauthorizedAccessException or ArgumentException)
        {
            _log.LogError("The stored TLS certificate can't be used; a new one will be ordered: {Message}", ex.Message);
        }

        return null;
    }

    private X509Certificate2 TemporarySelfSigned()
    {
        IsTemporary = true;
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var name = _acme.Domains.FirstOrDefault() ?? "localhost";
        var req = new CertificateRequest("CN=" + name, key, HashAlgorithmName.SHA256);
        var san = new SubjectAlternativeNameBuilder();
        foreach (var d in _acme.Domains.DefaultIfEmpty("localhost"))
        {
            san.AddDnsName(d);
        }

        req.CertificateExtensions.Add(san.Build());
        var now = _time.GetUtcNow();
        using var cert = req.CreateSelfSigned(now.AddMinutes(-5), now.AddDays(2));
        _log.LogWarning("No TLS certificate yet; serving a temporary self-signed one until the first ACME order completes");
        return X509CertificateLoader.LoadPkcs12(cert.Export(X509ContentType.Pkcs12), password: null);
    }

    internal static X509Certificate2 Load(string chainPem, string keyPem)
    {
        using var pem = X509Certificate2.CreateFromPem(chainPem, keyPem);
        return X509CertificateLoader.LoadPkcs12(pem.Export(X509ContentType.Pkcs12), password: null);
    }

    internal static IReadOnlyList<string> DnsNames(X509Certificate2 cert)
    {
        foreach (var ext in cert.Extensions)
        {
            if (ext is X509SubjectAlternativeNameExtension san)
            {
                return san.EnumerateDnsNames().ToList();
            }
        }

        return Array.Empty<string>();
    }

    internal static void WriteAtomically(string path, string content)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(path))!;
        Directory.CreateDirectory(dir);
        var temp = Path.Combine(dir, "." + Path.GetFileName(path) + "." + Guid.NewGuid().ToString("N") + ".tmp");
        var options = new FileStreamOptions { Mode = FileMode.CreateNew, Access = FileAccess.Write };
        if (!OperatingSystem.IsWindows())
        {
            options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
        }

        using (var w = new StreamWriter(new FileStream(temp, options)))
        {
            w.Write(content);
        }

        File.Move(temp, path, overwrite: true);
    }

    public void Dispose() => _current.Dispose();
}

/// <summary>
/// Orders the first certificate and renews it before expiry, in the background. A failure keeps the
/// current certificate, logs an error, and retries with backoff.
/// </summary>
public sealed class AcmeRenewalService : BackgroundService
{
    private readonly AcmeCertificateManager _manager;
    private readonly Http01ChallengeStore _challenges;
    private readonly AcmeOptions _options;
    private readonly IHttpClientFactoryLite _httpFactory;
    private readonly TimeProvider _time;
    private readonly ILogger<AcmeRenewalService> _log;

    public AcmeRenewalService(AcmeCertificateManager manager, Http01ChallengeStore challenges, IOptions<AcmeOptions> options,
        IHttpClientFactoryLite httpFactory, TimeProvider time, ILogger<AcmeRenewalService> log)
    {
        _manager = manager;
        _challenges = challenges;
        _options = options.Value;
        _httpFactory = httpFactory;
        _time = time;
        _log = log;
    }

    /// <summary>Successful orders so far (tests and monitoring).</summary>
    public int Renewals { get; private set; }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var backoff = _options.RetryAfterFailure;
        while (!stoppingToken.IsCancellationRequested)
        {
            TimeSpan wait = _options.CheckInterval;
            try
            {
                if (_manager.NeedsRenewal())
                {
                    await RenewOnceAsync(stoppingToken).ConfigureAwait(false);
                }

                backoff = _options.RetryAfterFailure;
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                return;
            }
            catch (Exception ex) when (ex is AcmeException or HttpRequestException or CryptographicException or IOException or TaskCanceledException)
            {
                _log.LogError("Certificate order failed; keeping the current certificate, next try in {Wait}: {Message}", backoff, ex.Message);
                wait = backoff;
                backoff = TimeSpan.FromTicks(Math.Min(backoff.Ticks * 2, _options.CheckInterval.Ticks));
            }

            try
            {
                await Task.Delay(wait, _time, stoppingToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    /// <summary>One full order (account, challenges, finalize, install). Public for tests.</summary>
    public async Task RenewOnceAsync(CancellationToken ct)
    {
        if (!_options.AgreeToTermsOfService)
        {
            throw new AcmeException("Portal:Tls:Acme:AgreeToTermsOfService must be true to order a certificate.");
        }

        using var accountKey = AcmeAccountKey.LoadOrCreate(_options.AccountFolder);
        var client = new AcmeClient(_httpFactory.Create(), new Uri(_options.DirectoryUrl), accountKey, _time, _log);
        await client.EnsureAccountAsync(_options.ContactEmails, agreeToTerms: true, ct).ConfigureAwait(false);
        var issued = await client.OrderCertificateAsync(_options.Domains, _challenges, ct).ConfigureAwait(false);
        _manager.Install(issued);
        Renewals++;
    }
}

/// <summary>The ACME account key on disk: <c>account.key.pem</c>, PKCS#8, owner-only.</summary>
public static class AcmeAccountKey
{
    public static ECDsa LoadOrCreate(string folder)
    {
        if (string.IsNullOrWhiteSpace(folder))
        {
            throw new InvalidOperationException("Portal:Tls:Acme:AccountFolder is required.");
        }

        var path = Path.Combine(folder, "account.key.pem");
        var key = ECDsa.Create();
        if (File.Exists(path))
        {
            key.ImportFromPem(File.ReadAllText(path));
            return key;
        }

        key.GenerateKey(ECCurve.NamedCurves.nistP256);
        AcmeCertificateManager.WriteAtomically(path, key.ExportPkcs8PrivateKeyPem());
        return key;
    }
}

/// <summary>Makes the HttpClient the ACME client uses, so tests can point it at their own ACME server.
/// One pooled SocketsHttpHandler is plenty for a few calls a day.</summary>
public interface IHttpClientFactoryLite
{
    HttpClient Create();
}

public sealed class DefaultHttpClientFactoryLite : IHttpClientFactoryLite, IDisposable
{
    private readonly SocketsHttpHandler _handler = new() { PooledConnectionLifetime = TimeSpan.FromMinutes(10) };

    public HttpClient Create() => new(_handler, disposeHandler: false)
    {
        Timeout = TimeSpan.FromSeconds(60),
        DefaultRequestHeaders = { { "User-Agent", "Chuvadi-Portal-ACME/1.0" } },
    };

    public void Dispose() => _handler.Dispose();
}
