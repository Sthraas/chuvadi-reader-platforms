using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using ChuvadiReader.Web.Auth;
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
/// A minimal OpenID Connect provider shaped like Sangam (our own test code), so CI can test the
/// portal's sign-in without a running Sangam: discovery, JWKS (RS256), an authorize endpoint that
/// signs a fixed person in at once and redirects back (with <c>iss</c>, RFC 9207), a token endpoint
/// that checks the code, redirect URI, PKCE and client authentication (secret or private_key_jwt),
/// and end-session. It can also mint logout tokens.
/// </summary>
public sealed class FakeSangam : IAsyncDisposable
{
    private readonly RSA _key = RSA.Create(2048);
    private readonly ConcurrentDictionary<string, CodeGrant> _codes = new();
    private WebApplication _app = default!;

    public const string ClientId = "chuvadi-portal";
    public const string ClientSecret = "chuvadi-portal-test-secret-0123456789abcdef";

    public string Kid { get; } = "test-key-1";
    public Uri Base { get; private set; } = default!;
    public string Issuer => Base.ToString();
    public string Subject { get; set; } = "4b1d7f0e-0000-4000-8000-000000000001";
    public string Name { get; set; } = "Asha Menon";
    public string Sid { get; set; } = "sid-1";

    /// <summary>Public key the token endpoint accepts for private_key_jwt (null: secret only).</summary>
    public ECDsa? ClientAssertionKey { get; set; }

    /// <summary>Tamper with the ID token before it is signed (tests of refusals).</summary>
    public Action<JsonObject, JsonObject>? MutateIdToken { get; set; }

    /// <summary>Leave <c>iss</c> off the authorization response.</summary>
    public bool OmitIssInResponse { get; set; }

    public List<string> TokenRequests { get; } = new();

    private sealed record CodeGrant(string RedirectUri, string Challenge, string Nonce, string ClientId);

    public async Task StartAsync()
    {
        var b = WebApplication.CreateSlimBuilder();
        b.Logging.ClearProviders();
        b.WebHost.UseUrls("http://127.0.0.1:0");
        _app = b.Build();
        _app.MapGet("/.well-known/openid-configuration", () => Results.Json(new Dictionary<string, object>
        {
            ["issuer"] = Issuer,
            ["authorization_endpoint"] = U("/connect/authorize"),
            ["token_endpoint"] = U("/connect/token"),
            ["end_session_endpoint"] = U("/connect/endsession"),
            ["jwks_uri"] = U("/.well-known/jwks"),
            ["authorization_response_iss_parameter_supported"] = true,
            ["backchannel_logout_supported"] = true,
        }));
        _app.MapGet("/.well-known/jwks", () =>
        {
            var p = _key.ExportParameters(false);
            return Results.Json(new { keys = new[] { new { kty = "RSA", use = "sig", alg = "RS256", kid = Kid, n = AcmeJws.Base64Url(p.Modulus), e = AcmeJws.Base64Url(p.Exponent) } } });
        });
        _app.MapGet("/connect/authorize", (HttpContext c) =>
        {
            var q = c.Request.Query;
            if (q["client_id"] != ClientId || q["response_type"] != "code" || q["code_challenge_method"] != "S256" || string.IsNullOrEmpty(q["nonce"]))
            {
                return Results.BadRequest("bad authorize request");
            }

            var code = AcmeJws.Base64Url(RandomNumberGenerator.GetBytes(24));
            _codes[code] = new CodeGrant(q["redirect_uri"]!, q["code_challenge"]!, q["nonce"]!, q["client_id"]!);
            var back = $"{q["redirect_uri"]}?code={code}&state={Uri.EscapeDataString(q["state"]!)}";
            if (!OmitIssInResponse)
            {
                back += "&iss=" + Uri.EscapeDataString(Issuer);
            }

            return Results.Redirect(back);
        });
        _app.MapPost("/connect/token", async (HttpContext c) =>
        {
            var form = await c.Request.ReadFormAsync();
            TokenRequests.Add(string.Join("&", form.Select(kv => kv.Key)));
            if (!ClientAuthenticated(c, form))
            {
                return Results.Json(new { error = "invalid_client" }, statusCode: 401);
            }

            if (form["grant_type"] != "authorization_code" || !_codes.TryRemove(form["code"]!, out var grant))
            {
                return Results.Json(new { error = "invalid_grant" }, statusCode: 400);
            }

            var challenge = AcmeJws.Base64Url(SHA256.HashData(Encoding.ASCII.GetBytes(form["code_verifier"].ToString())));
            if (grant.RedirectUri != form["redirect_uri"] || grant.Challenge != challenge)
            {
                return Results.Json(new { error = "invalid_grant", error_description = "PKCE or redirect mismatch" }, statusCode: 400);
            }

            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            var header = new JsonObject { ["alg"] = "RS256", ["kid"] = Kid, ["typ"] = "JWT" };
            var payload = new JsonObject
            {
                ["iss"] = Issuer,
                ["aud"] = ClientId,
                ["sub"] = Subject,
                ["name"] = Name,
                ["email"] = "asha@example.in",
                ["sid"] = Sid,
                ["nonce"] = grant.Nonce,
                ["iat"] = now,
                ["exp"] = now + 3600,
                ["auth_time"] = now,
            };
            MutateIdToken?.Invoke(header, payload);
            return Results.Json(new { access_token = "opaque", token_type = "Bearer", expires_in = 3600, id_token = Sign(header, payload) });
        });
        _app.MapGet("/connect/endsession", (HttpContext c) =>
            Results.Redirect(c.Request.Query["post_logout_redirect_uri"].ToString() is { Length: > 0 } back ? back : "/"));
        await _app.StartAsync();
        Base = new Uri(_app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First() + "/");
    }

