using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json.Nodes;

namespace ChuvadiReader.Web.Hosting.Acme;

/// <summary>An ACME server's problem document (RFC 8555 §6.7, RFC 7807).</summary>
public sealed class AcmeException : Exception
{
    public AcmeException(string type, string detail, HttpStatusCode status)
        : base($"{detail} ({type}, HTTP {(int)status})")
    {
        Type = type;
        Detail = detail;
        Status = status;
    }

    public AcmeException(string message)
        : base(message)
    {
        Type = string.Empty;
        Detail = message;
    }

    public string Type { get; }
    public string Detail { get; }
    public HttpStatusCode Status { get; }
}

/// <summary>A certificate the ACME server issued: the PEM chain and the private key it was issued for.</summary>
public sealed record IssuedCertificate(string ChainPem, string PrivateKeyPem);

/// <summary>
/// A small ACME v2 client (RFC 8555) for Let's Encrypt, written for the portal: one account key
/// (ECDSA P-256, ES256), http-01 challenges, an ECDSA P-256 certificate key. Our own code on
/// <see cref="HttpClient"/> and BCL cryptography.
/// </summary>
public sealed class AcmeClient
{
    private const string JoseJson = "application/jose+json";
    private const int MaxNonceRetries = 3;

    private readonly HttpClient _http;
    private readonly Uri _directoryUrl;
    private readonly ECDsa _accountKey;
    private readonly TimeProvider _time;
    private readonly ILogger _log;
    private JsonObject? _directory;
    private string? _nonce;
    private string? _accountUrl;

    public AcmeClient(HttpClient http, Uri directoryUrl, ECDsa accountKey, TimeProvider time, ILogger log)
    {
        _http = http;
        _directoryUrl = directoryUrl;
        _accountKey = accountKey;
        _time = time;
        _log = log;
    }

    /// <summary>Longest wait for one authorization or order to change state.</summary>
    public TimeSpan PollLimit { get; init; } = TimeSpan.FromMinutes(3);

    /// <summary>Wait between polls when the server sends no Retry-After.</summary>
    public TimeSpan PollInterval { get; init; } = TimeSpan.FromSeconds(2);

    public string? AccountUrl => _accountUrl;

    /// <summary>The server's terms of service, when it publishes them.</summary>
    public async Task<string?> TermsOfServiceAsync(CancellationToken ct)
        => (string?)(await DirectoryAsync(ct).ConfigureAwait(false))["meta"]?["termsOfService"];

    /// <summary>Finds or creates the account for the key (RFC 8555 §7.3). Agreeing to the terms is the caller's decision.</summary>
    public async Task<string> EnsureAccountAsync(IReadOnlyList<string> contactEmails, bool agreeToTerms, CancellationToken ct)
    {
        if (_accountUrl is not null)
        {
            return _accountUrl;
        }

        var payload = new JsonObject { ["termsOfServiceAgreed"] = agreeToTerms };
        if (contactEmails.Count > 0)
        {
            payload["contact"] = new JsonArray(contactEmails.Select(e => (JsonNode)("mailto:" + e)).ToArray());
        }

        using var r = await PostAsync(await EndpointAsync("newAccount", ct).ConfigureAwait(false), payload, useJwk: true, ct).ConfigureAwait(false);
        _accountUrl = r.Headers.Location?.ToString() ?? throw new AcmeException("The ACME server didn't return the account URL.");
        var status = (string?)(await ReadJsonAsync(r, ct).ConfigureAwait(false))["status"];
        if (status is not "valid")
        {
            throw new AcmeException($"The ACME account is {status}.");
        }

        return _accountUrl;
    }

