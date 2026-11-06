using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.Logging.Abstractions;

namespace ChuvadiReader.Web.Tests;

public class CertificateSourceTests
{
    private sealed class ManualTime : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = DateTimeOffset.UtcNow;

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private static void WritePem(string certPath, string keyPath, string cn)
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var req = new CertificateRequest($"CN={cn}", key, HashAlgorithmName.SHA256);
        using var cert = req.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(30));
        File.WriteAllText(certPath, cert.ExportCertificatePem());
        File.WriteAllText(keyPath, key.ExportPkcs8PrivateKeyPem());
    }

    [Fact]
    public void Loads_a_pem_pair_and_picks_up_a_renewal_without_restart()
    {
        var dir = SpaceLayoutTests.NewTempDir();
        var certPath = Path.Combine(dir, "fullchain.pem");
        var keyPath = Path.Combine(dir, "privkey.pem");
        WritePem(certPath, keyPath, "first.example");
        var time = new ManualTime();
        using var source = new PemFileCertificateSource(
            new TlsOptions { CertificatePath = certPath, KeyPath = keyPath, ReloadCheck = TimeSpan.FromMinutes(5) },
            NullLogger<PemFileCertificateSource>.Instance, time);

        Assert.Equal("CN=first.example", source.Current.Subject);
        Assert.True(source.Current.HasPrivateKey);

        WritePem(certPath, keyPath, "second.example");
        File.SetLastWriteTimeUtc(certPath, DateTime.UtcNow.AddSeconds(5));
        File.SetLastWriteTimeUtc(keyPath, DateTime.UtcNow.AddSeconds(5));
        Assert.Equal("CN=first.example", source.Current.Subject); // not yet time to look
        time.Now += TimeSpan.FromMinutes(6);
        Assert.Equal("CN=second.example", source.Current.Subject);
    }

    [Fact]
    public void A_broken_renewal_keeps_the_working_certificate()
    {
        var dir = SpaceLayoutTests.NewTempDir();
        var certPath = Path.Combine(dir, "fullchain.pem");
        var keyPath = Path.Combine(dir, "privkey.pem");
        WritePem(certPath, keyPath, "good.example");
        var time = new ManualTime();
        using var source = new PemFileCertificateSource(
            new TlsOptions { CertificatePath = certPath, KeyPath = keyPath, ReloadCheck = TimeSpan.FromMinutes(1) },
            NullLogger<PemFileCertificateSource>.Instance, time);

        File.WriteAllText(certPath, "-----BEGIN CERTIFICATE-----\nnot base64\n-----END CERTIFICATE-----\n");
        File.SetLastWriteTimeUtc(certPath, DateTime.UtcNow.AddSeconds(5));
        time.Now += TimeSpan.FromMinutes(2);
        Assert.Equal("CN=good.example", source.Current.Subject);
    }

    [Fact]
    public void Missing_settings_fail_at_start()
        => Assert.Throws<InvalidOperationException>(() => new PemFileCertificateSource(new TlsOptions(), NullLogger<PemFileCertificateSource>.Instance, TimeProvider.System));
}
