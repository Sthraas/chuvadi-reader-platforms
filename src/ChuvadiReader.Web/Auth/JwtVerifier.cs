using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// Checks the tokens Sangam sends the portal: ID tokens (OpenID Connect Core §3.1.3.7) and back-channel
/// logout tokens (OpenID Connect Back-Channel Logout §2.6). Signature against Sangam's published keys
/// with an algorithm allow-list (never <c>none</c>, never HMAC), issuer, audience, times.
/// </summary>
public sealed class JwtVerifier
{
    public const string LogoutEvent = "http://schemas.openid.net/event/backchannel-logout";

    private static readonly HashSet<string> AllowedAlgorithms = ["RS256", "RS384", "RS512", "PS256", "ES256", "ES384", "ES512"];

    private readonly SangamMetadata _metadata;
    private readonly SangamOptions _options;
    private readonly TimeProvider _time;

    public JwtVerifier(SangamMetadata metadata, IOptions<SangamOptions> options, TimeProvider time)
    {
        _metadata = metadata;
        _options = options.Value;
        _time = time;
    }

    /// <summary>Checks an ID token from the token endpoint for the sign-in that sent <paramref name="nonce"/>.</summary>
    public async Task<Jwt> VerifyIdTokenAsync(string token, string nonce, CancellationToken ct)
    {
        var jwt = await VerifyCommonAsync(token, ct).ConfigureAwait(false);
        RequireTime(jwt, "exp", mustBeFuture: true);
        RequireTime(jwt, "iat", mustBeFuture: false);
        if (jwt.Claim("nonce") != nonce)
        {
            throw new SecurityTokenException("The ID token's nonce doesn't match this sign-in.");
        }

        if (string.IsNullOrEmpty(jwt.Claim("sub")))
        {
            throw new SecurityTokenException("The ID token has no subject.");
        }

        return jwt;
    }

    /// <summary>Checks a back-channel logout token.</summary>
    public async Task<Jwt> VerifyLogoutTokenAsync(string token, CancellationToken ct)
    {
        var jwt = await VerifyCommonAsync(token, ct).ConfigureAwait(false);
        if (jwt.Typ is not null && !string.Equals(jwt.Typ, "logout+jwt", StringComparison.OrdinalIgnoreCase))
        {
            throw new SecurityTokenException("Not a logout token.");
        }

        RequireTime(jwt, "iat", mustBeFuture: false);
        if (jwt.NumericClaim("exp") is not null)
        {
            RequireTime(jwt, "exp", mustBeFuture: true);
        }

        if (jwt.Payload["events"]?[LogoutEvent] is not System.Text.Json.Nodes.JsonObject)
        {
            throw new SecurityTokenException("The logout token has no logout event.");
        }

        if (jwt.Payload["nonce"] is not null)
        {
            throw new SecurityTokenException("A logout token must not carry a nonce.");
        }

        if (string.IsNullOrEmpty(jwt.Claim("jti")))
        {
            throw new SecurityTokenException("The logout token has no jti.");
        }

        if (string.IsNullOrEmpty(jwt.Claim("sub")) && string.IsNullOrEmpty(jwt.Claim("sid")))
        {
            throw new SecurityTokenException("The logout token names neither a person nor a session.");
        }

        return jwt;
    }

    private async Task<Jwt> VerifyCommonAsync(string token, CancellationToken ct)
    {
        var jwt = Jwt.Parse(token);
        if (jwt.Alg is null || !AllowedAlgorithms.Contains(jwt.Alg))
        {
            throw new SecurityTokenException($"Algorithm {jwt.Alg} isn't accepted.");
        }

        if (jwt.Header["crit"] is not null)
        {
            throw new SecurityTokenException("Critical header parameters aren't supported.");
        }

        var keys = await _metadata.KeysForAsync(jwt.Kid, ct).ConfigureAwait(false);
        if (!keys.Any(k => k.Verify(jwt.Alg, jwt.SigningInput, jwt.Signature)))
        {
            throw new SecurityTokenException("The token's signature isn't from Sangam.");
        }

        if (jwt.Claim("iss") != _options.Issuer)
        {
            throw new SecurityTokenException("The token isn't from the configured Sangam issuer.");
        }

        var aud = jwt.Audiences;
        if (!aud.Contains(_options.ClientId, StringComparer.Ordinal))
        {
            throw new SecurityTokenException("The token isn't for this portal.");
        }

        if (aud.Count > 1 && jwt.Claim("azp") is { } azp && azp != _options.ClientId)
        {
            throw new SecurityTokenException("The token was issued to another party.");
        }

        if (jwt.NumericClaim("nbf") is long nbf && DateTimeOffset.FromUnixTimeSeconds(nbf) > _time.GetUtcNow() + _options.ClockSkew)
        {
            throw new SecurityTokenException("The token isn't valid yet.");
        }

        return jwt;
    }

    private void RequireTime(Jwt jwt, string claim, bool mustBeFuture)
    {
        var value = jwt.NumericClaim(claim) ?? throw new SecurityTokenException($"The token has no {claim}.");
        var at = DateTimeOffset.FromUnixTimeSeconds(value);
        var now = _time.GetUtcNow();
        if (mustBeFuture ? at < now - _options.ClockSkew : at > now + _options.ClockSkew)
        {
            throw new SecurityTokenException(mustBeFuture ? "The token has expired." : $"The token's {claim} is in the future.");
        }
    }
}
