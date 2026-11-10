using Chuvadi.Pdf.Documents;

namespace ChuvadiReader.Core.Documents;

/// <summary>
/// D-160 (revised): the part of a PDF page the file says to show — its CropBox clipped to its MediaBox, which is what
/// chuvadi-pdf's renderers draw since 3.32.0 (<c>PdfDisplayBox.CropBox</c>, PDF 32000-1 §14.11.2). A page without a
/// CropBox, or whose CropBox misses the MediaBox, shows its MediaBox. Everything the Reader places on a page (redaction,
/// markups, page numbers, measuring, search boxes) is a fraction of this box, so it lands where it was drawn.
/// </summary>
/// <param name="X0">Left edge in default user space (points).</param>
/// <param name="Y0">Bottom edge in default user space (points).</param>
public readonly record struct ShownBox(double X0, double Y0, double W, double H)
{
    public double X1 => X0 + W;

    public double Y1 => Y0 + H;

    /// <summary>True when the box starts at the user-space origin (most files); the mapping is then the one before D-160.</summary>
    public bool AtOrigin => X0 == 0 && Y0 == 0;

    public static ShownBox Of(PdfPage page)
    {
        var m = page.MediaBox;
        double mx0 = Math.Min(m.X1, m.X2), my0 = Math.Min(m.Y1, m.Y2), mx1 = Math.Max(m.X1, m.X2), my1 = Math.Max(m.Y1, m.Y2);
        var c = page.CropBox;
        double x0 = Math.Max(mx0, Math.Min(c.X1, c.X2)), y0 = Math.Max(my0, Math.Min(c.Y1, c.Y2));
        double x1 = Math.Min(mx1, Math.Max(c.X1, c.X2)), y1 = Math.Min(my1, Math.Max(c.Y1, c.Y2));
        return x1 > x0 && y1 > y0
            ? new ShownBox(x0, y0, x1 - x0, y1 - y0)
            : new ShownBox(mx0, my0, mx1 - mx0, my1 - my0);
    }
}
