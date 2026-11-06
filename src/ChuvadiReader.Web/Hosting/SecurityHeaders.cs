namespace ChuvadiReader.Web.Hosting;

/// <summary>Response headers on every response. The content policy allows only the portal's own
/// scripts, styles, fonts and images; inline styles are allowed because the Ui sets
/// <c>style</c> attributes, and fonts may be <c>data:</c> URLs because chuvadi-pdf's SVG pages embed
/// their fonts that way. Framing is limited to the portal itself (the hidden print frame).</summary>
public static class SecurityHeaders
{
    public const string ContentSecurityPolicy =
        "default-src 'self'; " +
        "script-src 'self'; " +
        "style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: blob:; " +
        "font-src 'self' data:; " +
        "connect-src 'self'; " +
        "frame-src 'self'; " +
        "frame-ancestors 'self'; " +
        "object-src 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'";

    public static IApplicationBuilder UsePortalSecurityHeaders(this IApplicationBuilder app, bool hsts)
        => app.Use(async (context, next) =>
        {
            var h = context.Response.Headers;
            h.ContentSecurityPolicy = ContentSecurityPolicy;
            h.XContentTypeOptions = "nosniff";
            h.XFrameOptions = "SAMEORIGIN";
            h["Referrer-Policy"] = "no-referrer";
            h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()";
            h["Cross-Origin-Opener-Policy"] = "same-origin";
            h["Cross-Origin-Resource-Policy"] = "same-origin";
            if (hsts && context.Request.IsHttps)
            {
                h.StrictTransportSecurity = "max-age=31536000; includeSubDomains";
            }

            await next(context).ConfigureAwait(false);
        });
}
