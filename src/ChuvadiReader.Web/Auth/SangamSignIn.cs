using System.Net.Http.Headers;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using ChuvadiReader.Web.Hosting.Acme;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// The portal as a Sangam client: OpenID Connect Authorization Code flow with PKCE (S256), our own
/// code on the framework's cookie authentication and Data Protection (no OpenID Connect package).
/// <list type="number">
/// <item><c>GET /signin</c> → Sangam's authorize endpoint (state, nonce, PKCE, kept in an encrypted, short-lived cookie).</item>
/// <item><c>GET /signin-sangam</c> → checks state and <c>iss</c> (RFC 9207), redeems the code with client
/// authentication, verifies the ID token, signs the person in to the portal cookie.</item>
/// <item><c>GET /signout</c> → ends the portal sign-in on every tab, then Sangam's end-session endpoint.</item>
/// <item><c>POST /backchannel-logout</c> → Sangam says a sign-in ended; every tab of it is ended.</item>
/// </list>
/// </summary>
public static class SangamSignIn
{
    public const string FlowCookiePrefix = "chvd.oidc.";
    public const string SignedOutPath = "/signed-out";
    public const string SignOutCookie = "chvd.signout";

    private const string Purpose = "ChuvadiReader.Web.Auth.SignInFlow.v1";

    /// <summary>What a sign-in in flight remembers between leaving for Sangam and coming back.</summary>
    internal sealed record Flow(string State, string Nonce, string Verifier, string ReturnUrl, long CreatedUnix);

    public static IEndpointRouteBuilder MapSangamSignIn(this IEndpointRouteBuilder app)
    {
        var o = app.ServiceProvider.GetRequiredService<IOptions<SangamOptions>>().Value;

        app.MapGet("/signin", (Delegate)SignInAsync).AllowAnonymous();
        app.MapGet(o.CallbackPath, (Delegate)CallbackAsync).AllowAnonymous();
        app.MapGet("/signout", (Delegate)SignOutAsync).AllowAnonymous();
        app.MapGet(o.SignedOutCallbackPath, (Delegate)SignedOutCallbackAsync).AllowAnonymous();
        app.MapGet(SignedOutPath, () => Results.Content(SignedOutPage, "text/html; charset=utf-8")).AllowAnonymous();
        app.MapPost(o.BackChannelLogoutPath, (Delegate)BackChannelLogoutAsync).AllowAnonymous().DisableAntiforgery();
        return app;
    }

    // ── 1. leave for Sangam ─────────────────────────────────────────────────────────

    private static async Task<IResult> SignInAsync(HttpContext http, SangamMetadata metadata, IOptions<SangamOptions> options,
        IDataProtectionProvider dp, TimeProvider time, string? returnUrl)
    {
        var o = options.Value;
        var flow = new Flow(Random(32), Random(32), Random(48), SafeReturnUrl(returnUrl), time.GetUtcNow().ToUnixTimeSeconds());
        var protector = dp.CreateProtector(Purpose);
        http.Response.Cookies.Append(FlowCookiePrefix + flow.State[..16], protector.Protect(JsonSerializer.Serialize(flow)), new CookieOptions
        {
            HttpOnly = true,
            Secure = http.Request.IsHttps,
            SameSite = SameSiteMode.Lax, // must come back on Sangam's top-level redirect
            Path = o.CallbackPath,
            MaxAge = o.SignInTimeLimit,
            IsEssential = true,
        });

        var challenge = AcmeJws.Base64Url(SHA256.HashData(Encoding.ASCII.GetBytes(flow.Verifier)));
        var query = new Dictionary<string, string?>
        {
            ["response_type"] = "code",
            ["client_id"] = o.ClientId,
            ["redirect_uri"] = CallbackUrl(http, o),
            ["scope"] = o.Scope,
            ["state"] = flow.State,
            ["nonce"] = flow.Nonce,
            ["code_challenge"] = challenge,
            ["code_challenge_method"] = "S256",
            ["ui_locales"] = o.UiLocales,
        };
        var authorize = await metadata.EndpointAsync("authorization_endpoint", http.RequestAborted).ConfigureAwait(false);
        return Results.Redirect(Microsoft.AspNetCore.WebUtilities.QueryHelpers.AddQueryString(authorize, query.Where(kv => !string.IsNullOrEmpty(kv.Value))!));
    }

    /// <summary>Cookie claim for the organisation unit shown after the Sangam ID (12b, D-35).</summary>
    public const string UnitClaim = "chvd_unit";

