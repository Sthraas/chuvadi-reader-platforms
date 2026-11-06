using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json.Nodes;
using ChuvadiReader.Web.Hosting.Acme;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace ChuvadiReader.Web.Tests;

/// <summary>
/// A strict, in-process ACME server for tests (our own test code, RFC 8555): checks every JWS
/// signature, single-use nonces, the <c>url</c> header, <c>jwk</c> only on newAccount and <c>kid</c>
/// elsewhere, validates http-01 by fetching the key authorization from the portal under test, and
/// issues certificates from a throwaway test CA for exactly the ordered names.
/// </summary>
public sealed class FakeAcmeServer : IAsyncDisposable
{
    private readonly ConcurrentDictionary<string, bool> _nonces = new();
    private readonly ConcurrentDictionary<string, ECDsa> _accounts = new();
    private readonly ConcurrentDictionary<string, Order> _orders = new();
    private readonly ConcurrentDictionary<string, Authz> _authz = new();
    private readonly ConcurrentDictionary<string, string> _certs = new();
    private readonly ECDsa _caKey = ECDsa.Create(ECCurve.NamedCurves.nistP256);
    private readonly X509Certificate2 _ca;
    private WebApplication _app = default!;
    private int _n;

    public FakeAcmeServer()
    {
        var req = new CertificateRequest("CN=Fake ACME Test CA", _caKey, HashAlgorithmName.SHA256);
        req.CertificateExtensions.Add(new X509BasicConstraintsExtension(true, false, 0, true));
        _ca = req.CreateSelfSigned(DateTimeOffset.UtcNow.AddYears(-1), DateTimeOffset.UtcNow.AddYears(2));
    }

    /// <summary>Where http-01 validation fetches from (the portal under test), instead of resolving the domain.</summary>
    public Uri? ValidationBase { get; set; }

    /// <summary>Lifetime of issued certificates.</summary>
    public TimeSpan CertificateLifetime { get; set; } = TimeSpan.FromDays(90);

    /// <summary>Issue certificates whose life started this long ago (to test the renewal window).</summary>
    public TimeSpan Backdate { get; set; } = TimeSpan.Zero;

    /// <summary>Reject this many requests with badNonce before accepting (tests nonce retry).</summary>
    public int BadNonceBudget { get; set; }

    /// <summary>Make every http-01 validation fail (tests failure handling).</summary>
    public bool FailValidation { get; set; }

    public Uri Directory => new(Base, "/directory");

    public Uri Base { get; private set; } = default!;

    public int Issued => _certs.Count;

    public int Accounts => _accounts.Count;

    public List<string> Violations { get; } = new();

