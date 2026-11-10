using ChuvadiReader.Web.Hosting;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// The HTTP side of file transfer: chunked uploads into a session folder, single-use downloads, and
/// the PDF handed to the browser for printing. Every endpoint needs a signed-in user and checks the ticket belongs to them;
/// state-changing requests must also come from the portal's own origin.
/// </summary>
public static class FileEndpoints
{
    public const string Prefix = "/portal";

    public sealed record BeginUpload(string? Name, long Size);

    /// <summary>The route a drawn page's image is fetched from (D-158): <c>/_chvd/pages/&lt;token&gt;.png</c>.</summary>
    public const string PageImagesRoute = "/" + ChuvadiReader.Core.Reader.PageImages.PathPrefix + "{file}";

    public static IEndpointRouteBuilder MapPortalFiles(this IEndpointRouteBuilder app)
    {
        // D-158: drawn pages by address. Same origin, signed-in only, and only to the person and sign-in that
        // drew them. Unknown, freed, malformed or someone else's: the same 404. Never cached anywhere.
        app.MapGet(PageImagesRoute, (string file, HttpContext http, ChuvadiReader.Core.Reader.PageImages images) =>
        {
            if (!SameOriginIfStated(http)
                || ChuvadiReader.Web.Platform.PortalPageImageOwner.For(http.User) is not { } owner
                || !ChuvadiReader.Core.Reader.PageImages.TryParseAddress(file, out var token)
                || !images.TryGet(token, owner, out var png))
            {
                return Results.NotFound();
            }

            http.Response.Headers.CacheControl = "private, no-store";
            http.Response.Headers["X-Content-Type-Options"] = "nosniff";
            http.Response.Headers["Cross-Origin-Resource-Policy"] = "same-origin"; // no other site can embed it
            return Results.Bytes(png, "image/png");
        }).RequireAuthorization();

        var g = app.MapGroup(Prefix).RequireAuthorization();

        g.MapPost("/upload/{ticket}/files", (string ticket, BeginUpload body, HttpContext http, TransferRegistry reg) =>
        {
            if (!SameOrigin(http))
            {
                return Results.StatusCode(StatusCodes.Status403Forbidden);
            }

            var t = reg.FindUpload(ticket, UserKey.From(http.User) ?? string.Empty);
            if (t is null)
            {
                return Results.NotFound();
            }

            var (file, error) = t.Begin(body.Name, body.Size);
            return file is null ? Results.BadRequest(new { error }) : Results.Ok(new { id = file.Id, name = file.Name });
        });

        g.MapPut("/upload/{ticket}/files/{fileId}", async (string ticket, string fileId, long offset, HttpContext http,
            TransferRegistry reg, IOptions<PortalOptions> options, CancellationToken ct) =>
        {
            if (!SameOrigin(http))
            {
                return Results.StatusCode(StatusCodes.Status403Forbidden);
            }

            var t = reg.FindUpload(ticket, UserKey.From(http.User) ?? string.Empty);
            var f = t?.Find(fileId);
            if (t is null || f is null)
            {
                return Results.NotFound();
            }

            var max = options.Value.UploadChunkBytes;
            if (http.Request.ContentLength is long len && len > max)
            {
                return Results.BadRequest(new { error = "Chunk too large." });
            }

            // The server-wide body limit is small; a chunk endpoint raises it to one chunk only.
            if (http.Features.Get<IHttpMaxRequestBodySizeFeature>() is { IsReadOnly: false } limit)
            {
                limit.MaxRequestBodySize = max;
            }

            var error = await f.AppendAsync(offset, http.Request.Body, max, ct).ConfigureAwait(false);
            return error is null
                ? Results.Ok(new { received = f.Received, complete = f.IsComplete })
                : Results.BadRequest(new { error });
        });

        g.MapGet("/download/{token}", (string token, HttpContext http, TransferRegistry reg) =>
        {
            var d = reg.TakeDownload(token, UserKey.From(http.User) ?? string.Empty);
            if (d is null || !File.Exists(d.Path))
            {
                return Results.NotFound();
            }

            if (d.DeleteAfter)
            {
                http.Response.OnCompleted(() =>
                {
                    TryDeleteFileAndEmptyParent(d.Path);
                    return Task.CompletedTask;
                });
            }

            http.Response.Headers.CacheControl = "no-store";
            return Results.File(d.Path, ContentTypeFor(d.FileName), d.FileName, enableRangeProcessing: false);
        });

        g.MapGet("/print/{ticket}", (string ticket, HttpContext http, TransferRegistry reg) =>
        {
            var p = reg.FindPrint(ticket, UserKey.From(http.User) ?? string.Empty);
            if (p is null || !File.Exists(p.PdfPath))
            {
                return Results.NotFound();
            }

            http.Response.Headers.CacheControl = "no-store";
            // Inline, so the browser's own PDF viewer shows it in the print frame.
            http.Response.Headers.ContentDisposition = "inline; filename*=UTF-8''" + Uri.EscapeDataString(p.Title.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase) ? p.Title : p.Title + ".pdf");
            return Results.File(p.PdfPath, "application/pdf");
        });

        return app;
    }

    /// <summary>State-changing requests must carry the portal's own Origin (or none from a non-browser
    /// client is refused too).</summary>
    internal static bool SameOrigin(HttpContext http)
    {
        var origin = http.Request.Headers.Origin.ToString();
        if (string.IsNullOrEmpty(origin))
        {
            return false;
        }

        var configured = http.RequestServices.GetRequiredService<IOptions<PortalOptions>>().Value.PublicOrigin;
        var expected = !string.IsNullOrWhiteSpace(configured)
            ? configured.TrimEnd('/')
            : $"{http.Request.Scheme}://{http.Request.Host}";
        return string.Equals(origin, expected, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>For requests a browser makes by itself (an image): refused when the browser says it came
    /// from another site (<c>Sec-Fetch-Site</c>, or a stated <c>Origin</c>). Image requests usually carry
    /// neither from our own page, so their absence is allowed.</summary>
    internal static bool SameOriginIfStated(HttpContext http)
    {
        var site = http.Request.Headers["Sec-Fetch-Site"].ToString();
        if (site.Length > 0 && site is not ("same-origin" or "none"))
        {
            return false; // "same-site" (a sibling sub-domain) and "cross-site" both refused
        }

        return string.IsNullOrEmpty(http.Request.Headers.Origin.ToString()) || SameOrigin(http);
    }

    internal static string ContentTypeFor(string name) => Path.GetExtension(name).ToLowerInvariant() switch
    {
        ".pdf" => "application/pdf",
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".json" => "application/json",
        ".zip" => "application/zip",
        ".docx" => "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx" => "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt" or ".md" or ".log" => "text/plain; charset=utf-8",
        _ => "application/octet-stream",
    };

    internal static void TryDeleteFileAndEmptyParent(string path)
    {
        try
        {
            File.Delete(path);
            var dir = Path.GetDirectoryName(path);
            if (dir is not null && Directory.Exists(dir) && !Directory.EnumerateFileSystemEntries(dir).Any())
            {
                Directory.Delete(dir);
            }
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
