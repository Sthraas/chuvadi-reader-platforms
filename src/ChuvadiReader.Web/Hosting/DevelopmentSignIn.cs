using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Development and test only: signs every request in as a fixed local person, so the portal can be
/// run and tested before the Sangam client is wired. Registered only when the environment is
/// Development or Testing; <see cref="Program"/> refuses to start in any other environment without Sangam.
/// The person can be chosen per request with the <c>X-Dev-User</c> header (tests use it for isolation checks),
/// or with the <c>chvd-dev-user</c> cookie. Browser tests should use the cookie: a closing page's own
/// "disconnect" call (a beacon) carries cookies like the real sign-in, but not a test tool's extra headers, so
/// with only the header it reaches the default person's worker and the old connection is never ended (WT-22).
/// </summary>
public sealed class DevelopmentSignInHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public const string SchemeName = "Development";

    /// <summary>Development and test only: names the person, as the <c>X-Dev-User</c> header does.</summary>
    public const string CookieName = "chvd-dev-user";

    public DevelopmentSignInHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder)
        : base(options, logger, encoder)
    {
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var who = Request.Headers["X-Dev-User"].ToString();
        if (string.IsNullOrWhiteSpace(who))
        {
            who = Request.Cookies[CookieName] ?? string.Empty;
        }

        if (string.IsNullOrWhiteSpace(who) || who.Length > 64)
        {
            who = "dev-user";
        }

        var identity = new ClaimsIdentity(
        [
            new Claim("sub", who),
            new Claim("name", "Developer"),
        ], SchemeName, "name", "role");
        return Task.FromResult(AuthenticateResult.Success(new AuthenticationTicket(new ClaimsPrincipal(identity), SchemeName)));
    }
}

/// <summary>
/// Development and test only, when Sangam isn't configured: <c>/signout</c> ends the person's session (every
/// open tab leaves, its documents are closed, its files deleted, its worker stops) and shows the signed-out
/// page, as the real sign-out does. Without it a Development session could only end by expiry, and since a
/// session keeps its documents and its worker while it lasts (D-174), every test person stayed for 30 minutes.
/// </summary>
public static class DevelopmentSignOut
{
    public static IEndpointRouteBuilder MapDevelopmentSignOut(this IEndpointRouteBuilder app)
    {
        app.MapGet("/signout", async (HttpContext http, Auth.ITabControl tabs) =>
        {
            // As the real sign-out: a cross-site page can't sign someone out.
            if (http.Request.Headers["Sec-Fetch-Site"].ToString() is "cross-site")
            {
                return Results.StatusCode(StatusCodes.Status403Forbidden);
            }

            if (http.User.FindFirst("sub")?.Value is { } sub)
            {
                await tabs.EndAsync(sub, null).ConfigureAwait(false);
            }

            return Results.Redirect(Auth.SangamSignIn.SignedOutPath);
        });
        return app;
    }
}