    public async Task StartAsync()
    {
        var b = WebApplication.CreateSlimBuilder();
        b.Logging.ClearProviders();
        b.WebHost.UseUrls("http://127.0.0.1:0");
        _app = b.Build();
        _app.MapGet("/directory", () => Results.Json(new
        {
            newNonce = U("/new-nonce"),
            newAccount = U("/new-account"),
            newOrder = U("/new-order"),
            revokeCert = U("/revoke"),
            keyChange = U("/key-change"),
            meta = new { termsOfService = U("/terms") },
        }));
        _app.MapMethods("/new-nonce", ["HEAD", "GET"], (HttpContext c) => { Nonce(c); return Results.Ok(); });
        _app.MapPost("/new-account", (Delegate)((HttpContext c) => NewAccount(c)));
        _app.MapPost("/new-order", (Delegate)((HttpContext c) => NewOrder(c)));
        _app.MapPost("/order/{id}", (HttpContext c, string id) => GetOrder(c, id));
        _app.MapPost("/authz/{id}", (HttpContext c, string id) => GetAuthz(c, id));
        _app.MapPost("/chall/{id}", (HttpContext c, string id) => Respond(c, id));
        _app.MapPost("/finalize/{id}", (HttpContext c, string id) => Finalize(c, id));
        _app.MapPost("/cert/{id}", (HttpContext c, string id) => GetCert(c, id));
        await _app.StartAsync();
        Base = new Uri(_app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
    }

    public X509Certificate2 CaCertificate => _ca;

    // ── handlers ────────────────────────────────────────────────────────────────────

    private async Task<IResult> NewAccount(HttpContext c)
    {
        var (h, payload, error) = await ReadAsync(c, expectJwk: true);
        if (error is not null) return error;
        var jwk = h["jwk"]!.AsObject();
        var thumb = AcmeJws.Thumbprint(AcmeJws.ImportJwk(jwk));
        var p = JsonNode.Parse(payload)!.AsObject();
        if (p["termsOfServiceAgreed"]?.GetValue<bool>() != true)
        {
            return Problem(c, "userActionRequired", "Terms of service must be agreed", 403);
        }

        var url = U("/acct/" + thumb);
        var created = _accounts.TryAdd(url, AcmeJws.ImportJwk(jwk));
        c.Response.Headers.Location = url;
        return Results.Json(new { status = "valid", contact = p["contact"] }, statusCode: created ? 201 : 200);
    }

    private async Task<IResult> NewOrder(HttpContext c)
    {
        var (_, payload, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        var names = JsonNode.Parse(payload)!["identifiers"]!.AsArray().Select(i => (string)i!["value"]!).ToList();
        var id = Id();
        var order = new Order(id, names);
        foreach (var name in names)
        {
            var a = new Authz(Id(), name, Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(16)));
            _authz[a.Id] = a;
            order.Authz.Add(a.Id);
        }

        _orders[id] = order;
        c.Response.Headers.Location = U("/order/" + id);
        return Results.Json(OrderJson(order), statusCode: 201);
    }

    private async Task<IResult> GetOrder(HttpContext c, string id)
    {
        var (_, payload, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        if (payload.Length != 0) Violations.Add("order fetch must be POST-as-GET");
        var o = _orders[id];
        if (o.Status == "pending" && o.Authz.All(a => _authz[a].Status == "valid")) o.Status = "ready";
        if (o.Authz.Any(a => _authz[a].Status == "invalid")) o.Status = "invalid";
        return Results.Json(OrderJson(o));
    }

    private async Task<IResult> GetAuthz(HttpContext c, string id)
    {
        var (_, payload, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        if (payload.Length != 0) Violations.Add("authz fetch must be POST-as-GET");
        return Results.Json(AuthzJson(_authz[id]));
    }

    private async Task<IResult> Respond(HttpContext c, string id)
    {
        var (h, payload, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        if (payload != "{}") Violations.Add("challenge response payload must be {}");
        var a = _authz[id];
        var key = _accounts[(string)h["kid"]!];
        var expected = AcmeJws.KeyAuthorization(a.Token, key);
        string? got = null;
        try
        {
            using var http = new HttpClient();
            var b = ValidationBase ?? new Uri("http://" + a.Name);
            got = await http.GetStringAsync(new Uri(b, "/.well-known/acme-challenge/" + a.Token));
        }
        catch (HttpRequestException)
        {
        }

        a.Status = !FailValidation && got == expected ? "valid" : "invalid";
        a.Error = a.Status == "invalid" ? "key authorization mismatch" : null;
        return Results.Json(ChallengeJson(a));
    }

    private async Task<IResult> Finalize(HttpContext c, string id)
    {
        var (_, payload, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        var o = _orders[id];
        if (o.Status != "ready") return Problem(c, "orderNotReady", "Order not ready", 403);
        var der = AcmeJws.FromBase64Url((string)JsonNode.Parse(payload)!["csr"]!);
        var csr = CertificateRequest.LoadSigningRequest(der, HashAlgorithmName.SHA256, CertificateRequestLoadOptions.UnsafeLoadCertificateExtensions);
        var san = csr.CertificateExtensions.OfType<X509SubjectAlternativeNameExtension>().Single().EnumerateDnsNames().ToList();
        if (!san.OrderBy(x => x).SequenceEqual(o.Names.OrderBy(x => x)))
        {
            return Problem(c, "badCSR", "CSR names don't match the order", 400);
        }

        var serial = RandomNumberGenerator.GetBytes(12);
        serial[0] &= 0x7F;
        var now = DateTimeOffset.UtcNow;
        var notBefore = now - Backdate - TimeSpan.FromMinutes(5);
        using var leaf = csr.Create(_ca, notBefore, notBefore + CertificateLifetime, serial);
        _certs[id] = leaf.ExportCertificatePem() + "\n" + _ca.ExportCertificatePem() + "\n";
        o.Status = "valid";
        o.Cert = U("/cert/" + id);
        return Results.Json(OrderJson(o));
    }

    private async Task<IResult> GetCert(HttpContext c, string id)
    {
        var (_, _, error) = await ReadAsync(c, expectJwk: false);
        if (error is not null) return error;
        return Results.Text(_certs[id], "application/pem-certificate-chain");
    }

    // ── JWS checks ──────────────────────────────────────────────────────────────────

    private async Task<(JsonObject Header, string Payload, IResult? Error)> ReadAsync(HttpContext c, bool expectJwk)
    {
        if (c.Request.ContentType != "application/jose+json") Violations.Add("content type " + c.Request.ContentType);
        var body = await new StreamReader(c.Request.Body).ReadToEndAsync();
        var (h, _, _) = AcmeJws.Verify(body, expectJwk ? null : ECDsa.Create(ECCurve.NamedCurves.nistP256));
        var nonce = (string?)h["nonce"];
        if (nonce is null || !_nonces.TryRemove(nonce, out _))
        {
            return (h, string.Empty, Problem(c, "badNonce", "Bad nonce", 400));
        }

        if (BadNonceBudget > 0)
        {
            BadNonceBudget--;
            return (h, string.Empty, Problem(c, "badNonce", "Bad nonce (forced)", 400));
        }

        var url = (string?)h["url"];
        if (url != U(c.Request.Path)) Violations.Add($"url header {url} != {U(c.Request.Path)}");
        if ((string?)h["alg"] != "ES256") Violations.Add("alg " + h["alg"]);
        ECDsa key;
        if (expectJwk)
        {
            if (h["jwk"] is null || h["kid"] is not null) Violations.Add("newAccount must use jwk");
            key = AcmeJws.ImportJwk(h["jwk"]!.AsObject());
        }
        else
        {
            if (h["kid"] is null || h["jwk"] is not null) Violations.Add("requests after newAccount must use kid");
            if (!_accounts.TryGetValue((string)h["kid"]!, out key!))
            {
                return (h, string.Empty, Problem(c, "accountDoesNotExist", "No such account", 400));
            }
        }

        var (_, payload, ok) = AcmeJws.Verify(body, key);
        if (!ok)
        {
            return (h, string.Empty, Problem(c, "malformed", "Bad signature", 400));
        }

        Nonce(c);
        return (h, payload, null);
    }

    private IResult Problem(HttpContext c, string type, string detail, int status)
    {
        Nonce(c);
        return Results.Json(new { type = "urn:ietf:params:acme:error:" + type, detail }, statusCode: status, contentType: "application/problem+json");
    }

    private void Nonce(HttpContext c)
    {
        var n = AcmeJws.Base64Url(RandomNumberGenerator.GetBytes(16));
        _nonces[n] = true;
        c.Response.Headers["Replay-Nonce"] = n;
        c.Response.Headers.CacheControl = "no-store";
    }

    private object OrderJson(Order o) => new
    {
        status = o.Status,
        identifiers = o.Names.Select(n => new { type = "dns", value = n }),
        authorizations = o.Authz.Select(a => U("/authz/" + a)),
        finalize = U("/finalize/" + o.Id),
        certificate = o.Cert,
    };

    private object AuthzJson(Authz a) => new
    {
        status = a.Status,
        identifier = new { type = "dns", value = a.Name },
        challenges = new[] { ChallengeJson(a), new { type = "dns-01", url = U("/chall/x"), token = "dnsonly", status = "pending", error = (object?)null } },
    };

    private object ChallengeJson(Authz a) => new
    {
        type = "http-01",
        url = U("/chall/" + a.Id),
        token = a.Token,
        status = a.Status == "valid" ? "valid" : a.Status == "invalid" ? "invalid" : "pending",
        error = a.Error is null ? null : (object)new { type = "urn:ietf:params:acme:error:unauthorized", detail = a.Error },
    };

    private string U(string path) => new Uri(Base, path).ToString();

    private string Id() => Interlocked.Increment(ref _n).ToString(System.Globalization.CultureInfo.InvariantCulture);

    private sealed class Order(string id, List<string> names)
    {
        public string Id { get; } = id;
        public List<string> Names { get; } = names;
        public List<string> Authz { get; } = new();
        public string Status { get; set; } = "pending";
        public string? Cert { get; set; }
    }

    private sealed class Authz(string id, string name, string token)
    {
        public string Id { get; } = id;
        public string Name { get; } = name;
        public string Token { get; } = token;
        public string Status { get; set; } = "pending";
        public string? Error { get; set; }
    }

    public async ValueTask DisposeAsync()
    {
        await _app.DisposeAsync();
        _ca.Dispose();
        _caKey.Dispose();
    }
}
