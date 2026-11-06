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

    public static IEndpointRouteBuilder MapPortalFiles(this IEndpointRouteBuilder app)
    {
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