    /// <summary>
    /// Orders a certificate for <paramref name="domains"/>, answering http-01 challenges through
    /// <paramref name="challenges"/>, and returns the chain with its new private key.
    /// </summary>
    public async Task<IssuedCertificate> OrderCertificateAsync(IReadOnlyList<string> domains, Http01ChallengeStore challenges, CancellationToken ct)
    {
        if (domains.Count == 0)
        {
            throw new ArgumentException("At least one domain is needed.", nameof(domains));
        }

        if (_accountUrl is null)
        {
            throw new InvalidOperationException("Call EnsureAccountAsync first.");
        }

        // 1. New order.
        var orderPayload = new JsonObject
        {
            ["identifiers"] = new JsonArray(domains.Select(d => (JsonNode)new JsonObject { ["type"] = "dns", ["value"] = d }).ToArray()),
        };
        string orderUrl;
        JsonObject order;
        using (var r = await PostAsync(await EndpointAsync("newOrder", ct).ConfigureAwait(false), orderPayload, useJwk: false, ct).ConfigureAwait(false))
        {
            orderUrl = r.Headers.Location?.ToString() ?? throw new AcmeException("The ACME server didn't return the order URL.");
            order = await ReadJsonAsync(r, ct).ConfigureAwait(false);
        }

        // 2. Authorizations: answer each pending http-01 challenge.
        var published = new List<string>();
        try
        {
            foreach (var authzUrl in order["authorizations"]!.AsArray().Select(a => (string)a!))
            {
                var authz = await PostAsGetJsonAsync(authzUrl, ct).ConfigureAwait(false);
                var status = (string?)authz["status"];
                if (status == "valid")
                {
                    continue;
                }

                if (status != "pending")
                {
                    throw new AcmeException($"Authorization for {authz["identifier"]?["value"]} is {status}.");
                }

                var challenge = authz["challenges"]!.AsArray().Select(c => c!.AsObject()).FirstOrDefault(c => (string?)c["type"] == "http-01")
                    ?? throw new AcmeException($"The ACME server offered no http-01 challenge for {authz["identifier"]?["value"]}.");
                var token = (string)challenge["token"]!;
                if (token.Length == 0 || token.Any(ch => !(char.IsAsciiLetterOrDigit(ch) || ch is '-' or '_')))
                {
                    throw new AcmeException("The ACME server sent an invalid challenge token.");
                }

                challenges.Publish(token, AcmeJws.KeyAuthorization(token, _accountKey));
                published.Add(token);

                using (await PostAsync((string)challenge["url"]!, new JsonObject(), useJwk: false, ct).ConfigureAwait(false))
                {
                }

                await PollAsync(authzUrl, s => s == "valid", s => s is "invalid" or "deactivated" or "expired" or "revoked", "authorization", ct).ConfigureAwait(false);
            }

            // 3. Wait for the order to be ready, then finalize with a CSR for a fresh key.
            order = await PollAsync(orderUrl, s => s is "ready" or "valid", s => s == "invalid", "order", ct).ConfigureAwait(false);
            using var certKey = ECDsa.Create(ECCurve.NamedCurves.nistP256);
            if ((string?)order["status"] == "ready")
            {
                var csr = CreateCsr(domains, certKey);
                using (await PostAsync((string)order["finalize"]!, new JsonObject { ["csr"] = AcmeJws.Base64Url(csr) }, useJwk: false, ct).ConfigureAwait(false))
                {
                }

                order = await PollAsync(orderUrl, s => s == "valid", s => s == "invalid", "order", ct).ConfigureAwait(false);
            }
            else
            {
                throw new AcmeException("The order was already finalized with another key.");
            }

            // 4. Download the chain.
            var certUrl = (string?)order["certificate"] ?? throw new AcmeException("The valid order has no certificate URL.");
            using var cr = await PostAsync(certUrl, null, useJwk: false, ct, accept: "application/pem-certificate-chain").ConfigureAwait(false);
            var chain = await cr.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            if (!chain.Contains("-----BEGIN CERTIFICATE-----", StringComparison.Ordinal))
            {
                throw new AcmeException("The ACME server returned no PEM certificate.");
            }

            return new IssuedCertificate(chain, certKey.ExportPkcs8PrivateKeyPem());
        }
        finally
        {
            foreach (var token in published)
            {
                challenges.Remove(token);
            }
        }
    }

    internal static byte[] CreateCsr(IReadOnlyList<string> domains, ECDsa key)
    {
        var req = new CertificateRequest(new X500DistinguishedName("CN=" + domains[0]), key, HashAlgorithmName.SHA256);
        var san = new SubjectAlternativeNameBuilder();
        foreach (var d in domains)
        {
            san.AddDnsName(d);
        }

        req.CertificateExtensions.Add(san.Build());
        return req.CreateSigningRequest();
    }

    // ── protocol plumbing ─────────────────────────────────────────────────────────────

