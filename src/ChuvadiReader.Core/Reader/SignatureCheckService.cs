using System.Globalization;
using System.Security.Cryptography.X509Certificates;
using Chuvadi.Cryptography.PathValidation;
using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Signatures;
using Chuvadi.Pdf.Signatures.Verification;
using ChuvadiX509 = Chuvadi.Cryptography.X509.X509Certificate;

namespace ChuvadiReader.Core.Reader;

/// <summary>Plain-language outcome of checking one signature.</summary>
public enum SignatureCheckStatus
{
    /// <summary>Cryptographically intact, covers the whole file, and the signer's certificate
    /// chains to a trusted root.</summary>
    Valid,

    /// <summary>Intact and covers the whole file, but the signer's certificate could not be
    /// confirmed (not issued by a trusted root, expired, or no trust list available).</summary>
    UnknownTrust,

    /// <summary>The signature is intact for the revision it signed, but the file was changed
    /// afterwards (an incremental update after signing — a later signature, form fill or edit).</summary>
    ModifiedAfterSigning,

    /// <summary>The signature doesn't match the bytes it claims to cover, is malformed, or
    /// its certificate is revoked.</summary>
    Invalid,

    /// <summary>A signature kind the library can't verify (non-CMS sub-filter, unknown algorithm).</summary>
    Unsupported,

    /// <summary>D-198, until Pdf 3.35.1: no verdict is given. What the signature states (signer, time, reason,
    /// place, issuer) is shown; whether it is valid or trusted is not said, because the library's verdict can be
    /// wrong (SIG-12).</summary>
    NotChecked,
}

/// <summary>One signature as the Signatures card shows it.</summary>
public sealed record SignatureCheckInfo(
    string FieldName,
    string SignerName,
    DateTimeOffset? SigningTime,
    string? Reason,
    string? Location,
    string? ContactInfo,
    string SubFilter,
    bool IsDocumentTimestamp,
    bool CoversWholeDocument,
    bool IntegrityVerified,
    bool TrustValidated,
    bool TimestampValidated,
    string? IssuerName,
    DateTimeOffset? CertificateValidTo,
    SignatureCheckStatus Status,
    string LibraryStatus,
    string Detail,
    string Summary);

/// <summary>All signatures in a file. <see cref="Error"/> is set when the file couldn't be read.</summary>
public sealed record SignatureCheckReport(IReadOnlyList<SignatureCheckInfo> Signatures, string? Error = null)
{
    /// <summary>False when the signer's certificate was not checked against trusted roots
    /// (<see cref="SignatureCheckOptions.CheckTrust"/> off, D-198): no signature can be "Valid" then.</summary>
    public bool TrustChecked { get; init; } = true;

    public bool HasSignatures => Signatures.Count > 0;

    /// <summary>True when every signature is <see cref="SignatureCheckStatus.Valid"/>.</summary>
    public bool AllValid => HasSignatures && Signatures.All(s => s.Status == SignatureCheckStatus.Valid);

    /// <summary>Short status-bar text, e.g. "1 signature valid" or "2 signatures · 1 needs attention".</summary>
    public string Headline
    {
        get
        {
            if (Error is not null)
            {
                return "Signatures couldn't be checked";
            }

            int n = Signatures.Count;
            if (n == 0)
            {
                return "Not signed";
            }

            int ok = Signatures.Count(s => s.Status == SignatureCheckStatus.Valid);
            string noun = n == 1 ? "signature" : "signatures";
            if (!TrustChecked)
            {
                return $"{n} {noun} · not checked in this version";
            }

            return ok == n ? $"{n} {noun} valid" : $"{n} {noun} · {n - ok} need{(n - ok == 1 ? "s" : "")} attention";
        }
    }
}

/// <summary>Options for <see cref="SignatureCheckService.CheckAsync"/>.</summary>
public sealed class SignatureCheckOptions
{
    /// <summary>Trust the operating system's root certificate store (Windows "Trusted Root
    /// Certification Authorities"). Default true.</summary>
    public bool UseSystemTrustStore { get; init; } = true;

    /// <summary>Extra trusted root/issuer certificates (DER), e.g. an organisation's own CA.</summary>
    public IReadOnlyList<byte[]>? TrustedCertificates { get; init; }

    /// <summary>Whether a verdict is given at all (valid, changed, not valid, trusted). <b>Off by default until the
    /// Reader is on Pdf 3.35.1 (D-198, library advisory D-405/D-406):</b> on 3.32.0 a signature can be reported
    /// valid while the page shows what an attacker added (SIG-12), so the check shows only what the signature
    /// states and every signature is <see cref="SignatureCheckStatus.NotChecked"/>. No trust store is built.
    /// Tests turn it on to keep the verdict code proven for when it returns.</summary>
    public bool CheckTrust { get; init; }
}

/// <summary>
/// Lists and verifies a PDF's digital signatures with chuvadi-pdf's
/// <see cref="SignatureReader"/> and <see cref="PdfSignatureVerifier"/>, and turns the result
/// into a plain-language line ("Signed by A. Shiva · 1 Nov 2026 · document unchanged since
/// signing"). Read-only: the file is never changed.
/// </summary>
public sealed class SignatureCheckService
{
    private static readonly Lazy<IReadOnlyList<ChuvadiX509>> SystemRoots = new(LoadSystemRoots);