    /// <summary>The <c>name</c> of Sangam's <c>sangam_org</c> claim (the organisation this sign-in is for;
    /// sent with the <c>org.current</c> scope) — a JSON object, or the same as a string. Null otherwise.</summary>
    internal static string? OrganisationName(System.Text.Json.Nodes.JsonNode? org)
    {
        try
        {
            if (org is System.Text.Json.Nodes.JsonValue v && v.TryGetValue<string>(out var text))
            {
                org = System.Text.Json.Nodes.JsonNode.Parse(text);
            }

            return org is System.Text.Json.Nodes.JsonObject o && o["name"] is System.Text.Json.Nodes.JsonValue n && n.TryGetValue<string>(out var name)
                ? name.Trim() is { Length: > 0 and <= 120 } trimmed ? trimmed : null
                : null;
        }
        catch (System.Text.Json.JsonException)
        {
            return null;
        }
    }

    // ── 2. back from Sangam ─────────────────────────────────────────────────────────

    private static async Task<IResult> CallbackAsync(HttpContext http, SangamMetadata metadata, JwtVerifier verifier, IOptions<SangamOptions> options,
        IDataProtectionProvider dp, Hosting.Acme.IHttpClientFactoryLite httpFactory, ClientAuthentication clientAuth, TimeProvider time, ILoggerFactory logs)
    {
        var log = logs.CreateLogger("ChuvadiReader.Web.Auth.SangamSignIn");
        var o = options.Value;
        var q = http.Request.Query;
        string? state = q["state"];
        if (string.IsNullOrEmpty(state) || state.Length < 16)
        {
            return Fail("The sign-in answer has no state.");
        }

        var cookieName = FlowCookiePrefix + state[..16];
        var stored = http.Request.Cookies[cookieName];
        http.Response.Cookies.Delete(cookieName, new CookieOptions { Path = o.CallbackPath, Secure = http.Request.IsHttps, HttpOnly = true, SameSite = SameSiteMode.Lax });
        if (stored is null)
        {
            return Fail("This sign-in has expired or was started in another browser.");
        }

        Flow flow;
        try
        {
            flow = JsonSerializer.Deserialize<Flow>(dp.CreateProtector(Purpose).Unprotect(stored))!;
        }
        catch (CryptographicException)
        {
            return Fail("This sign-in can't be read.");
        }

        if (!CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(flow.State), Encoding.ASCII.GetBytes(state))
            || time.GetUtcNow().ToUnixTimeSeconds() - flow.CreatedUnix > (long)o.SignInTimeLimit.TotalSeconds)
        {
            return Fail("This sign-in has expired.");
        }

        // RFC 9207: the answer must say it comes from our Sangam (mix-up defence) when Sangam supports it.
        var discovery = await metadata.DiscoveryAsync(http.RequestAborted).ConfigureAwait(false);
        string? iss = q["iss"];
        if (iss is not null ? iss != o.Issuer : discovery["authorization_response_iss_parameter_supported"]?.GetValue<bool>() == true)
        {
            return Fail("The sign-in answer isn't from the configured Sangam.");
        }

        if (q["error"].ToString() is { Length: > 0 } error)
        {
            log.LogInformation("Sangam returned {Error}: {Description}", error, q["error_description"].ToString());
            return error == "access_denied" ? Results.Redirect(SignedOutPath) : Fail("Sangam didn't complete the sign-in.");
        }

        string? code = q["code"];
        if (string.IsNullOrEmpty(code))
        {
            return Fail("The sign-in answer has no code.");
        }

