using CoreGraphics;
using Foundation;
using PdfKit;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-26: draws each page of the print PDF onto the sheet itself. Handing UIKit the PDF as a printing item
/// left a page shown landscape (an upright page with /Rotate 90) drawn into the upright sheet's area even on a
/// landscape sheet, so its right and bottom were cut off. Here every page is placed by <see cref="PrintFit"/> inside
/// the sheet's printable area, as shown (turn counted), and drawn by PDFKit — still vector, marks included.
/// </summary>
internal sealed class MacPdfPageRenderer : UIPrintPageRenderer
{
    private readonly PdfDocument _pdf;
    private readonly bool _fitToPage;

    public MacPdfPageRenderer(byte[] pdf, bool fitToPage)
    {
        _pdf = new PdfDocument(NSData.FromArray(pdf));
        _fitToPage = fitToPage;
    }

    public override nint NumberOfPages => _pdf.PageCount;

    public override void DrawPage(nint index, CGRect pageRect)
    {
        var context = UIGraphics.GetCurrentContext();
        var page = _pdf.GetPage(index);
        if (context is null || page is null)
        {
            return;
        }

        Draw(context, page, PrintableRect, _fitToPage);
    }

    /// <summary>Draws <paramref name="page"/> inside <paramref name="area"/> of a context whose origin is top-left
    /// (UIKit's). Returns where it was placed.</summary>
    public static PrintFit.Placement Draw(CGContext context, PdfPage page, CGRect area, bool fitToPage)
    {
        var box = page.GetBoundsForBox(PdfDisplayBox.Crop);
        var (w, h) = PrintFit.Shown(box.Width, box.Height, (int)page.Rotation);
        var at = PrintFit.Place(w, h, area.X, area.Y, area.Width, area.Height, fitToPage);

        context.SaveState();
        context.ClipToRect(new CGRect(at.X, at.Y, at.Width, at.Height));
        // PDFKit draws the page as shown with its bottom-left corner at the origin, y upwards.
        context.TranslateCTM((nfloat)at.X, (nfloat)(at.Y + at.Height));
        context.ScaleCTM((nfloat)at.Scale, (nfloat)(-at.Scale));
        page.Draw(PdfDisplayBox.Crop, context);
        context.RestoreState();
        return at;
    }

    /// <summary>Smoke check: the first page of <paramref name="pdf"/> drawn on a sheet of the given size with 18 pt
    /// margins, into a bitmap; returns the placement and the box of everything that is not white.</summary>
    public static string Probe(byte[] pdf, bool landscape, bool fitToPage)
    {
        int sw = landscape ? 792 : 612, sh = landscape ? 612 : 792;
        using var doc = new PdfDocument(NSData.FromArray(pdf));
        var page = doc.GetPage(0);
        if (page is null)
        {
            return "no-page";
        }

        using var space = CGColorSpace.CreateDeviceRGB();
        var pixels = new byte[sw * sh * 4];
        using var bitmap = new CGBitmapContext(pixels, sw, sh, 8, sw * 4, space, CGImageAlphaInfo.PremultipliedLast);
        bitmap.SetFillColor(1, 1, 1, 1);
        bitmap.FillRect(new CGRect(0, 0, sw, sh));
        bitmap.TranslateCTM(0, sh);   // top-left origin, as UIKit's print context
        bitmap.ScaleCTM(1, -1);
        var at = Draw(bitmap, page, new CGRect(18, 18, sw - 36, sh - 36), fitToPage);

        int x0 = sw, y0 = sh, x1 = -1, y1 = -1;
        for (var y = 0; y < sh; y++)
        {
            for (var x = 0; x < sw; x++)
            {
                var i = (y * sw + x) * 4;
                if (pixels[i] < 200 || pixels[i + 1] < 200 || pixels[i + 2] < 200)
                {
                    if (x < x0) { x0 = x; }
                    if (x > x1) { x1 = x; }
                    if (y < y0) { y0 = y; }
                    if (y > y1) { y1 = y; }
                }
            }
        }

        // The same drawing into a PDF, as printing does: it must stay vector — no picture of the page in it.
        using var data = new NSMutableData();
        using (var consumer = new CGDataConsumer(data))
        {
            var sheet = new CGRect(0, 0, sw, sh);
            using var pdfOut = new CGContextPDF(consumer, sheet);
            pdfOut.BeginPage(sheet);
            pdfOut.TranslateCTM(0, sh);
            pdfOut.ScaleCTM(1, -1);
            Draw(pdfOut, page, new CGRect(18, 18, sw - 36, sh - 36), fitToPage);
            pdfOut.EndPage();
            pdfOut.Close();
        }

        var written = System.Text.Encoding.Latin1.GetString(data.ToArray());
        var images = System.Text.RegularExpressions.Regex.Matches(written, @"/Subtype\s*/Image").Count;

        return FormattableString.Invariant(
            $"sheet={sw}x{sh} rotation={page.Rotation} scale={at.Scale:0.###} placed={at.X:0},{at.Y:0}+{at.Width:0}x{at.Height:0} ink={x0},{y0}..{x1},{y1} pdf-bytes={written.Length} pdf-images={images}");
    }
}