    private async Task<JsonObject> PollAsync(string url, Func<string?, bool> done, Func<string?, bool> failed, string what, CancellationToken ct)
    {
        var deadline = _time.GetUtcNow() + PollLimit;
        while (true)
        {
            using var r = await PostAsync(url, null, useJwk: false, ct).ConfigureAwait(false);
            var body = await ReadJsonAsync(r, ct).ConfigureAwait(false);
            var status = (string?)body["status"];
            if (done(status))
            {
                return body;
            }

            if (failed(status))
            {
                var error = body["error"] ?? body["challenges"]?.AsArray().Select(c => c?["error"]).FirstOrDefault(e => e is not null);
                throw new AcmeException((string?)error?["type"] ?? string.Empty, $"The {what} is {status}: {(string?)error?["detail"] ?? "no detail"}", HttpStatusCode.OK);
            }

            if (_time.GetUtcNow() > deadline)
            {
                throw new AcmeException($"The {what} was still {status} after {PollLimit.TotalSeconds:0} s.");
            }

            var wait = r.Headers.RetryAfter?.Delta ?? (r.Headers.RetryAfter?.Date - _time.GetUtcNow()) ?? PollInterval;
            wait = TimeSpan.FromSeconds(Math.Clamp(wait.TotalSeconds, 0.5, 30));
            await Task.Delay(wait, _time, ct).ConfigureAwait(false);
        }
    }

    private async Task<JsonObject> PostAsGetJsonAsync(string url, CancellationToken ct)
    {
        using var r = await PostAsync(url, null, useJwk: false, ct).ConfigureAwait(false);
        return await ReadJsonAsync(r, ct).ConfigureAwait(false);
    }

    private async Task<HttpResponseMessage> PostAsync(string url, JsonNode? payload, bool useJwk, CancellationToken ct, string? accept = null)
    {
        for (int attempt = 0; ; attempt++)
        {
            var nonce = await TakeNonceAsync(ct).ConfigureAwait(false);
            var body = AcmeJws.Sign(_accountKey, url, nonce, useJwk ? null : _accountUrl, payload);
            using var req = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = new StringContent(body, Encoding.UTF8),
            };
            req.Content.Headers.ContentType = new MediaTypeHeaderValue(JoseJson);
            if (accept is not null)
            {
                req.Headers.Accept.ParseAdd(accept);
            }

            var r = await _http.SendAsync(req, ct).ConfigureAwait(false);
            KeepNonce(r);
            if (r.IsSuccessStatusCode)
            {
                return r;
            }

            using (r)
            {
                var problem = await ReadProblemAsync(r, ct).ConfigureAwait(false);
                if (problem.Type == "urn:ietf:params:acme:error:badNonce" && attempt < MaxNonceRetries)
                {
                    _log.LogDebug("ACME badNonce, retrying");
                    continue;
                }

                throw problem;
            }
        }
    }

    private async Task<string> TakeNonceAsync(CancellationToken ct)
    {
        var n = Interlocked.Exchange(ref _nonce, null);
        if (n is not null)
        {
            return n;
        }

        using var req = new HttpRequestMessage(HttpMethod.Head, await EndpointAsync("newNonce", ct).ConfigureAwait(false));
        using var r = await _http.SendAsync(req, ct).ConfigureAwait(false);
        return r.Headers.TryGetValues("Replay-Nonce", out var v) ? v.First()
            : throw new AcmeException("The ACME server didn't give a nonce.");
    }

    private void KeepNonce(HttpResponseMessage r)
    {
        if (r.Headers.TryGetValues("Replay-Nonce", out var v))
        {
            _nonce = v.First();
        }
    }

    private async Task<JsonObject> DirectoryAsync(CancellationToken ct)
    {
        if (_directory is null)
        {
            using var r = await _http.GetAsync(_directoryUrl, ct).ConfigureAwait(false);
            if (!r.IsSuccessStatusCode)
            {
                throw new AcmeException($"The ACME directory answered HTTP {(int)r.StatusCode}.");
            }

            _directory = await ReadJsonAsync(r, ct).ConfigureAwait(false);
        }

        return _directory;
    }

    private async Task<string> EndpointAsync(string name, CancellationToken ct)
        => (string?)(await DirectoryAsync(ct).ConfigureAwait(false))[name] ?? throw new AcmeException($"The ACME directory has no {name}.");

    private static async Task<JsonObject> ReadJsonAsync(HttpResponseMessage r, CancellationToken ct)
    {
        var text = await r.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        return (JsonNode.Parse(text) as JsonObject) ?? throw new AcmeException("The ACME server sent something that isn't a JSON object.");
    }

    private static async Task<AcmeException> ReadProblemAsync(HttpResponseMessage r, CancellationToken ct)
    {
        try
        {
            var p = await ReadJsonAsync(r, ct).ConfigureAwait(false);
            return new AcmeException((string?)p["type"] ?? string.Empty, (string?)p["detail"] ?? "no detail", r.StatusCode);
        }
        catch (System.Text.Json.JsonException)
        {
            return new AcmeException(string.Empty, "unreadable error", r.StatusCode);
        }
        catch (AcmeException)
        {
            return new AcmeException(string.Empty, "unreadable error", r.StatusCode);
        }
    }
}