        // Redeem the code.
        var tokenEndpoint = await metadata.EndpointAsync("token_endpoint", http.RequestAborted).ConfigureAwait(false);
        var form = new Dictionary<string, string>
        {
            ["grant_type"] = "authorization_code",
            ["code"] = code,
            ["redirect_uri"] = CallbackUrl(http, o),
            ["code_verifier"] = flow.Verifier,
        };
        using var req = new HttpRequestMessage(HttpMethod.Post, tokenEndpoint);
        clientAuth.Apply(req, form);
        req.Content = new FormUrlEncodedContent(form);
        req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        using var client = httpFactory.Create();
        using var resp = await client.SendAsync(req, http.RequestAborted).ConfigureAwait(false);
        var body = await resp.Content.ReadAsStringAsync(http.RequestAborted).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode)
        {
            log.LogWarning("Sangam's token endpoint refused the code: HTTP {Status} {Body}", (int)resp.StatusCode, body.Length > 300 ? body[..300] : body);
            return Fail("Sangam didn't accept the sign-in.");
        }

        var tokens = JsonNode.Parse(body) as JsonObject;
        var idToken = (string?)tokens?["id_token"];
        if (idToken is null)
        {
            return Fail("Sangam sent no ID token.");
        }

        Jwt id;
        try
        {
            id = await verifier.VerifyIdTokenAsync(idToken, flow.Nonce, http.RequestAborted).ConfigureAwait(false);
        }
        catch (SecurityTokenException ex)
        {
            log.LogWarning("ID token refused: {Message}", ex.Message);
            return Fail("Sangam's answer couldn't be verified.");
        }

        var claims = new List<Claim> { new("sub", id.Claim("sub")!) };
        foreach (var name in new[] { "name", "email", "sid", "acr" })
        {
            if (id.Claim(name) is { Length: > 0 } v)
            {
                claims.Add(new Claim(name, v));
            }
        }

        if (OrganisationName(id.Payload["sangam_org"]) is { Length: > 0 } unit)
        {
            claims.Add(new Claim(UnitClaim, unit));
        }

        if (id.NumericClaim("auth_time") is long authTime)
        {
            claims.Add(new Claim("auth_time", authTime.ToString(System.Globalization.CultureInfo.InvariantCulture)));
        }

        var now = time.GetUtcNow();
        var principal = new ClaimsPrincipal(new ClaimsIdentity(claims, "Sangam", "name", "role"));
        var props = new AuthenticationProperties
        {
            IssuedUtc = now,
            ExpiresUtc = now + o.AbsoluteSessionLifetime,
            IsPersistent = false,
            AllowRefresh = false,
        };
        props.StoreTokens([new AuthenticationToken { Name = "id_token", Value = idToken }]);
        await http.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, principal, props).ConfigureAwait(false);
        return Results.Redirect(flow.ReturnUrl);
    }

    // ── 3. sign out ─────────────────────────────────────────────────────────────────

    private static async Task<IResult> SignOutAsync(HttpContext http, SangamMetadata metadata, PortalSessions sessions, IOptions<SangamOptions> options,
        IDataProtectionProvider dp)
    {
        // A cross-site page could make a browser call this; it only signs out, but refuse it anyway.
        var site = http.Request.Headers["Sec-Fetch-Site"].ToString();
        if (site is "cross-site")
        {
            return Results.StatusCode(StatusCodes.Status403Forbidden);
        }

        var result = await http.AuthenticateAsync(CookieAuthenticationDefaults.AuthenticationScheme).ConfigureAwait(false);
        await http.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme).ConfigureAwait(false);
        if (!result.Succeeded)
        {
            return Results.Redirect(SignedOutPath);
        }

        var user = result.Principal!;
        var sub = user.FindFirst("sub")?.Value;
        var sid = user.FindFirst("sid")?.Value;
        // The cookie stops working everywhere now; open tabs are ended when Sangam sends the browser back.
        await sessions.RevokeAsync(sub, sid, endTabs: false).ConfigureAwait(false);

        var o = options.Value;
        http.Response.Cookies.Append(SignOutCookie, dp.CreateProtector(Purpose + ".signout").Protect(JsonSerializer.Serialize(new[] { sub, sid })), new CookieOptions
        {
            HttpOnly = true,
            Secure = http.Request.IsHttps,
            SameSite = SameSiteMode.Lax,
            Path = o.SignedOutCallbackPath,
            MaxAge = TimeSpan.FromMinutes(10),
            IsEssential = true,
        });
        var endSession = await metadata.OptionalEndpointAsync("end_session_endpoint", http.RequestAborted).ConfigureAwait(false);
        if (endSession is null)
        {
            return Results.Redirect(SignedOutPath);
        }

        var query = new Dictionary<string, string?>
        {
            ["id_token_hint"] = result.Properties?.GetTokenValue("id_token"),
            ["client_id"] = o.ClientId,
            ["post_logout_redirect_uri"] = BaseUrl(http) + o.SignedOutCallbackPath,
        };
        return Results.Redirect(Microsoft.AspNetCore.WebUtilities.QueryHelpers.AddQueryString(endSession, query.Where(kv => !string.IsNullOrEmpty(kv.Value))!));
    }

    /// <summary>Back from Sangam's end-session: end every tab of the sign-in that was signed out, then show the signed-out page.</summary>
    private static async Task<IResult> SignedOutCallbackAsync(HttpContext http, PortalSessions sessions, IOptions<SangamOptions> options, IDataProtectionProvider dp)
    {
        var stored = http.Request.Cookies[SignOutCookie];
        http.Response.Cookies.Delete(SignOutCookie, new CookieOptions { Path = options.Value.SignedOutCallbackPath, Secure = http.Request.IsHttps, HttpOnly = true, SameSite = SameSiteMode.Lax });
        if (stored is not null)
        {
            try
            {
                var ids = JsonSerializer.Deserialize<string?[]>(dp.CreateProtector(Purpose + ".signout").Unprotect(stored));
                if (ids is { Length: 2 })
                {
                    await sessions.RevokeAsync(ids[0], ids[1]).ConfigureAwait(false);
                }
            }
            catch (CryptographicException)
            {
            }
        }

        return Results.Redirect(SignedOutPath);
    }

    // ── 4. Sangam says a sign-in ended ──────────────────────────────────────────────

    private static async Task<IResult> BackChannelLogoutAsync(HttpContext http, JwtVerifier verifier, PortalSessions sessions, ILoggerFactory logs)
    {
        var log = logs.CreateLogger("ChuvadiReader.Web.Auth.SangamSignIn");
        http.Response.Headers.CacheControl = "no-store";
        if (!http.Request.HasFormContentType)
        {
            return Results.BadRequest();
        }

        var form = await http.Request.ReadFormAsync(http.RequestAborted).ConfigureAwait(false);
        string? token = form["logout_token"];
        if (string.IsNullOrEmpty(token))
        {
            return Results.BadRequest();
        }

        Jwt jwt;
        try
        {
            jwt = await verifier.VerifyLogoutTokenAsync(token, http.RequestAborted).ConfigureAwait(false);
        }
        catch (SecurityTokenException ex)
        {
            log.LogWarning("Logout token refused: {Message}", ex.Message);
            return Results.BadRequest();
        }

        if (!sessions.FirstUse(jwt.Claim("jti")!))
        {
            return Results.Ok(); // already done
        }

        var ended = await sessions.RevokeAsync(jwt.Claim("sub"), jwt.Claim("sid")).ConfigureAwait(false);
        log.LogInformation("Back-channel logout ended {Count} open tab(s)", ended);
        return Results.Ok();
    }

    // ── helpers ─────────────────────────────────────────────────────────────────────

    /// <summary>Cookie checks on every request: the sign-in wasn't revoked since.</summary>
    public static Task ValidatePrincipalAsync(CookieValidatePrincipalContext context)
    {
        var sessions = context.HttpContext.RequestServices.GetRequiredService<PortalSessions>();
        var user = context.Principal;
        var issued = context.Properties.IssuedUtc ?? DateTimeOffset.MinValue;
        if (!sessions.IsValid(user?.FindFirst("sub")?.Value, user?.FindFirst("sid")?.Value, issued))
        {
            context.RejectPrincipal();
        }

        return Task.CompletedTask;
    }

    internal static string SafeReturnUrl(string? url)
        => !string.IsNullOrEmpty(url) && url.StartsWith('/') && !url.StartsWith("//", StringComparison.Ordinal) && !url.StartsWith("/\\", StringComparison.Ordinal)
           && !url.Contains('\r') && !url.Contains('\n') && url.Length <= 2048
            ? url : "/";

    private static string CallbackUrl(HttpContext http, SangamOptions o) => BaseUrl(http) + o.CallbackPath;

    /// <summary>The portal's own public address: <c>Portal:PublicOrigin</c> when set, else the request's.</summary>
    private static string BaseUrl(HttpContext http)
    {
        var configured = http.RequestServices.GetRequiredService<IOptions<Hosting.PortalOptions>>().Value.PublicOrigin;
        return !string.IsNullOrWhiteSpace(configured) ? configured.TrimEnd('/') : $"{http.Request.Scheme}://{http.Request.Host}";
    }

    private static string Random(int bytes) => AcmeJws.Base64Url(RandomNumberGenerator.GetBytes(bytes));

    private static IResult Fail(string message)
        => Results.Content(Page("Sign-in didn't complete", System.Net.WebUtility.HtmlEncode(message), "/signin", "Try again"), "text/html; charset=utf-8", statusCode: 400);

    private static readonly string SignedOutPage = Page("Signed out", "Your files were removed from the server.", "/signin", "Sign in again");

    // Functional pages only; the Web portal UI chat owns their final look.
    private static string Page(string title, string message, string href, string action) =>
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">" +
        $"<title>{title} · Chuvadi</title><link rel=\"stylesheet\" href=\"/_content/ChuvadiReader.Ui/css/tokens.css\"></head>" +
        "<body style=\"margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--chvd-surface,#faf6ee);color:var(--chvd-ink,#1a1310);font-family:system-ui,sans-serif\">" +
        $"<main style=\"max-width:420px;padding:24px;text-align:center\"><h1 style=\"font-size:22px;font-weight:600\">{title}</h1><p>{message}</p>" +
        $"<p><a href=\"{href}\">{action}</a></p></main></body></html>";
}

