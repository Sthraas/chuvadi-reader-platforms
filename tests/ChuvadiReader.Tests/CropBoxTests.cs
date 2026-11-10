using Chuvadi.Pdf.Authoring;
using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Graphics;
using Chuvadi.Pdf.Reader;
using Chuvadi.Pdf.Text;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// D-160 (revised): a page shows what its file says — its CropBox within its MediaBox (chuvadi-pdf 3.32.0 draws that).
/// Everything the Reader puts on a page is a fraction of that box, so it lands where it was drawn. Fixture: a 600 × 800
/// page whose CropBox is [50 200 450 700] (400 × 500, off the page's centre), authored in code.
/// </summary>
public sealed class CropBoxTests
{
    private const double MediaW = 600, MediaH = 800, CropX = 50, CropY = 200, CropW = 400, CropH = 500;

    /// <summary>White page; "SECRET" near the crop's top-left and "KEEP" lower down, both inside the crop;
    /// "OUTSIDE" in the part the CropBox hides.</summary>
    private static string CroppedPage(bool inheritCrop = false)
    {
        var b = PdfDocumentBuilder.Create();
        var pb = b.AddPage(new PageSize(MediaW, MediaH));
        pb.DrawRectangle(0, 0, MediaW, MediaH, Color.FromHex("#FFFFFF"), Color.FromHex("#FFFFFF"), 0);
        pb.DrawText("SECRET", 120, 190, "Helvetica-Bold", 24, Color.FromHex("#000000"));   // top-left frame: user y ≈ 586–610
        pb.DrawText("KEEP", 300, 480, "Helvetica-Bold", 24, Color.FromHex("#000000"));
        pb.DrawText("OUTSIDE", 10, 20, "Helvetica-Bold", 24, Color.FromHex("#000000"));
        var path = TestPdf.WriteTemp(b.ToByteArray());

        using var doc = PdfDocument.Open(path);
        doc.Pages[0].CropBox = new PdfRectangle(CropX, CropY, CropX + CropW, CropY + CropH);
        var outPath = TestPdf.TempOutput();
        using (var fs = File.Create(outPath)) doc.Save(fs, null);
        return outPath;
    }

    private static string Text(string path)
    {
        using var doc = PdfDocument.Open(path);
        return string.Concat(new TextExtractor(doc.Objects, ExtractionStrategy.Layout).ExtractFragments(doc.Pages[0]).Select(f => f.Text));
    }

    [Fact]
    public void The_shown_box_is_the_crop_box_within_the_media_box()
    {
        using var doc = PdfDocument.Open(CroppedPage());
        Assert.Equal(new ShownBox(CropX, CropY, CropW, CropH), ShownBox.Of(doc.Pages[0]));

        // The renderer draws the same box: the page image is the crop's size (96 dpi: 400 pt → 533 px).
        var bmp = PdfRenderExtensions.RenderPageToBmp(doc, 0, 72);
        Assert.Equal((int)CropW, bmp[18] | (bmp[19] << 8));
    }

    [Fact]
    public void A_crop_box_inherited_from_the_page_tree_is_followed()
    {
        // tools/OfficeCorpus/make_pdf_fixtures.py: /CropBox on the /Pages node only.
        using var doc = PdfDocument.Open(System.IO.Path.Combine(AppContext.BaseDirectory, "Fixtures", "Pdf", "inherited-cropbox.pdf"));
        var bmp = PdfRenderExtensions.RenderPageToBmp(doc, 0, 72);
        var drawnW = bmp[18] | (bmp[19] << 8);
        Assert.Equal(new ShownBox(50, 200, 400, 500), ShownBox.Of(doc.Pages[0]));
        Assert.Equal(400, drawnW);   // the renderer follows it too
    }

    [Fact]
    public void A_page_without_a_crop_box_shows_its_media_box()
    {
        using var doc = PdfDocument.Open(TestPdf.BlankPage(300, 400));
        Assert.Equal(new ShownBox(0, 0, 300, 400), ShownBox.Of(doc.Pages[0]));
    }