    public Task<SignatureCheckReport> CheckAsync(
        string pdfPath,
        string? password = null,
        SignatureCheckOptions? options = null,
        CancellationToken ct = default)
        => Task.Run(() => Check(pdfPath, password, options, ct), ct);

    /// <summary>Synchronous core of <see cref="CheckAsync"/>.</summary>
    public SignatureCheckReport Check(string pdfPath, string? password = null, SignatureCheckOptions? options = null, CancellationToken ct = default)
    {
        options ??= new SignatureCheckOptions();
        try
        {
            long fileLength = new FileInfo(pdfPath).Length;
            using var doc = string.IsNullOrEmpty(password) ? PdfDocument.Open(pdfPath) : PdfDocument.Open(pdfPath, password);
            var signatures = SignatureReader.Read(doc.Catalog, doc.Objects);
            if (signatures.Count == 0)
            {
                return new SignatureCheckReport(Array.Empty<SignatureCheckInfo>());
            }

            var verifyOptions = new SignatureVerifyOptions { TrustStore = options.CheckTrust ? BuildTrustStore(options) : null };
            var list = new List<SignatureCheckInfo>(signatures.Count);
            foreach (var sig in signatures)
            {
                ct.ThrowIfCancellationRequested();
                list.Add(Describe(sig, doc, pdfPath, fileLength, verifyOptions, options.CheckTrust));
            }

            return new SignatureCheckReport(list) { TrustChecked = options.CheckTrust };
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            return new SignatureCheckReport(Array.Empty<SignatureCheckInfo>(), ex.Message);
        }
    }

    private static SignatureCheckInfo Describe(PdfSignature sig, PdfDocument doc, string path, long fileLength, SignatureVerifyOptions verifyOptions, bool trustChecked)
    {
        bool covers = CoversWholeFile(sig.ByteRange, path, fileLength);

        SignatureVerificationResult? result = null;
        string? verifyError = null;
        try
        {
            result = sig.Verify(doc, verifyOptions);
        }
        catch (Exception ex)
        {
            verifyError = ex.Message;
        }

        DateTimeOffset? cmsTime = null;
        if (sig.IsCmsBased)
        {
            try
            {
                cmsTime = sig.DecodeCms().SignerInfos.FirstOrDefault()?.SigningTime;
            }
            catch
            {
                // Malformed CMS: the verifier reports it; the dictionary time is the fallback.
            }
        }

        var cert = result?.SignerCertificate;
        string signer = FirstNonBlank(cert?.Subject?.CommonName, sig.Name, cert?.Subject?.ToString(), sig.FieldName) ?? "Unknown signer";
        DateTimeOffset? when = result is { TimestampValidated: true, SignatureTimestamp: { } ts } ? ts : cmsTime ?? sig.SigningTimeFromDictionary;

        var (status, detail) = Classify(sig, result, verifyError, covers, trustChecked);
        string libStatus = result?.Status.ToString() ?? (verifyError is null ? "Unknown" : "Error");

        return new SignatureCheckInfo(
            sig.FieldName ?? string.Empty,
            signer,
            when,
            NullIfBlank(sig.Reason),
            NullIfBlank(sig.Location),
            NullIfBlank(sig.ContactInfo),
            sig.SubFilter ?? string.Empty,
            sig.IsDocumentTimestamp,
            covers,
            result?.IntegrityVerified ?? false,
            result?.TrustValidated ?? false,
            result?.TimestampValidated ?? false,
            FirstNonBlank(cert?.Issuer?.CommonName, cert?.Issuer?.ToString()),
            cert?.Validity?.NotAfter,
            status,
            libStatus,
            detail,
            Summarise(sig.IsDocumentTimestamp, signer, when, status, trustChecked));
    }

