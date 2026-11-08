namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// WT-07: the Blazor circuit (<c>/_blazor</c>) answers only the portal's own pages. A browser always sends
/// <c>Origin</c> when it opens the circuit (the negotiate POST and the WebSocket upgrade), so those must carry
/// the portal's origin. Any other circuit request that names a foreign origin is refused too. The
/// <c>SameSite=Lax</c> cookie already stops most cross-site use, but a sibling sub-domain counts as same-site.
/// </summary>
public static class CircuitOrigin
{
    public const string CircuitPath = "/_blazor";

    public static IApplicationBuilder UseCircuitOriginCheck(this IApplicationBuilder app)
        => app.Use((http, next) =>
        {
            if (http.Request.Path.StartsWithSegments(CircuitPath) && !Allowed(http))
            {
                http.Response.StatusCode = StatusCodes.Status403Forbidden;
                return Task.CompletedTask;
            }

            return next(http);
        });

    /// <summary>The beacon a closing page sends to end its circuit at once.</summary>
    public const string DisconnectPath = CircuitPath + "/disconnect";

    internal static bool Allowed(HttpContext http)
    {
        var origin = http.Request.Headers.Origin.ToString();
        if (http.Request.Path.StartsWithSegments(DisconnectPath) && origin is "" or "null")
        {
            // Safari sends the closing page's beacon without a usable Origin. It can only end a circuit
            // whose secret id it carries, so it is harmless; a foreign Origin is still refused below.
            return true;
        }

        var opening = HttpMethods.IsPost(http.Request.Method) || http.WebSockets.IsWebSocketRequest
            || http.Request.Headers.Upgrade.Count > 0;
        if (origin.Length == 0)
        {
            return !opening; // a long-polling GET from the portal's own page may carry no Origin
        }

        return Files.FileEndpoints.SameOrigin(http);
    }
}
