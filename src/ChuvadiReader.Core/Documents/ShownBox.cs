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

    /// <summary>B-32: the page's /Rotate as a quarter turn clockwise (0, 90, 180 or 270): how far the page is turned
    /// when it is shown.</summary>
    public static int TurnOf(PdfPage page) => (((page.Rotate % 360) + 360) % 360) / 90 * 90;

    /// <summary>The size of the box as shown with the page turned by <paramref name="turn"/>: on its side for a
    /// quarter turn either way.</summary>
    public (double W, double H) ShownSize(int turn) => turn is 90 or 270 ? (H, W) : (W, H);

    /// <summary>Places something drawn on the page as shown (a page of <see cref="ShownSize"/>, origin bottom-left,
    /// y up) onto the page's own space, for a page turned clockwise by <paramref name="turn"/>.</summary>
    public Chuvadi.Pdf.Graphics.Transform FromShown(int turn)
    {
        var t = turn switch
        {
            90 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(90).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(W, 0)),
            180 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(180).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(W, H)),
            270 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(-90).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(0, H)),
            _ => Chuvadi.Pdf.Graphics.Transform.Identity,
        };
        return AtOrigin ? t : t.Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(X0, Y0));
    }

    /// <summary>The other way from <see cref="FromShown"/>: places the page's own content as it is shown, on a page of
    /// <see cref="ShownSize"/> with its origin at the bottom-left. Used where a page is rebuilt (the bench's crop,
    /// margins, resize and imposition), so a turned page stays as it was shown.</summary>
    public Chuvadi.Pdf.Graphics.Transform ToShown(int turn)
    {
        var t = turn switch
        {
            90 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(-90).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(0, W)),
            180 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(180).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(W, H)),
            270 => Chuvadi.Pdf.Graphics.Transform.CreateRotationDegrees(90).Multiply(Chuvadi.Pdf.Graphics.Transform.CreateTranslation(H, 0)),
            _ => Chuvadi.Pdf.Graphics.Transform.Identity,
        };
        return AtOrigin ? t : Chuvadi.Pdf.Graphics.Transform.CreateTranslation(-X0, -Y0).Multiply(t);
    }

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
