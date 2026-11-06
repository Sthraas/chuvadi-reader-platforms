using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// The folder-safe key for a signed-in person. Sangam's <c>sub</c> is our own pairwise id for the
/// person (ADR-0017), so it is what storage is keyed on — never the e-mail. The key is a hash so
/// no claim value ever reaches a file path.
/// </summary>
public static class UserKey
{
    /// <summary>Returns the key, or null when the principal has no subject (not signed in).</summary>
    public static string? From(ClaimsPrincipal? user)
    {
        if (user?.Identity?.IsAuthenticated != true)
        {
            return null;
        }

        var sub = user.FindFirst("sub")?.Value ?? user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(sub))
        {
            return null;
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes("chuvadi-portal-user:" + sub));
        return Convert.ToHexStringLower(hash.AsSpan(0, 16));
    }
}