    private bool ClientAuthenticated(HttpContext c, IFormCollection form)
    {
        if (form["client_assertion_type"] == ClientAuthentication.AssertionType && ClientAssertionKey is not null)
        {
            var jwt = Jwt.Parse(form["client_assertion"]!);
            var ok = ClientAssertionKey.VerifyData(jwt.SigningInput, jwt.Signature, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            return ok && jwt.Alg == "ES256" && jwt.Typ == "client-authentication+jwt" && jwt.Claim("iss") == ClientId && jwt.Claim("sub") == ClientId
                   && jwt.Claim("aud") == Issuer && !string.IsNullOrEmpty(jwt.Claim("jti"))
                   && jwt.NumericClaim("exp") is long exp && exp > now && exp - jwt.NumericClaim("iat") <= 300;
        }

        var auth = c.Request.Headers.Authorization.ToString();
        if (!auth.StartsWith("Basic ", StringComparison.Ordinal))
        {
            return false;
        }

        var pair = Encoding.UTF8.GetString(Convert.FromBase64String(auth[6..])).Split(':', 2);
        return Uri.UnescapeDataString(pair[0]) == ClientId && Uri.UnescapeDataString(pair[1]) == ClientSecret;
    }

    /// <summary>A logout token as Sangam sends it; <paramref name="mutate"/> breaks it for refusal tests.</summary>
    public string LogoutToken(string? sid, string? sub = null, Action<JsonObject, JsonObject>? mutate = null)
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var header = new JsonObject { ["alg"] = "RS256", ["kid"] = Kid, ["typ"] = "logout+jwt" };
        var payload = new JsonObject
        {
            ["iss"] = Issuer,
            ["aud"] = ClientId,
            ["iat"] = now,
            ["exp"] = now + 120,
            ["jti"] = Guid.NewGuid().ToString("D"),
            ["events"] = new JsonObject { [JwtVerifier.LogoutEvent] = new JsonObject() },
        };
        if (sid is not null) payload["sid"] = sid;
        if (sub is not null) payload["sub"] = sub;
        mutate?.Invoke(header, payload);
        return Sign(header, payload);
    }

    public string Sign(JsonObject header, JsonObject payload)
        => Jwt.Create(header, payload, input => _key.SignData(input, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1));

    private string U(string path) => new Uri(Base, path.TrimStart('/')).ToString();

    public async ValueTask DisposeAsync()
    {
        await _app.DisposeAsync();
        _key.Dispose();
    }
}
