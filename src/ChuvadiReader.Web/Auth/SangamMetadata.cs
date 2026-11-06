using System.Text.Json.Nodes;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Auth;

/// <summary>Sign-in settings (section <c>Sangam</c>). Issuer, client id and addresses are configuration (Arun, 6 Nov).</summary>
public sealed class SangamOptions
{
    public const string Section = "Sangam";

    /// <summary>Sangam's issuer, e.g. <c>https://id.sangamid.in/</c> (a local Sangam in tests: <c>http://localhost:5100/</c>).</summary>
    public string Authority { get; set; } = string.Empty;

    public string ClientId { get; set; } = string.Empty;

    /// <summary>Client secret (client_secret_basic). Use either this or <see cref="PrivateKeyPath"/>.</summary>
    public string? ClientSecret { get; set; }

    /// <summary>PEM private key (P-256 or RSA-3072) for <c>private_key_jwt</c>; the public half is registered with Sangam.</summary>
    public string? PrivateKeyPath { get; set; }

    /// <summary>Key id registered with Sangam for <see cref="PrivateKeyPath"/>.</summary>
    public string? PrivateKeyId { get; set; }

    /// <summary>What the portal asks for: who the person is, nothing more.</summary>
    public string Scope { get; set; } = "openid profile email org.current";

    /// <summary>Optional Sangam screen languages (<c>en</c>, <c>hi</c>, <c>ml</c>).</summary>
    public string? UiLocales { get; set; }

    public string CallbackPath { get; set; } = "/signin-sangam";

    public string SignedOutCallbackPath { get; set; } = "/signout-sangam";

    public string BackChannelLogoutPath { get; set; } = "/backchannel-logout";

    /// <summary>Allowed clock difference with Sangam.</summary>
    public TimeSpan ClockSkew { get; set; } = TimeSpan.FromMinutes(2);

    /// <summary>How long a started sign-in may take before it must be restarted.</summary>
    public TimeSpan SignInTimeLimit { get; set; } = TimeSpan.FromMinutes(10);

    /// <summary>Absolute portal session lifetime (D-30).</summary>
    public TimeSpan AbsoluteSessionLifetime { get; set; } = TimeSpan.FromHours(8);

    public bool IsConfigured => !string.IsNullOrWhiteSpace(Authority) && !string.IsNullOrWhiteSpace(ClientId);

    public string Issuer => Authority.EndsWith('/') ? Authority : Authority + "/";
}

/// <summary>
/// Sangam's discovery document and signing keys, fetched on first use and cached. Keys are fetched
/// again when a token names a key we don't have (Sangam rotates keys), at most once a minute so a
/// stream of bad tokens can't hammer Sangam. Singleton.
/// </summary>
public sealed class SangamMetadata
{
    private static readonly TimeSpan MinRefresh = TimeSpan.FromMinutes(1);
    private static readonly TimeSpan MaxAge = TimeSpan.FromHours(24);

    private readonly SangamOptions _options;
    private readonly Hosting.Acme.IHttpClientFactoryLite _http;
    private readonly TimeProvider _time;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private JsonObject? _discovery;
    private IReadOnlyList<JsonWebKey> _keys = [];
    private DateTimeOffset _keysFetched = DateTimeOffset.MinValue;

    public SangamMetadata(IOptions<SangamOptions> options, Hosting.Acme.IHttpClientFactoryLite http, TimeProvider time)
    {
        _options = options.Value;
        _http = http;
        _time = time;
    }

    public async Task<JsonObject> DiscoveryAsync(CancellationToken ct)
    {
        if (_discovery is not null)
        {
            return _discovery;
        }

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_discovery is null)
            {
                using var client = _http.Create();
                var text = await client.GetStringAsync(new Uri(new Uri(_options.Issuer), ".well-known/openid-configuration"), ct).ConfigureAwait(false);
                var d = JsonNode.Parse(text) as JsonObject ?? throw new SecurityTokenException("Sangam's discovery document isn't JSON.");
                if ((string?)d["issuer"] != _options.Issuer)
                {
                    throw new SecurityTokenException($"Sangam's discovery issuer {(string?)d["issuer"]} isn't the configured {_options.Issuer}.");
                }

                foreach (var name in new[] { "authorization_endpoint", "token_endpoint", "jwks_uri" })
                {
                    if (string.IsNullOrEmpty((string?)d[name]))
                    {
                        throw new SecurityTokenException($"Sangam's discovery document has no {name}.");
                    }
                }

                _discovery = d;
            }

            return _discovery;
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task<string> EndpointAsync(string name, CancellationToken ct)
        => (string?)(await DiscoveryAsync(ct).ConfigureAwait(false))[name] ?? throw new SecurityTokenException($"Sangam has no {name}.");

    public async Task<string?> OptionalEndpointAsync(string name, CancellationToken ct)
        => (string?)(await DiscoveryAsync(ct).ConfigureAwait(false))[name];

    /// <summary>The key for <paramref name="kid"/>, refetching the key set if it's unknown.</summary>
    public async Task<IReadOnlyList<JsonWebKey>> KeysForAsync(string? kid, CancellationToken ct)
    {
        var now = _time.GetUtcNow();
        var known = Match(_keys, kid);
        if (known.Count > 0 && now - _keysFetched < MaxAge)
        {
            return known;
        }

        if (now - _keysFetched < MinRefresh && _keys.Count > 0)
        {
            return known;
        }

        // Outside the gate: DiscoveryAsync takes the same (non-reentrant) gate.
        var uri = await EndpointAsync("jwks_uri", ct).ConfigureAwait(false);
        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_time.GetUtcNow() - _keysFetched >= MinRefresh || _keys.Count == 0)
            {
                using var client = _http.Create();
                var set = JsonNode.Parse(await client.GetStringAsync(uri, ct).ConfigureAwait(false)) as JsonObject
                    ?? throw new SecurityTokenException("Sangam's key set isn't JSON.");
                _keys = (set["keys"] as JsonArray ?? []).OfType<JsonObject>().Select(JsonWebKey.From).Where(k => k is not null).Cast<JsonWebKey>().ToList();
                _keysFetched = _time.GetUtcNow();
            }

            return Match(_keys, kid);
        }
        finally
        {
            _gate.Release();
        }
    }

    private static IReadOnlyList<JsonWebKey> Match(IReadOnlyList<JsonWebKey> keys, string? kid)
        => kid is null ? keys : keys.Where(k => k.Kid == kid).ToList();
}
