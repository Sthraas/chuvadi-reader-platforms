using System.Security.Cryptography.X509Certificates;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Where Kestrel's TLS certificate comes from. Pluggable so the source can change without touching
/// the server: today a PEM pair on disk (whatever process renews it — Pezhai is being asked, D-pending);
/// a Pezhai-backed source can be added later behind the same interface.
/// </summary>
public interface ICertificateSource
{
    /// <summary>The current certificate with its private key. Called on every TLS handshake, so it
    /// must be cheap; implementations cache and reload when the certificate changes.</summary>
    X509Certificate2 Current { get; }
}

/// <summary>Settings for <see cref="PemFileCertificateSource"/> (section <c>Portal:Tls</c>).</summary>
public sealed class TlsOptions
{
    public const string Section = "Portal:Tls";

    /// <summary>Certificate chain, PEM (leaf first).</summary>
    public string CertificatePath { get; set; } = string.Empty;

    /// <summary>Private key, PEM (PKCS#8, RSA or EC). Readable only by the service account.</summary>
    public string KeyPath { get; set; } = string.Empty;

    /// <summary>How often to look for a renewed certificate on disk.</summary>
    public TimeSpan ReloadCheck { get; set; } = TimeSpan.FromMinutes(5);
}

/// <summary>
/// Loads a PEM certificate and key, and reloads them when either file changes (checked at most every
/// <see cref="TlsOptions.ReloadCheck"/>), so a renewal needs no restart. A broken renewal keeps the
/// previous certificate and logs an error.
/// </summary>
public sealed class PemFileCertificateSource : ICertificateSource, IDisposable
{
    private readonly TlsOptions _options;
    private readonly ILogger<PemFileCertificateSource> _log;
    private readonly TimeProvider _time;
    private readonly object _lock = new();
    private X509Certificate2 _current;
    private DateTime _certStamp;
    private DateTime _keyStamp;
    private DateTimeOffset _nextCheck;

    public PemFileCertificateSource(TlsOptions options, ILogger<PemFileCertificateSource> log, TimeProvider time)
    {
        _options = options;
        _log = log;
        _time = time;
        _current = Load(out _certStamp, out _keyStamp);
        _nextCheck = _time.GetUtcNow() + _options.ReloadCheck;
    }

    public X509Certificate2 Current
    {
        get
        {
            var now = _time.GetUtcNow();
            if (now < _nextCheck)
            {
                return _current;
            }

            lock (_lock)
            {
                if (now >= _nextCheck)
                {
                    _nextCheck = now + _options.ReloadCheck;
                    TryReload();
                }

                return _current;
            }
        }
    }

    private void TryReload()
    {
        try
        {
            var c = File.GetLastWriteTimeUtc(_options.CertificatePath);
            var k = File.GetLastWriteTimeUtc(_options.KeyPath);
            if (c == _certStamp && k == _keyStamp)
            {
                return;
            }

            var next = Load(out var cs, out var ks);
            var old = _current;
            _current = next;
            _certStamp = cs;
            _keyStamp = ks;
            _log.LogInformation("TLS certificate reloaded: {Subject}, valid until {NotAfter:u}", next.Subject, next.NotAfter.ToUniversalTime());
            // The old certificate may still be referenced by handshakes in flight; let the GC have it.
            GC.KeepAlive(old);
        }
        catch (Exception ex) when (ex is IOException or System.Security.Cryptography.CryptographicException or UnauthorizedAccessException or ArgumentException)
        {
            _log.LogError("Could not reload the TLS certificate; keeping the current one: {Message}", ex.Message);
        }
    }

    private X509Certificate2 Load(out DateTime certStamp, out DateTime keyStamp)
    {
        if (string.IsNullOrWhiteSpace(_options.CertificatePath) || string.IsNullOrWhiteSpace(_options.KeyPath))
        {
            throw new InvalidOperationException("Portal:Tls:CertificatePath and Portal:Tls:KeyPath must be set.");
        }

        certStamp = File.GetLastWriteTimeUtc(_options.CertificatePath);
        keyStamp = File.GetLastWriteTimeUtc(_options.KeyPath);
        using var pem = X509Certificate2.CreateFromPemFile(_options.CertificatePath, _options.KeyPath);
        // Re-import so the private key is usable by SslStream on every platform (ephemeral PEM keys aren't on Windows).
        var cert = X509CertificateLoader.LoadPkcs12(pem.Export(X509ContentType.Pkcs12), password: null);
        if (cert.NotAfter.ToUniversalTime() < _time.GetUtcNow().UtcDateTime)
        {
            _log.LogError("The TLS certificate expired on {NotAfter:u}", cert.NotAfter.ToUniversalTime());
        }

        return cert;
    }

    public void Dispose() => _current.Dispose();
}