/// <summary>
/// How the portal proves who it is to Sangam's token endpoint: <c>private_key_jwt</c> (preferred; a
/// two-minute, single-use assertion signed with our key, typed <c>client-authentication+jwt</c>,
/// audience Sangam's issuer) or <c>client_secret_basic</c>. Singleton.
/// </summary>
public sealed class ClientAuthentication : IDisposable
{
    public const string AssertionType = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer";

    private readonly SangamOptions _options;
    private readonly TimeProvider _time;
    private readonly AsymmetricAlgorithm? _key;
    private readonly string? _alg;

    public ClientAuthentication(IOptions<SangamOptions> options, TimeProvider time)
    {
        _options = options.Value;
        _time = time;
        if (!string.IsNullOrWhiteSpace(_options.PrivateKeyPath))
        {
            var pem = File.ReadAllText(_options.PrivateKeyPath);
            if (TryEc(pem, out var ec))
            {
                (_key, _alg) = (ec, ec!.KeySize switch { 256 => "ES256", 384 => "ES384", 521 => "ES512", _ => throw new InvalidOperationException("Unsupported EC key size.") });
            }
            else
            {
                var rsa = RSA.Create();
                rsa.ImportFromPem(pem);
                if (rsa.KeySize < 2048)
                {
                    throw new InvalidOperationException("The Sangam client key must be RSA 2048 bits or more, or ECDSA.");
                }

                (_key, _alg) = (rsa, "RS256");
            }
        }
        else if (string.IsNullOrEmpty(_options.ClientSecret))
        {
            throw new InvalidOperationException("Set Sangam:PrivateKeyPath (preferred) or Sangam:ClientSecret.");
        }
    }

