using System.Net;
using ChuvadiReader.Ui.Components.Legal;
using ChuvadiReader.Ui.Components.Platform.Portal;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Web;

namespace ChuvadiReader.Web.Auth;

/// <summary>
/// Ui pages a visitor reads before signing in, rendered to plain HTML on the server: no circuit is
/// needed (in gateway mode there is no worker yet). Each is the Ui's own component; a small script of
/// ours wires its one interaction.
/// <list type="bullet">
/// <item><c>/signin</c>: the sign-in page (12a, <see cref="PortalSignIn"/>).</item>
/// <item><c>/terms</c>, <c>/privacy</c>, <c>/licence</c>: the portal's legal documents (the Foundation's
/// <see cref="LicencesSection"/>: terms of use, privacy, cookies, third-party notices; drafts, marked so).
/// The sign-in page's "Terms of use" opens <c>/terms</c>; <c>/privacy</c> is the address a privacy policy
/// link needs; <c>/licence?part=cookies|notices</c> opens the others (D-86).</item>
/// </list>
/// </summary>
public static class StaticPages
{
    public const string SignInStartPath = "/signin/sangam";
    public const string LicencePath = "/licence";
    public const string TermsPath = "/terms";
    public const string PrivacyPath = "/privacy";

    /// <summary>The legal pages' addresses, readable before sign-in.</summary>
    public static readonly string[] LegalPaths = [TermsPath, PrivacyPath, LicencePath];

    /// <summary>Where each portal document lives (the page's switch becomes links to these).</summary>
    private static string AddressOf(string id) => id switch
    {
        "terms" => TermsPath,
        "privacy" => PrivacyPath,
        _ => LicencePath + "?part=" + Uri.EscapeDataString(id),
    };

    /// <summary>The sign-in page, with an optional reason the last attempt failed.</summary>
    public static async Task<IResult> SignInAsync(HttpContext http, string? error = null, int status = StatusCodes.Status200OK)
    {
        var card = await RenderAsync<PortalSignIn>(http, new Dictionary<string, object?>
        {
            [nameof(PortalSignIn.Error)] = error,
            [nameof(PortalSignIn.ShowSangamId)] = PortalSignIn.ShowSangamIdDefault,
        }).ConfigureAwait(false);
        var returnUrl = SangamSignIn.SafeReturnUrl(http.Request.Query["returnUrl"]);
        var start = SignInStartPath + "?returnUrl=" + Uri.EscapeDataString(returnUrl);
        return Page(http, "Sign in · Chuvadi", card, "js/signin.js", ("data-chvd-signin", start), status);
    }

    /// <summary>A legal page: <c>/terms</c>, <c>/privacy</c>, or <c>/licence?part=</c> one of the portal's documents.</summary>
    public static async Task<IResult> LegalAsync(HttpContext http)
    {
        var docs = LegalTexts.PortalDocs;
        var route = http.Request.Path.Value?.TrimEnd('/') ?? LicencePath;
        string? asked = http.Request.Query["part"];
        var part = route switch
        {
            TermsPath => "terms",
            PrivacyPath => "privacy",
            _ => docs.Any(d => d.Id == asked) ? asked! : docs[0].Id,
        };
        var title = route switch
        {
            TermsPath => "Terms of use",
            PrivacyPath => "Privacy",
            _ => "Licences",
        };
        var section = await RenderAsync<LicencesSection>(http, new Dictionary<string, object?>
        {
            [nameof(LicencesSection.Part)] = part,
            [nameof(LicencesSection.Title)] = title,
        }).ConfigureAwait(false);
        var links = string.Join(" ", docs.Select(d => AddressOf(d.Id)));
        return Page(http, title + " · Chuvadi", "<div class=\"licence-page chvd-static-licence\">" + section + "</div>", "js/legal.js",
            ("data-chvd-docs", links), StatusCodes.Status200OK);
    }

    /// <summary>Renders a Ui component with its own small set of services: the request's own would
    /// include Blazor Server's circuit-only services in single mode, which can't run outside a circuit.</summary>
    private static async Task<string> RenderAsync<TComponent>(HttpContext http, Dictionary<string, object?> parameters)
        where TComponent : IComponent
    {
        var links = http.RequestServices.GetRequiredService<PortalLinks>();
        await using var services = new ServiceCollection()
            .AddSingleton(links)
            .AddSingleton<ChuvadiReader.Platform.IPlatformInfo>(new ChuvadiReader.Web.Platform.WebPlatformInfo()) // the portal's documents
            .BuildServiceProvider();
        await using var renderer = new HtmlRenderer(services, http.RequestServices.GetRequiredService<ILoggerFactory>());
        return await renderer.Dispatcher.InvokeAsync(async () =>
        {
            var output = await renderer.RenderComponentAsync<TComponent>(ParameterView.FromDictionary(parameters)).ConfigureAwait(false);
            return output.ToHtmlString();
        }).ConfigureAwait(false);
    }

    /// <summary>The same head as the portal's own page (Ui stylesheets and fonts), no Blazor runtime.</summary>
    private static IResult Page(HttpContext http, string title, string body, string script, (string Name, string Value) data, int status)
    {
        http.Response.Headers.CacheControl = "no-store";
        var html =
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\" />" +
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /><base href=\"/\" />" +
            "<title>" + WebUtility.HtmlEncode(title) + "</title>" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/fonts/google/fonts.css\" />" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/lipi-sans/lipi-sans.css\" />" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/tokens.css\" />" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/app.css\" />" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/shell.css\" />" +
            "<link rel=\"stylesheet\" href=\"_content/ChuvadiReader.Ui/css/prefs.css\" />" +
            "<link rel=\"stylesheet\" href=\"ChuvadiReader.Web.styles.css\" />" +
            "<link rel=\"stylesheet\" href=\"css/portal.css\" />" +
            "</head><body " + data.Name + "=\"" + WebUtility.HtmlEncode(data.Value) + "\">" +
            body +
            "<script src=\"" + script + "\"></script>" +
            "</body></html>";
        return Results.Content(html, "text/html; charset=utf-8", statusCode: status);
    }
}
