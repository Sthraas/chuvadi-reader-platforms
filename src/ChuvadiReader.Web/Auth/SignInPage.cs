using System.Net;
using ChuvadiReader.Ui.Components.Platform.Portal;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Web;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// The portal's sign-in page (design 12a): the Web portal UI chat's <see cref="PortalSignIn"/>, rendered
/// to plain HTML on the server. No circuit is needed before sign-in: in gateway mode there is no worker
/// yet. "Continue with Sangam" is wired by <c>js/signin.js</c> to <c>/signin/sangam</c>, which leaves for
/// Sangam with the return address. The Sangam ID field stays off (U-9 a) until Sangam pre-fills
/// <c>login_hint</c>.
/// </summary>
public static class SignInPage
{
    public const string StartPath = "/signin/sangam";

    public static async Task<IResult> RenderAsync(HttpContext http, string? error = null, int status = StatusCodes.Status200OK)
    {
        // Its own small set of services (only what the page injects): the request's own would include
        // Blazor Server's circuit-only services in single mode, which can't run outside a circuit.
        var links = http.RequestServices.GetRequiredService<PortalLinks>();
        await using var services = new ServiceCollection().AddSingleton(links).BuildServiceProvider();
        await using var renderer = new HtmlRenderer(services, http.RequestServices.GetRequiredService<ILoggerFactory>());
        var card = await renderer.Dispatcher.InvokeAsync(async () =>
        {
            var parameters = ParameterView.FromDictionary(new Dictionary<string, object?>
            {
                [nameof(PortalSignIn.Error)] = error,
                [nameof(PortalSignIn.ShowSangamId)] = PortalSignIn.ShowSangamIdDefault,
            });
            var output = await renderer.RenderComponentAsync<PortalSignIn>(parameters).ConfigureAwait(false);
            return output.ToHtmlString();
        }).ConfigureAwait(false);

        var returnUrl = SangamSignIn.SafeReturnUrl(http.Request.Query["returnUrl"]);
        http.Response.Headers.CacheControl = "no-store";
        return Results.Content(Document(card, returnUrl), "text/html; charset=utf-8", statusCode: status);
    }

    /// <summary>The same head as the portal's own page (Ui stylesheets, fonts, theme), no Blazor runtime.</summary>
    private static string Document(string card, string returnUrl) =>
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\" />" +
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /><base href=\"/\" />" +
        "<title>Sign in · Chuvadi</title>" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/fonts/google/fonts.css\" />" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/lipi-sans/lipi-sans.css\" />" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/tokens.css\" />" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/app.css\" />" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/shell.css\" />" +
        "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/prefs.css\" />" +
        "<link rel=\"stylesheet\" href=\"ChuvadiReader.Web.styles.css\" />" +
        "<link rel=\"stylesheet\" href=\"css/portal.css\" />" +
        "</head><body data-chvd-signin=\"" + WebUtility.HtmlEncode(StartPath + "?returnUrl=" + Uri.EscapeDataString(returnUrl)) + "\">" +
        card +
        "<script src=\"js/signin.js\"></script>" +
        "</body></html>";
}