    [Fact]
    public async Task A_redaction_box_removes_what_was_under_it_on_screen()
    {
        var src = CroppedPage();
        var outp = TestPdf.TempOutput();
        // Drawn over "SECRET": the top-left part of the page as shown (fractions of the 400 × 500 crop).
        var pages = new Dictionary<int, PageRedaction> { [0] = new PageRedaction(0, [new NormBox(0, 0.15, 0.5, 0.12)]) };
        await new RedactService().RedactToFileAsync(src, outp, pages, "#000000");

        var text = Text(outp);
        Assert.DoesNotContain("SECRET", text, StringComparison.Ordinal);
        Assert.Contains("KEEP", text, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_shape_lands_where_it_was_drawn()
    {
        var src = CroppedPage();
        var outp = TestPdf.TempOutput();
        var shapes = new Dictionary<int, PageShape>
        {
            [0] = new PageShape(0, [new ShapeAnno(0, 0, 0.3, 0.3, ShapeKind.Rectangle, "#FF0000", "#FF0000", 1, 0)]),
        };
        await new RedactService().FlattenToFileAsync(src, outp, new Dictionary<int, PageRedaction>(), "#000000",
            new Dictionary<int, PageText>(), new Dictionary<int, PageImage>(), shapes);

        Assert.True(TestPdf.IsReddish(TestPdf.SamplePixel(outp, 0, 0.2, 0.2)), "inside the shape, as drawn");
        Assert.True(TestPdf.IsWhitish(TestPdf.SamplePixel(outp, 0, 0.4, 0.4)), "just outside it");
    }

    [Fact]
    public void Measuring_uses_the_page_as_shown()
    {
        // Across the whole shown width: 400 pt = 141.1 mm (the MediaBox would say 600 pt = 211.7 mm).
        var r = new MeasureService().Measure(CroppedPage(), 0, new PagePoint(0, 0.5), new PagePoint(1, 0.5));
        Assert.Equal(400 * 25.4 / 72, r.PaperMm, 1);
    }

    [Fact]
    public void A_page_number_sits_inside_the_page_as_shown()
    {
        var src = File.ReadAllBytes(CroppedPage());
        var num = new DeskNumbering { Position = NumberPosition.BottomRight };
        var stamped = new StampService().ApplyNumbering(src, num, 1);
        var text = Text(TestPdf.WriteTemp(stamped));
        Assert.Contains("1", text, StringComparison.Ordinal);

        // Dark pixels in the shown page's bottom-right corner, where the number goes (24 pt margin).
        using var doc = PdfDocument.Open(new MemoryStream(stamped));
        var bmp = PdfRenderExtensions.RenderPageToBmp(doc, 0, 144);
        var dark = 0;
        for (double fx = 0.80; fx < 0.96; fx += 0.004)
        {
            for (double fy = 0.90; fy < 0.97; fy += 0.004)
            {
                var p = TestPdf.SampleBmp(bmp, fx, fy);
                if (p.R < 120 && p.G < 120 && p.B < 120) dark++;
            }
        }

        Assert.True(dark > 0, "no number in the shown page's bottom-right corner");
    }

    private static BenchPage BenchOf(string path) => new() { SourcePath = path, SourceName = "c.pdf", SourceIndex = 0, OriginalIndex = 0 };

    [Fact]
    public async Task Cropping_on_the_bench_cuts_the_page_as_shown()
    {
        // The top half of the page as shown: 400 × 250, with SECRET and without KEEP.
        var page = BenchOf(CroppedPage());
        page.Crop = new CropRect(0, 0, 1, 0.5);
        var outPath = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([page]));
        using var doc = PdfDocument.Open(outPath);
        Assert.Equal(CropW, ShownBox.Of(doc.Pages[0]).W, 1);
        Assert.Equal(CropH / 2, ShownBox.Of(doc.Pages[0]).H, 1);
        var bmp = PdfRenderExtensions.RenderPageToBmp(doc, 0, 72);
        Assert.Equal((int)CropW, bmp[18] | (bmp[19] << 8));
        Assert.Contains("SECRET", Text(outPath), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Resizing_on_the_bench_keeps_what_the_file_hides_hidden()
    {
        // Normalised to A4, the page as shown fills it: what was outside the CropBox stays out of sight.
        var outPath = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([BenchOf(CroppedPage())], default, "A4"));
        using var doc = PdfDocument.Open(outPath);
        var bmp = PdfRenderExtensions.RenderPageToBmp(doc, 0, 72);
        var dark = 0;
        for (double fx = 0; fx < 1; fx += 0.01)
        {
            for (double fy = 0; fy < 1; fy += 0.01)
            {
                var p = TestPdf.SampleBmp(bmp, fx, fy);
                if (p.R < 120 && p.G < 120 && p.B < 120) dark++;
            }
        }

        // SECRET and KEEP only (OUTSIDE is as big; with it the count roughly doubles).
        using var shownOnly = PdfDocument.Open(CroppedPage());
        var before = PdfRenderExtensions.RenderPageToBmp(shownOnly, 0, 72);
        var darkBefore = 0;
        for (double fx = 0; fx < 1; fx += 0.01)
        {
            for (double fy = 0; fy < 1; fy += 0.01)
            {
                var p = TestPdf.SampleBmp(before, fx, fy);
                if (p.R < 120 && p.G < 120 && p.B < 120) darkBefore++;
            }
        }

        Assert.InRange(dark, darkBefore / 2, darkBefore * 3 / 2);
        Assert.True(TestPdf.IsWhitish(TestPdf.SampleBmp(bmp, 0.05, 0.03)), "the top-left corner, where OUTSIDE would be");
    }

    private static int DarkIn(byte[] bmp, double x0, double x1, double y0, double y1)
    {
        var dark = 0;
        for (double fx = x0; fx < x1; fx += 0.004)
        {
            for (double fy = y0; fy < y1; fy += 0.004)
            {
                var p = TestPdf.SampleBmp(bmp, fx, fy);
                if (p.R < 140 && p.G < 140 && p.B < 140) dark++;
            }
        }

        return dark;
    }

    [Fact(Skip = "Library item PDF-L1: chuvadi-pdf 3.32.0's HeaderFooter places the bands on the MediaBox, so on a cropped page they fall in the part the file hides")]
    public void A_footer_shows_on_the_page_as_shown()
    {
        var hf = new DeskHeaderFooter { FooterEnabled = true, FooterCenter = "FOOTER TEXT", FontSize = 14, ColorHex = "#000000" };
        var stamped = new StampService().ApplyHeaderFooter(File.ReadAllBytes(CroppedPage()), hf, [0], "c.pdf", DateTimeOffset.UnixEpoch);
        using var doc = PdfDocument.Open(new MemoryStream(stamped));
        Assert.True(DarkIn(PdfRenderExtensions.RenderPageToBmp(doc, 0, 144), 0.2, 0.8, 0.92, 1) > 0, "no footer at the foot of the page as shown");
    }

    [Fact(Skip = "Library item PDF-L2: chuvadi-pdf 3.32.0's WatermarkStamper centres on the MediaBox, not on the page as shown (on this page it lands at 62 % across, 60 % down)")]
    public void A_watermark_shows_on_the_page_as_shown()
    {
        var wm = new DeskWatermark { Text = "WATERMARK", FontSize = 40, Opacity = 1, RotationDegrees = 0, ColorHex = "#000000" };
        var stamped = new StampService().ApplyWatermark(File.ReadAllBytes(CroppedPage()), wm, [0]);
        using var doc = PdfDocument.Open(new MemoryStream(stamped));
        // Centred on the page as shown: dark pixels across its middle band (the page's own text is elsewhere).
        Assert.True(DarkIn(PdfRenderExtensions.RenderPageToBmp(doc, 0, 144), 0.25, 0.75, 0.45, 0.55) > 0, "no watermark across the middle of the page as shown");
    }

    [Fact]
    public async Task A_large_sheet_drawn_as_an_image_is_the_size_of_the_page_as_shown()
    {
        // 2000 × 2000 pt with a 1600 × 1200 CropBox: large enough to be drawn as one image (D-158).
        var b = PdfDocumentBuilder.Create();
        var pb = b.AddPage(new PageSize(2000, 2000));
        pb.DrawRectangle(0, 0, 2000, 2000, Color.FromHex("#FFFFFF"), Color.FromHex("#FFFFFF"), 0);
        var path = TestPdf.WriteTemp(b.ToByteArray());
        using (var doc = PdfDocument.Open(path))
        {
            doc.Pages[0].CropBox = new PdfRectangle(100, 100, 1700, 1300);
            path = TestPdf.TempOutput();
            using var fs = File.Create(path);
            doc.Save(fs, null);
        }

        using var session = await new ChuvadiReader.Core.Reader.ChuvadiPdfReader().OpenAsync(path, "sheet.pdf");
        var svg = await session.RenderPageSvgAsync(0);
        Assert.Contains("<image", svg, StringComparison.Ordinal);
        Assert.Contains("width=\"1600pt\" height=\"1200pt\"", svg, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Properties_report_the_size_of_the_page_as_shown()
    {
        var props = await new DocumentPropertiesService().ReadAsync(CroppedPage());
        Assert.StartsWith("141 × 176 mm", props.PageSize, StringComparison.Ordinal);
    }
}