    private static (SignatureCheckStatus Status, string Detail) Classify(
        PdfSignature sig, SignatureVerificationResult? r, string? verifyError, bool covers, bool trustChecked)
    {
        if (!sig.IsCmsBased)
        {
            return (SignatureCheckStatus.Unsupported, $"This signature type ({sig.SubFilter}) can't be checked.");
        }

        if (!trustChecked)
        {
            // D-198: no verdict until Pdf 3.35.1, whatever the library says; what the signature states is shown.
            return (SignatureCheckStatus.NotChecked,
                "Shown here is what the signature states. Whether it is valid, and whether the file changed after it, is not checked in this version: checking comes back with the next update.");
        }

        if (r is null)
        {
            return (SignatureCheckStatus.Invalid, "The signature couldn't be read: " + (verifyError ?? "unknown error"));
        }

        switch (r.Status)
        {
            case SignatureVerificationStatus.UnsupportedSubFilter:
            case SignatureVerificationStatus.UnsupportedAlgorithm:
                return (SignatureCheckStatus.Unsupported, r.Message);
            case SignatureVerificationStatus.Invalid:
            case SignatureVerificationStatus.DigestMismatch:
                return (SignatureCheckStatus.Invalid, "The signed content no longer matches the signature — the document was altered.");
            case SignatureVerificationStatus.MalformedSignature:
            case SignatureVerificationStatus.SignerCertificateNotFound:
                return (SignatureCheckStatus.Invalid, r.Message);
            case SignatureVerificationStatus.TrustChainCertificateRevoked:
                return (SignatureCheckStatus.Invalid, "The signer's certificate has been revoked.");
        }

        if (!r.IntegrityVerified)
        {
            return (SignatureCheckStatus.Invalid, r.Message);
        }

        if (!covers)
        {
            return (SignatureCheckStatus.ModifiedAfterSigning,
                "The signature is intact, but the file was changed after it was signed (a later revision was added).");
        }

        if (r.TrustValidated)
        {
            return (SignatureCheckStatus.Valid, "The certificate is trusted and the document is unchanged since signing.");
        }

        string why = r.Status switch
        {
            SignatureVerificationStatus.TrustChainCertificateOutOfValidity => "The signer's certificate was expired or not yet valid at signing time.",
            SignatureVerificationStatus.TrustChainBroken => "The signer's certificate isn't issued by a certificate authority this device trusts.",
            SignatureVerificationStatus.TrustChainInvalid => "The signer's certificate chain didn't validate.",
            _ => "The signer's certificate couldn't be checked against a trusted authority.",
        };
        return (SignatureCheckStatus.UnknownTrust, why + " The document is unchanged since signing.");
    }

    private static string Summarise(bool isTimestamp, string signer, DateTimeOffset? when, SignatureCheckStatus status, bool trustChecked)
    {
        string head = isTimestamp ? $"Timestamped by {signer}" : $"Signed by {signer}";
        string date = when is { } w ? " · " + w.ToLocalTime().ToString("d MMM yyyy", CultureInfo.InvariantCulture) : string.Empty;
        return status switch
        {
            SignatureCheckStatus.Valid => $"{head}{date} · certificate valid · document unchanged since signing",
            SignatureCheckStatus.NotChecked => $"{head}{date} · not checked in this version",
            SignatureCheckStatus.UnknownTrust => $"{head}{date} · document unchanged since signing · certificate not verified",
            SignatureCheckStatus.ModifiedAfterSigning => $"{head}{date} · document changed after signing",
            SignatureCheckStatus.Invalid => $"{head}{date} · signature is not valid",
            _ => $"{head}{date} · signature can't be checked",
        };
    }

    /// <summary>True when the signed byte range runs to the end of the file (only trailing
    /// whitespace after it is tolerated), i.e. nothing was appended after signing.</summary>
    internal static bool CoversWholeFile(ByteRange range, string path, long fileLength)
    {
        long end = range.SecondOffset + range.SecondLength;
        if (range.FirstOffset != 0 || end > fileLength)
        {
            return false;
        }

        if (end == fileLength)
        {
            return true;
        }

        long tail = fileLength - end;
        if (tail > 64)
        {
            return false;
        }

        try
        {
            using var fs = File.OpenRead(path);
            fs.Seek(end, SeekOrigin.Begin);
            var buf = new byte[tail];
            fs.ReadExactly(buf);
            return buf.All(b => b is (byte)' ' or (byte)'\r' or (byte)'\n' or (byte)'\t' or 0);
        }
        catch
        {
            return false;
        }
    }

    private static TrustStore? BuildTrustStore(SignatureCheckOptions options)
    {
        var store = new TrustStore();
        int added = 0;
        if (options.UseSystemTrustStore)
        {
            foreach (var c in SystemRoots.Value)
            {
                store.Add(c);
                added++;
            }
        }

        foreach (var der in options.TrustedCertificates ?? Array.Empty<byte[]>())
        {
            try
            {
                store.Add(ChuvadiX509.Decode(der));
                added++;
            }
            catch
            {
                // Skip anything that isn't a decodable certificate.
            }
        }

        // With no anchors at all, let the verifier skip trust (reported as "not verified").
        return added == 0 ? null : store;
    }

    private static IReadOnlyList<ChuvadiX509> LoadSystemRoots()
    {
        var list = new List<ChuvadiX509>();
        foreach (var location in new[] { StoreLocation.CurrentUser, StoreLocation.LocalMachine })
        {
            try
            {
                using var x = new X509Store(StoreName.Root, location);
                x.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
                foreach (var c in x.Certificates)
                {
                    try
                    {
                        list.Add(ChuvadiX509.Decode(c.RawData));
                    }
                    catch
                    {
                        // A root the library can't parse simply isn't used as an anchor.
                    }
                    finally
                    {
                        c.Dispose();
                    }
                }
            }
            catch
            {
                // No store on this platform/location.
            }
        }

        return list;
    }

    private static string? FirstNonBlank(params string?[] values) =>
        values.FirstOrDefault(v => !string.IsNullOrWhiteSpace(v))?.Trim();

    private static string? NullIfBlank(string? s) => string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