    public string Method => _key is null ? "client_secret_basic" : "private_key_jwt";

    public void Apply(HttpRequestMessage request, IDictionary<string, string> form)
    {
        if (_key is null)
        {
            // RFC 6749 §2.3.1: form-urlencode id and secret before Basic.
            var pair = Uri.EscapeDataString(_options.ClientId) + ":" + Uri.EscapeDataString(_options.ClientSecret!);
            request.Headers.Authorization = new AuthenticationHeaderValue("Basic", Convert.ToBase64String(Encoding.UTF8.GetBytes(pair)));
            return;
        }

        form["client_id"] = _options.ClientId;
        form["client_assertion_type"] = AssertionType;
        form["client_assertion"] = CreateAssertion();
    }

    public string CreateAssertion()
    {
        var now = _time.GetUtcNow().ToUnixTimeSeconds();
        var header = new JsonObject { ["alg"] = _alg, ["typ"] = "client-authentication+jwt" };
        if (!string.IsNullOrEmpty(_options.PrivateKeyId))
        {
            header["kid"] = _options.PrivateKeyId;
        }

        var payload = new JsonObject
        {
            ["iss"] = _options.ClientId,
            ["sub"] = _options.ClientId,
            ["aud"] = _options.Issuer,
            ["jti"] = AcmeJws.Base64Url(RandomNumberGenerator.GetBytes(24)),
            ["iat"] = now,
            ["nbf"] = now,
            ["exp"] = now + 120,
        };
        return Jwt.Create(header, payload, input => _key switch
        {
            ECDsa ec => ec.SignData(input, _alg switch { "ES384" => HashAlgorithmName.SHA384, "ES512" => HashAlgorithmName.SHA512, _ => HashAlgorithmName.SHA256 },
                DSASignatureFormat.IeeeP1363FixedFieldConcatenation),
            RSA rsa => rsa.SignData(input, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1),
            _ => throw new InvalidOperationException(),
        });
    }

    private static bool TryEc(string pem, out ECDsa? ec)
    {
        ec = ECDsa.Create();
        try
        {
            ec.ImportFromPem(pem);
            return true;
        }
        catch (Exception ex) when (ex is CryptographicException or ArgumentException)
        {
            ec.Dispose();
            ec = null;
            return false;
        }
    }

    public void Dispose() => _key?.Dispose();
}
