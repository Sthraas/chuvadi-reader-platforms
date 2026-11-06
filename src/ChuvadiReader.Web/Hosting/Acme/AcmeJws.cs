using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ChuvadiReader.Web.Hosting.Acme;

/// <summary>
/// The JSON Web Signature pieces ACME needs (RFC 8555 §6.2, RFC 7515, RFC 7518, RFC 7638), with an
/// ECDSA P-256 account key and ES256 only. BCL cryptography; no other code.
/// </summary>
public static class AcmeJws
{
    public static string Base64Url(ReadOnlySpan<byte> data)
        => Convert.ToBase64String(data).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    public static string Base64Url(string text) => Base64Url(Encoding.UTF8.GetBytes(text));

    public static byte[] FromBase64Url(string text)
    {
        var s = text.Replace('-', '+').Replace('_', '/');
        s += (s.Length % 4) switch { 2 => "==", 3 => "=", 0 => string.Empty, _ => throw new FormatException("Not base64url.") };
        return Convert.FromBase64String(s);
    }

    /// <summary>The public JWK of a P-256 key, members in the order RFC 7638 needs for the thumbprint.</summary>
    public static JsonObject Jwk(ECDsa key)
    {
        var p = key.ExportParameters(includePrivateParameters: false);
        if (p.Curve.Oid.Value != ECCurve.NamedCurves.nistP256.Oid.Value)
        {
            throw new ArgumentException("The ACME account key must be ECDSA P-256.", nameof(key));
        }

        return new JsonObject
        {
            ["crv"] = "P-256",
            ["kty"] = "EC",
            ["x"] = Base64Url(p.Q.X),
            ["y"] = Base64Url(p.Q.Y),
        };
    }

    /// <summary>RFC 7638 thumbprint: SHA-256 of the required members, lexicographic, no whitespace.</summary>
    public static string Thumbprint(ECDsa key)
    {
        var jwk = Jwk(key);
        var canonical = $"{{\"crv\":\"P-256\",\"kty\":\"EC\",\"x\":\"{jwk["x"]}\",\"y\":\"{jwk["y"]}\"}}";
        return Base64Url(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)));
    }

    /// <summary>The http-01 key authorization for a challenge token (RFC 8555 §8.1).</summary>
    public static string KeyAuthorization(string token, ECDsa accountKey) => token + "." + Thumbprint(accountKey);

    /// <summary>
    /// A flattened JWS for an ACME request. <paramref name="kid"/> is the account URL; when null the
    /// public key is embedded as <c>jwk</c> (only for newAccount). A null payload is POST-as-GET
    /// (empty payload, RFC 8555 §6.3).
    /// </summary>
    public static string Sign(ECDsa key, string url, string nonce, string? kid, JsonNode? payload)
    {
        var header = new JsonObject
        {
            ["alg"] = "ES256",
            ["nonce"] = nonce,
            ["url"] = url,
        };
        if (kid is null)
        {
            header["jwk"] = Jwk(key);
        }
        else
        {
            header["kid"] = kid;
        }

        var protectedB64 = Base64Url(header.ToJsonString());
        var payloadB64 = payload is null ? string.Empty : Base64Url(payload.ToJsonString());
        // .NET's ECDsa.SignData returns IEEE P1363 (r || s), which is what JWS ES256 uses.
        var signature = key.SignData(Encoding.ASCII.GetBytes(protectedB64 + "." + payloadB64), HashAlgorithmName.SHA256,
            DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        return new JsonObject
        {
            ["protected"] = protectedB64,
            ["payload"] = payloadB64,
            ["signature"] = Base64Url(signature),
        }.ToJsonString();
    }

    /// <summary>Reads a flattened JWS back (used by the tests' ACME server).</summary>
    public static (JsonObject Header, string Payload, bool SignatureValid) Verify(string jws, ECDsa? key)
    {
        var o = JsonNode.Parse(jws)!.AsObject();
        var protectedB64 = (string)o["protected"]!;
        var payloadB64 = (string)o["payload"]!;
        var header = JsonNode.Parse(FromBase64Url(protectedB64))!.AsObject();
        var payload = payloadB64.Length == 0 ? string.Empty : Encoding.UTF8.GetString(FromBase64Url(payloadB64));
        if (key is null)
        {
            key = ImportJwk(header["jwk"]!.AsObject());
        }

        var ok = key.VerifyData(Encoding.ASCII.GetBytes(protectedB64 + "." + payloadB64), FromBase64Url((string)o["signature"]!),
            HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        return (header, payload, ok);
    }

    public static ECDsa ImportJwk(JsonObject jwk)
    {
        if ((string?)jwk["kty"] != "EC" || (string?)jwk["crv"] != "P-256")
        {
            throw new CryptographicException("Only EC P-256 keys are accepted.");
        }

        return ECDsa.Create(new ECParameters
        {
            Curve = ECCurve.NamedCurves.nistP256,
            Q = new ECPoint { X = FromBase64Url((string)jwk["x"]!), Y = FromBase64Url((string)jwk["y"]!) },
        });
    }

    internal static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
}
