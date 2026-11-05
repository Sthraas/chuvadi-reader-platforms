using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Operations;

namespace ChuvadiReader.Core.Reader;

/// <summary>The PDF a host hands to its operating system's print system, plus what it holds.</summary>
public sealed record PrintDocument(byte[] Pdf, int PageCount, string JobName);

/// <summary>
/// Prepares a PDF for printing through an OS print system (macOS print panel, Android PrintManager,
/// browser print): chuvadi-pdf opens the file (with its password, if any) and writes a new PDF holding
/// exactly the requested pages, in the requested order, unencrypted. The pages stay vector — nothing is
/// rasterised — and the original file is never changed. Used by hosts whose print path takes a PDF.
/// </summary>
public static class PrintDocumentBuilder
{
    /// <summary>Builds the print PDF. Throws <see cref="ArgumentException"/> with a short user-facing
    /// message when the page range can't be used.</summary>
    public static Task<PrintDocument> BuildAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
        => Task.Run(() =>
        {
            ArgumentException.ThrowIfNullOrEmpty(pdfPath);
            ArgumentNullException.ThrowIfNull(request);

            using var doc = string.IsNullOrEmpty(request.Password)
                ? PdfDocument.Open(pdfPath)
                : PdfDocument.Open(pdfPath, request.Password);

            if (!PageRangeParser.TryParse(request.PageRange, doc.PageCount, request.CurrentPage, out var pages, out var error))
            {
                throw new ArgumentException(error ?? "Those pages can't be printed.");
            }

            ct.ThrowIfCancellationRequested();
            var selectors = pages.Select(p => new PageSelector(doc, p)).ToList();
            using var output = new MemoryStream();
            PageOperations.Assemble(output, selectors);

            var name = string.IsNullOrWhiteSpace(request.JobName) ? Path.GetFileName(pdfPath) : request.JobName!;
            return new PrintDocument(output.ToArray(), pages.Count, name);
        }, ct);
}
