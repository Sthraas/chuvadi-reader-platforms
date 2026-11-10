using System.Security.Claims;
using ChuvadiReader.Platform;
using Microsoft.AspNetCore.Components.Authorization;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// D-158: who owns the page images drawn in this connection: the signed-in person and their sign-in session
/// (Sangam's <c>sid</c>). Computed only from the server's own sign-in (the circuit's authentication state, or
/// the request's cookie on the image endpoint), never from anything the browser sends, so the circuit that
/// draws a page and the request that fetches it compute the same value for the same person and session.
/// Another person, or the same person's other sign-in, gets a different owner and so a 404. Scoped (per
/// connection).
/// </summary>
public sealed class PortalPageImageOwner : IPageImageOwner
{
    private readonly AuthenticationStateProvider _auth;
    private string? _current;

    public PortalPageImageOwner(AuthenticationStateProvider auth) => _auth = auth;

    public string Current => _current ??= Resolve();

    /// <summary>The owner for <paramref name="user"/>, or null when nobody is signed in.</summary>
    public static string? For(ClaimsPrincipal? user)
        => Files.UserKey.From(user) is { } key ? key + "/" + (user!.FindFirst("sid")?.Value ?? "-") : null;

    private string Resolve()
    {
        var state = _auth.GetAuthenticationStateAsync();
        // Interactive Server sets the state when the circuit starts, so it is already there when pages draw.
        var user = state.IsCompletedSuccessfully ? state.Result.User : null;
        // Nobody signed in: an owner no request can ever present, so nothing drawn here could be fetched.
        return For(user) ?? "nobody/" + Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(16));
    }
}
