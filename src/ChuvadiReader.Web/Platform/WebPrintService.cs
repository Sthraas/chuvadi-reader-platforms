using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Operations;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Files;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// Printing on the portal is the browser printing the PDF (coordinator decision, 6 Nov). The whole,
/// unprotected document is handed over as it is. For a page range or a password-protected file,
/// chuvadi-pdf assembles a print copy of just those pages (unprotected, in this session's folder,
/// deleted with the session). A file whose permissions forbid printing is refused, as on every
/// platform. The browser's own dialog then chooses printer, copies and scaling, and
/// it does not report back whether the person printed or cancelled — so success means "handed to
/// the print dialog".
/// </summary>
public sealed class WebPrintService : IPrintService
{
    private readonly SessionSpace _space;
    private readonly TransferRegistry _registry;
    private readonly BrowserBridge _browser;

    public WebPrintService(SessionSpace space, TransferRegistry registry, BrowserBridge browser)
    {
        _space = space;
        _registry = registry;
        _browser = browser;
    }

    public bool IsAvailable => true;

    public async Task<PrintResult> PrintAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        string? copy = null;
        try
        {
            await _space.EnsureAsync(ct).ConfigureAwait(false);
            var title = string.IsNullOrWhiteSpace(request.JobName) ? Path.GetFileName(pdfPath) : request.JobName!;

            var prepared = await Task.Run(() => Prepare(pdfPath, request, ct), ct).ConfigureAwait(false);
            if (prepared.Error is not null)
            {
                return new PrintResult(PrintOutcome.Failed, 0, prepared.Error);
            }

            copy = prepared.CopyPath;
            var ticket = _registry.CreatePrint(_space.UserKey, _space.ConnectionId, prepared.CopyPath ?? pdfPath, title, TimeSpan.FromMinutes(30));
            var shown = await _browser.PrintAsync($"{FileEndpoints.Prefix}/print/{ticket.Id}", ct).ConfigureAwait(false);
            var n = prepared.PageCount;
            var pages = n == 1 ? "1 page" : $"{n} pages";
            return shown switch
            {
                "dialog" => new PrintResult(PrintOutcome.Printed, n, $"Sent {pages} to the browser's print dialog"),
                "tab" => new PrintResult(PrintOutcome.Printed, n, $"Ready: open the PDF ({pages}) from the link, then print it from its tab"),
                _ => new PrintResult(PrintOutcome.Failed, 0, "The browser couldn't open its print dialog"),
            };
        }
        catch (OperationCanceledException)
        {
            Delete(copy);
            return new PrintResult(PrintOutcome.Cancelled, 0, "Printing cancelled");
        }
        catch (Exception ex) when (ex is JSException or JSDisconnectedException)
        {
            return new PrintResult(PrintOutcome.Failed, 0, "Couldn't print: the browser didn't respond");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or InvalidDataException or InvalidOperationException or ArgumentException)
        {
            Delete(copy);
            return new PrintResult(PrintOutcome.Failed, 0, "Couldn't print: " + ex.Message);
        }
    }

    private sealed record Prepared(string? CopyPath, int PageCount, string? Error);

    private Prepared Prepare(string pdfPath, PrintRequest request, CancellationToken ct)
    {
        using var doc = string.IsNullOrEmpty(request.Password) ? PdfDocument.Open(pdfPath) : PdfDocument.Open(pdfPath, request.Password);

        // The file's own "no printing" permission (L-8). Checked before anything is handed over: the
        // browser would otherwise get the whole file, and a print copy would carry no protection at all.
        if (!PrintPermission.Allows(doc))
        {
            return new Prepared(null, 0, PrintPermission.Refused);
        }

        if (!PageRangeParser.TryParse(request.PageRange, doc.Pages.Count, request.CurrentPage, out var pages, out var error))
        {
            return new Prepared(null, 0, error);
        }

        bool everyPageInOrder = pages.Count == doc.Pages.Count && pages.Select((p, i) => p == i).All(x => x);
        if (everyPageInOrder && string.IsNullOrEmpty(request.Password))
        {
            return new Prepared(null, pages.Count, null);
        }

        ct.ThrowIfCancellationRequested();
        var folder = Path.Combine(_space.Print, TransferRegistry.NewToken());
        SpaceLayout.CreatePrivateDirectory(folder);
        var copy = Path.Combine(folder, SpaceLayout.SafeFileName(Path.GetFileName(pdfPath), "document.pdf"));
        using (var output = new FileStream(copy, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            PageOperations.Assemble(output, pages.Select(i => new PageSelector(doc, i)).ToList());
        }

        return new Prepared(copy, pages.Count, null);
    }

    private static void Delete(string? path)
    {
        if (path is not null)
        {
            FileEndpoints.TryDeleteFileAndEmptyParent(path);
        }
    }
}
