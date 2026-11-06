using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Operations;

namespace ChuvadiReader.Core.Reader;

/// <summary>The PDF a host hands to its operating system's print system, plus what it holds.</summary>
public sealed record PrintDocument(byte[] Pdf, int PageCount, string JobName);

/// <summary>The file's own permissions forbid printing (<see cref="PrintPermission"/>); the message is
/// <see cref="PrintPermission.Refused"/>.</summary>
public sealed class PrintRefusedException : Exception
{
    public PrintRefusedException()
        : base(PrintPermission.Refused)
    {
    }
}

/// <summary>
/// Prepares a PDF for printing through an OS print system (macOS print panel, Android PrintManager,
/// browser print), so what prints is what Chuvadi shows, not the OS's own reading of the file:
/// <list type="number">
/// <item>chuvadi-pdf opens the file (with its password, if any);</item>
/// <item>form fields and annotations are flattened into the page content — using chuvadi-pdf's generated
/// appearances where the file's are missing or out of date — and anything that could not be baked is
/// dropped, so no live annotation is left for the OS to draw its own way;</item>
/// <item>exactly the requested pages are written, in the requested order, unencrypted.</item>
/// </list>
/// Everything stays vector — nothing is rasterised — and the original file is never changed.
/// The flatten follows on-screen rules (as the Reader and the Windows print path draw today); the
/// print-flag rules (ISO 32000 §12.5.3) need a library option — see docs/mac/LIBRARY-ASKS.md.
/// </summary>
public static class PrintDocumentBuilder
{
    /// <summary>Builds the print PDF. Throws <see cref="PrintRefusedException"/> when the file's permissions
    /// forbid printing (checked first, before any work), and <see cref="ArgumentException"/> with a short
    /// user-facing message when the page range can't be used.</summary>
    public static Task<PrintDocument> BuildAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
        => Task.Run(() =>
        {
            ArgumentException.ThrowIfNullOrEmpty(pdfPath);
            ArgumentNullException.ThrowIfNull(request);

            using var doc = string.IsNullOrEmpty(request.Password)
                ? PdfDocument.Open(pdfPath)
                : PdfDocument.Open(pdfPath, request.Password);

            if (!PrintPermission.Allows(doc))
            {
                throw new PrintRefusedException();
            }

            if (!PageRangeParser.TryParse(request.PageRange, doc.PageCount, request.CurrentPage, out var pages, out var error))
            {
                throw new ArgumentException(error ?? "Those pages can't be printed.");
            }

            ct.ThrowIfCancellationRequested();

            // Flatten the whole document first: the form's /NeedAppearances and field tree live in the
            // catalog, so baking before picking pages keeps generated field appearances correct.
            using var flat = new MemoryStream();
            AnnotationFlattener.Flatten(flat, doc, new AnnotationFlattenOptions
            {
                Kinds = AnnotationFlattenKinds.All,
                DropRemainingAnnotations = true,
            });

            ct.ThrowIfCancellationRequested();
            flat.Position = 0;
            using var flatDoc = PdfDocument.Open(flat, leaveOpen: true);
            var selectors = pages.Select(p => new PageSelector(flatDoc, p)).ToList();
            using var output = new MemoryStream();
            PageOperations.Assemble(output, selectors);

            var name = string.IsNullOrWhiteSpace(request.JobName) ? Path.GetFileName(pdfPath) : request.JobName!;
            return new PrintDocument(output.ToArray(), pages.Count, name);
        }, ct);
}
