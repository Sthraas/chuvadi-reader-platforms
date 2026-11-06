using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using ChuvadiReader.Web.Hosting.Acme;

namespace ChuvadiReader.Web.Auth;

/// <summary>A compact JWS (RFC 7515) read apart; nothing is trusted until <see cref="JwtVerifier"/> has checked it.</summary>
public sealed class Jwt
{
    private Jwt(JsonObject header, JsonObject payload, byte[] signingInput, byte[] signature)
    {
        Header = header;
        Payload = payload;
        SigningInput = signingInput;
        Signature = signature;
    }

    public JsonObject Header { get; }
    public JsonObject Payload { get; }
    public byte[] SigningInput { get; }
    public byte[] Signature { get; }

    public string? Alg => (string?)Header["alg"];
    public string? Kid => (string?)Header["kid"];
    public string? Typ => (string?)Header["typ"];

    public string? Claim(string name) => Payload[name] is JsonValue v && v.TryGetValue<string>(out var s) ? s : null;

    public long? NumericClaim(string name) => Payload[name] is JsonValue v && v.TryGetValue<long>(out var l) ? l
        : Payload[name] is JsonValue d && d.TryGetValue<double>(out var dd) ? (long)dd : null;

    /// <summary>The <c>aud</c> claim as a list (string or array, RFC 7519 §4.1.3).</summary>
    public IReadOnlyList<string> Audiences => Payload["aud"] switch
    {
        JsonValue v when v.TryGetValue<string>(out var s) => [s],
        JsonArray a => a.Select(x => (string?)x).Where(x => x is not null).Cast<string>().ToList(),
        _ => [],
    };

    /// <summary>Splits a compact JWS. Refuses JWE (5 parts), unsigned tokens and oversize input.</summary>
    public static Jwt Parse(string token)
    {
        if (string.IsNullOrEmpty(token) || token.Length > 16 * 1024)
        {
            throw new SecurityTokenException("The token is empty or too large.");
        }

        var parts = token.Split('.');
        if (parts.Length != 3)
        {
            throw new SecurityTokenException("Not a signed JWT.");
        }

        try
        {
            var header = JsonNode.Parse(AcmeJws.FromBase64Url(parts[0])) as JsonObject ?? throw new SecurityTokenException("Bad JWT header.");
            var payload = JsonNode.Parse(AcmeJws.FromBase64Url(parts[1])) as JsonObject ?? throw new SecurityTokenException("Bad JWT payload.");
            var signature = AcmeJws.FromBase64Url(parts[2]);
            return new Jwt(header, payload, Encoding.ASCII.GetBytes(parts[0] + "." + parts[1]), signature);
        }
        catch (FormatException ex)
        {
            throw new SecurityTokenException("Bad JWT encoding.", ex);
        }
        catch (System.Text.Json.JsonException ex)
        {
            throw new SecurityTokenException("Bad JWT JSON.", ex);
        }
    }

    /// <summary>Makes a compact JWS (client assertions; tests).</summary>
    public static string Create(JsonObject header, JsonObject payload, Func<byte[], byte[]> sign)
    {
        var input = AcmeJws.Base64Url(header.ToJsonString()) + "." + AcmeJws.Base64Url(payload.ToJsonString());
        return input + "." + AcmeJws.Base64Url(sign(Encoding.ASCII.GetBytes(input)));
    }
}

public sealed class SecurityTokenException : Exception
{
    public SecurityTokenException(string message)
        : base(message)
    {
    }

    public SecurityTokenException(string message, Exception inner)
        : base(message, inner)
    {
    }
}

/// <summary>A public key from a JWKS (RFC 7517), RSA or EC.</summary>
public sealed class JsonWebKey
{
    private JsonWebKey(string? kid, string kty, string? alg, string? use, RSA? rsa, ECDsa? ec)
    {
        Kid = kid;
        Kty = kty;
        Alg = alg;
        Use = use;
        Rsa = rsa;
        Ec = ec;
    }

    public string? Kid { get; }
    public string Kty { get; }
    public string? Alg { get; }
    public string? Use { get; }
    public RSA? Rsa { get; }
    public ECDsa? Ec { get; }

    /// <summary>Reads one key; null for key types or uses we don't accept (they are skipped, not fatal).</summary>
    public static JsonWebKey? From(JsonObject k)
    {
        var kty = (string?)k["kty"];
        var use = (string?)k["use"];
        if (use is not null && use != "sig")
        {
            return null;
        }

        if (kty == "RSA")
        {
            var n = AcmeJws.FromBase64Url((string)k["n"]!);
            if (n.Length < 256)
            {
                return null; // under 2048 bits
            }

            var rsa = RSA.Create();
            rsa.ImportParameters(new RSAParameters { Modulus = n, Exponent = AcmeJws.FromBase64Url((string)k["e"]!) });
            return new JsonWebKey((string?)k["kid"], kty, (string?)k["alg"], use, rsa, null);
        }

        if (kty == "EC")
        {
            var curve = (string?)k["crv"] switch
            {
                "P-256" => ECCurve.NamedCurves.nistP256,
                "P-384" => ECCurve.NamedCurves.nistP384,
                "P-521" => ECCurve.NamedCurves.nistP521,
                _ => (ECCurve?)null,
            };
            if (curve is null)
            {
                return null;
            }

            var ec = ECDsa.Create(new ECParameters
            {
                Curve = curve.Value,
                Q = new ECPoint { X = AcmeJws.FromBase64Url((string)k["x"]!), Y = AcmeJws.FromBase64Url((string)k["y"]!) },
            });
            return new JsonWebKey((string?)k["kid"], kty, (string?)k["alg"], use, null, ec);
        }

        return null;
    }

    /// <summary>Checks a signature for one of the algorithms we accept. Anything else is false.</summary>
    public bool Verify(string alg, byte[] input, byte[] signature)
    {
        if (Alg is not null && Alg != alg)
        {
            return false;
        }

        return alg switch
        {
            "RS256" => Rsa?.VerifyData(input, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1) == true,
            "RS384" => Rsa?.VerifyData(input, signature, HashAlgorithmName.SHA384, RSASignaturePadding.Pkcs1) == true,
            "RS512" => Rsa?.VerifyData(input, signature, HashAlgorithmName.SHA512, RSASignaturePadding.Pkcs1) == true,
            "PS256" => Rsa?.VerifyData(input, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pss) == true,
            "ES256" => Ec?.KeySize == 256 && Ec.VerifyData(input, signature, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation),
            "ES384" => Ec?.KeySize == 384 && Ec.VerifyData(input, signature, HashAlgorithmName.SHA384, DSASignatureFormat.IeeeP1363FixedFieldConcatenation),
            "ES512" => Ec?.KeySize == 521 && Ec.VerifyData(input, signature, HashAlgorithmName.SHA512, DSASignatureFormat.IeeeP1363FixedFieldConcatenation),
            _ => false,
        };
    }
}
