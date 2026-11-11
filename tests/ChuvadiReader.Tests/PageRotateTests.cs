using System.Globalization;
using System.Text.RegularExpressions;
using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Graphics;
using Path = System.IO.Path;
using Chuvadi.Pdf.Rendering;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// Linux Test B-32: a page's /Rotate (90, 180, 270) was ignored on screen. The page is shown turned as the file says,
/// as every PDF viewer shows it, and what the Reader places on the page lands where it was drawn.
/// Fixture: a 200 × 400 page with a red square in its bottom-left corner and a blue one in its top-right.
/// </summary>
public sealed class PageRotateTests
{
    internal static string Turned(int rotate, string extra = "")
    {
        const string content = "1 0 0 rg 0 0 50 50 re f 0 0 1 rg 150 350 50 50 re f";
        return LayersMeasureSignatureTests.RawPdf(
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            $"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 400] /Rotate {rotate} {extra} /Contents 4 0 R >>",
            $"<< /Length {content.Length} >>\nstream\n{content}\nendstream");
    }

    private static (double W, double H) SizeOf(string svg)
    {
        var m = Regex.Match(svg, "viewBox=\"0 0 ([0-9.]+) ([0-9.]+)\"");
        return (double.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture), double.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture));
    }

    [Theory]
    [InlineData(0, 200, 400)]
    [InlineData(90, 400, 200)]
    [InlineData(180, 200, 400)]
    [InlineData(270, 400, 200)]
    public async Task A_turned_page_is_shown_turned(int rotate, double w, double h)
    {
        using var session = await new ChuvadiPdfReader().OpenAsync(Turned(rotate), "turned.pdf");
        var svg = await session.RenderPageSvgAsync(0);
        Assert.Equal((w, h), SizeOf(svg));
    }

    /// <summary>Where the fixture's squares are on the page as shown (fractions from its top-left).</summary>
    private static (double X, double Y) Red(int rotate) => rotate switch
    {
        90 => (0.0625, 0.125), 180 => (0.875, 0.0625), 270 => (0.9375, 0.875), _ => (0.125, 0.9375),
    };

    private static (double X, double Y) Blue(int rotate) => rotate switch
    {
        90 => (0.9375, 0.875), 180 => (0.125, 0.9375), 270 => (0.0625, 0.125), _ => (0.875, 0.0625),
    };

    /// <summary>A pixel of the page as a PDF viewer shows it (its /Rotate applied), at fractions from the top-left.</summary>
    internal static (int R, int G, int B) Shown(string path, double fx, double fy)
    {
        using var doc = PdfDocument.Open(path);
        var buffer = new PageRasterizer(doc.Objects, new RenderOptions { Dpi = 96, ApplyPageRotation = true, Background = ColorF.White })
            .Rasterize(doc.Pages[0]);
        var p = buffer.GetPixelBgra(Math.Min(buffer.Width - 1, (int)(fx * buffer.Width)), Math.Min(buffer.Height - 1, (int)(fy * buffer.Height)));
        return (p.R, p.G, p.B);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public void The_fixture_is_turned_clockwise_as_viewers_turn_it(int rotate)
    {
        var path = Turned(rotate);
        Assert.True(TestPdf.IsReddish(Shown(path, Red(rotate).X, Red(rotate).Y)));
        Assert.True(TestPdf.IsBluish(Shown(path, Blue(rotate).X, Blue(rotate).Y)));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task A_redaction_box_covers_what_was_under_it_on_screen(int rotate)
    {
        var src = Turned(rotate);
        var outp = TestPdf.TempOutput();
        var (x, y) = Red(rotate);
        var pages = new Dictionary<int, PageRedaction> { [0] = new PageRedaction(0, [new NormBox(x - 0.05, y - 0.05, 0.1, 0.1)]) };
        await new RedactService().RedactToFileAsync(src, outp, pages, "#000000");

        Assert.True(TestPdf.IsDark(Shown(outp, x, y)), "the red square's middle is covered");
        Assert.True(TestPdf.IsBluish(Shown(outp, Blue(rotate).X, Blue(rotate).Y)), "the blue square is untouched");
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task A_shape_a_text_and_a_picture_land_where_they_were_drawn_the_right_way_up(int rotate)
    {
        var src = Turned(rotate);
        var outp = TestPdf.TempOutput();
        // On the page as shown: a green rectangle middle-left, a short line of text at the top-left of a box in the
        // middle, and a picture (grey, its top-left quarter green) middle-right.
        var shapes = new Dictionary<int, PageShape>
        {
            [0] = new PageShape(0, [new ShapeAnno(0.05, 0.4, 0.1, 0.2, ShapeKind.Rectangle, "#00A000", "#00A000", 1, 0)]),
        };
        var texts = new Dictionary<int, PageText>
        {
            [0] = new PageText(0, [new TextAnno(0.25, 0.3, 0.4, 0.4, "MM", "Helvetica", true, false, 12, "#000000", "left", 0, 1.2)]),
        };
        var picture = TestPdf.Png(40, 40, (x, y) => x < 20 && y < 20 ? ((byte)0, (byte)160, (byte)0) : ((byte)200, (byte)200, (byte)200));
        var images = new Dictionary<int, PageImage>
        {
            [0] = new PageImage(0, [new ImageAnno(0.7, 0.3, 0.2, 0.4, picture, 0, 1, false)]),
        };
        await new RedactService().FlattenToFileAsync(src, outp, new Dictionary<int, PageRedaction>(), "#000000", texts, images, shapes);

        Assert.True(TestPdf.IsGreenish(Shown(outp, 0.1, 0.5)), "inside the shape, as drawn");
        Assert.True(TestPdf.IsWhitish(Shown(outp, 0.1, 0.75)), "below the shape");

        // The text: every dark pixel is in the top-left quarter of its box (left-aligned, first line).
        int inPlace = 0, elsewhere = 0;
        for (double fx = 0.02; fx < 0.98; fx += 0.004)
        {
            for (double fy = 0.02; fy < 0.98; fy += 0.004)
            {
                if (!TestPdf.IsDark(Shown2(outp, fx, fy))) continue;
                if (fx is > 0.24 and < 0.45 && fy is > 0.29 and < 0.5) inPlace++; else elsewhere++;
            }
        }

        Assert.True(inPlace > 5, "the text starts at the top-left of its box");
        Assert.Equal(0, elsewhere);

        // The picture is in the file at every turn and the screen draws it; the library's rasteriser, which these
        // tests look through, only draws it on an unturned page (library item PDF-L6, below).
        using (var session = await new ChuvadiPdfReader().OpenAsync(outp, "out.pdf"))
        {
            Assert.Contains("<image", await session.RenderPageSvgAsync(0), StringComparison.Ordinal);
        }

        if (rotate == 0)
        {
            AssertPictureUpright(outp);
        }
    }

    private static void AssertPictureUpright(string outp)
    {
        // Its green quarter is at the top-left of its box, the rest grey.
        Assert.True(TestPdf.IsGreenish(Shown(outp, 0.73, 0.36)), "the picture's top-left quarter");
        Assert.False(TestPdf.IsGreenish(Shown(outp, 0.87, 0.36)), "its top-right");
        Assert.False(TestPdf.IsGreenish(Shown(outp, 0.73, 0.64)), "its bottom-left");
        Assert.False(TestPdf.IsWhitish(Shown(outp, 0.87, 0.64)), "its bottom-right is the picture, not the page");
        Assert.True(TestPdf.IsWhitish(Shown(outp, 0.8, 0.75)), "below the picture");
    }

    /// <summary>Library item PDF-L6 (chuvadi-pdf 3.32.0): <c>PageRasterizer</c> draws nothing for a picture placed
    /// with a quarter or half turn (it draws one turned 45°, and the SVG renderer draws all of them). The saved file
    /// is right: other viewers show the picture upright in its box on a turned page. Until the library draws it,
    /// printing and image export from the Reader miss such a picture.</summary>
    [Theory(Skip = "Library item PDF-L6: PageRasterizer draws nothing for a picture placed with a quarter or half turn")]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task A_picture_on_a_turned_page_is_upright_in_its_box(int rotate)
    {
        var outp = TestPdf.TempOutput();
        var picture = TestPdf.Png(40, 40, (x, y) => x < 20 && y < 20 ? ((byte)0, (byte)160, (byte)0) : ((byte)200, (byte)200, (byte)200));
        var images = new Dictionary<int, PageImage> { [0] = new PageImage(0, [new ImageAnno(0.7, 0.3, 0.2, 0.4, picture, 0, 1, false)]) };
        await new RedactService().FlattenToFileAsync(Turned(rotate), outp, new Dictionary<int, PageRedaction>(), "#000000",
            new Dictionary<int, PageText>(), images, new Dictionary<int, PageShape>());
        AssertPictureUpright(outp);
    }

    private static readonly Dictionary<string, PixelBuffer> Rasters = [];

    private static (int R, int G, int B) Shown2(string path, double fx, double fy)
    {
        if (!Rasters.TryGetValue(path, out var buffer))
        {
            using var doc = PdfDocument.Open(path);
            buffer = new PageRasterizer(doc.Objects, new RenderOptions { Dpi = 96, ApplyPageRotation = true, Background = ColorF.White }).Rasterize(doc.Pages[0]);
            Rasters[path] = buffer;
        }

        var p = buffer.GetPixelBgra(Math.Min(buffer.Width - 1, (int)(fx * buffer.Width)), Math.Min(buffer.Height - 1, (int)(fy * buffer.Height)));
        return (p.R, p.G, p.B);
    }

    [Theory]
    [InlineData(0, 200, 400)]
    [InlineData(90, 400, 200)]
    [InlineData(180, 200, 400)]
    [InlineData(270, 400, 200)]
    public void Measuring_follows_the_page_as_shown(int rotate, double across, double down)
    {
        var path = Turned(rotate);
        Assert.Equal(across * 25.4 / 72, new MeasureService().Measure(path, 0, new PagePoint(0, 0.5), new PagePoint(1, 0.5)).PaperMm, 1);
        Assert.Equal(down * 25.4 / 72, new MeasureService().Measure(path, 0, new PagePoint(0.5, 0), new PagePoint(0.5, 1)).PaperMm, 1);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public void A_page_number_sits_at_the_bottom_of_the_page_as_shown(int rotate)
    {
        // The fixture's squares are in two corners; the number goes bottom-centre, which is clear at every turn.
        var stamped = TestPdf.WriteTemp(new StampService().ApplyNumbering(File.ReadAllBytes(Turned(rotate)),
            new DeskNumbering { Position = NumberPosition.BottomCenter, FontSize = 14, ColorHex = "#000000" }, 1));
        int inPlace = 0, elsewhere = 0;
        for (double fx = 0.02; fx < 0.98; fx += 0.004)
        {
            for (double fy = 0.02; fy < 0.98; fy += 0.004)
            {
                if (!TestPdf.IsDark(Shown2(stamped, fx, fy))) continue;
                if (fx is > 0.4 and < 0.6 && fy > 0.8) inPlace++; else elsewhere++;
            }
        }

        Assert.True(inPlace > 0, "no number at the bottom centre of the page as shown");
        Assert.Equal(0, elsewhere);
    }

    [Theory]
    [InlineData(0, "71 × 141 mm")]
    [InlineData(90, "141 × 71 mm")]
    public async Task Properties_report_the_page_as_shown(int rotate, string size)
    {
        var props = await new DocumentPropertiesService().ReadAsync(Turned(rotate));
        Assert.StartsWith(size, props.PageSize, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_large_turned_sheet_drawn_as_an_image_is_on_its_side()
    {
        const string content = "1 0 0 rg 0 0 50 50 re f";
        var path = LayersMeasureSignatureTests.RawPdf(
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1600 2400] /Rotate 90 /Contents 4 0 R >>",
            $"<< /Length {content.Length} >>\nstream\n{content}\nendstream");
        using var session = await new ChuvadiPdfReader().OpenAsync(path, "sheet.pdf");
        var svg = await session.RenderPageSvgAsync(0);
        Assert.Contains("<image", svg, StringComparison.Ordinal);
        Assert.Contains("width=\"2400pt\" height=\"1600pt\"", svg, StringComparison.Ordinal);
    }

    private static (int InPlace, int Elsewhere) Dark(string path, double x0, double x1, double y0, double y1)
    {
        int inPlace = 0, elsewhere = 0;
        for (double fx = 0.02; fx < 0.98; fx += 0.004)
        {
            for (double fy = 0.02; fy < 0.98; fy += 0.004)
            {
                if (!TestPdf.IsDark(Shown2(path, fx, fy))) continue;
                if (fx > x0 && fx < x1 && fy > y0 && fy < y1) inPlace++; else elsewhere++;
            }
        }

        return (inPlace, elsewhere);
    }

    /// <summary>Library item PDF-L7 (chuvadi-pdf 3.32.0): <c>HeaderFooter</c> places its bands on the unturned page, so
    /// on a page with /Rotate they are along a side (or upside down at the head), not at the foot as shown.</summary>
    [Theory(Skip = "Library item PDF-L7: HeaderFooter ignores the page's /Rotate (the footer is along a side of the page as shown)")]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public void A_footer_is_at_the_foot_of_a_turned_page(int rotate) => A_footer_is_at_the_foot_of_the_page_as_shown(rotate);

    [Theory]
    [InlineData(0)]
    public void A_footer_is_at_the_foot_of_the_page_as_shown(int rotate)
    {
        var hf = new DeskHeaderFooter { FooterEnabled = true, FooterCenter = "MMM", FontSize = 12, ColorHex = "#000000" };
        var stamped = TestPdf.WriteTemp(new StampService().ApplyHeaderFooter(File.ReadAllBytes(Turned(rotate)), hf, [0], "t.pdf", DateTimeOffset.UnixEpoch));
        var (inPlace, elsewhere) = Dark(stamped, 0.3, 0.7, 0.8, 1);
        Assert.True(inPlace > 0, "no footer at the foot of the page as shown");
        Assert.Equal(0, elsewhere);
    }

    /// <summary>Library item PDF-L8 (chuvadi-pdf 3.32.0): <c>WatermarkStamper</c> writes on the unturned page, so on a
    /// page with /Rotate a level watermark reads sideways (upside down at 180).</summary>
    [Theory(Skip = "Library item PDF-L8: WatermarkStamper ignores the page's /Rotate (a level watermark reads sideways on the page as shown)")]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public void A_watermark_is_level_on_a_turned_page(int rotate) => A_watermark_is_across_the_middle_of_the_page_as_shown(rotate);

    [Theory]
    [InlineData(0)]
    public void A_watermark_is_across_the_middle_of_the_page_as_shown(int rotate)
    {
        var wm = new DeskWatermark { Text = "MMMMMM", FontSize = 20, Opacity = 1, RotationDegrees = 0, ColorHex = "#000000" };
        var stamped = TestPdf.WriteTemp(new StampService().ApplyWatermark(File.ReadAllBytes(Turned(rotate)), wm, [0]));
        // Level text, centred: wider than tall, in the middle band.
        var (inPlace, elsewhere) = Dark(stamped, 0.1, 0.9, 0.35, 0.65);
        Assert.True(inPlace > 0, "no watermark across the middle of the page as shown");
        Assert.Equal(0, elsewhere);
    }

    [Fact]
    public async Task A_turned_page_is_exported_as_shown()
    {
        var folder = Path.Combine(Path.GetTempPath(), $"turned-export-{Guid.NewGuid():N}");
        try
        {
            await new ExportService().ExportAsync(Turned(90), folder, ExportFormat.Svg, false, 0, 96, "svg");
            await new ExportService().ExportAsync(Turned(90), folder, ExportFormat.Png, false, 0, 72, "png");
            Assert.Equal((400d, 200d), SizeOf(File.ReadAllText(Path.Combine(folder, "svg.svg"))));
            var png = File.ReadAllBytes(Path.Combine(folder, "png.png"));
            Assert.Equal(400, (png[16] << 24) | (png[17] << 16) | (png[18] << 8) | png[19]);   // IHDR width
            Assert.Equal(200, (png[20] << 24) | (png[21] << 16) | (png[22] << 8) | png[23]);   // IHDR height
        }
        finally
        {
            Directory.Delete(folder, true);
        }
    }

    // ── The bench ──

    private static BenchPage BenchOf(string path) => new() { SourcePath = path, SourceName = "t.pdf", SourceIndex = 0, OriginalIndex = 0 };

    /// <summary>The middle of the red square on the page as shown, and the shown page's size in pixels.</summary>
    private static (double X, double Y, int W, int H) RedSquare(string path)
    {
        using var doc = PdfDocument.Open(path);
        var b = new PageRasterizer(doc.Objects, new RenderOptions { Dpi = 72, ApplyPageRotation = true, Background = ColorF.White }).Rasterize(doc.Pages[0]);
        double sx = 0, sy = 0;
        var n = 0;
        for (var y = 0; y < b.Height; y++)
        {
            for (var x = 0; x < b.Width; x++)
            {
                var p = b.GetPixelBgra(x, y);
                if (!TestPdf.IsReddish((p.R, p.G, p.B))) continue;
                sx += x; sy += y; n++;
            }
        }

        Assert.True(n > 0, "the red square is gone");
        return (sx / n / b.Width, sy / n / b.Height, b.Width, b.Height);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task A_turned_page_goes_through_the_bench_as_shown(int rotate)
    {
        var outp = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([BenchOf(Turned(rotate))]));
        var red = RedSquare(outp);
        Assert.Equal(Red(rotate).X, red.X, 0.02);
        Assert.Equal(Red(rotate).Y, red.Y, 0.02);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task Turning_a_turned_page_on_the_bench_adds_to_its_turn(int rotate)
    {
        var page = BenchOf(Turned(rotate));
        page.Rotation = 90;
        var outp = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([page]));
        var red = RedSquare(outp);
        Assert.Equal(Red((rotate + 90) % 360).X, red.X, 0.02);
        Assert.Equal(Red((rotate + 90) % 360).Y, red.Y, 0.02);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task Cropping_a_turned_page_cuts_what_was_marked_on_screen(int rotate)
    {
        // The quarter of the page as shown that holds the red square.
        var (rx, ry) = Red(rotate);
        double qx = rx < 0.5 ? 0 : 0.5, qy = ry < 0.5 ? 0 : 0.5;
        var page = BenchOf(Turned(rotate));
        page.Crop = new CropRect(qx, qy, 0.5, 0.5);
        var outp = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([page]));
        var red = RedSquare(outp);
        bool sideways = rotate is 90 or 270;
        Assert.Equal(sideways ? 200 : 100, red.W);
        Assert.Equal(sideways ? 100 : 200, red.H);
        Assert.Equal((rx - qx) / 0.5, red.X, 0.03);
        Assert.Equal((ry - qy) / 0.5, red.Y, 0.03);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task Masking_a_turned_page_keeps_what_was_marked_on_screen(int rotate)
    {
        // Keep the quarter of the page as shown that holds the blue square; the red one is whitened, in place.
        var (bx, by) = Blue(rotate);
        var page = BenchOf(Turned(rotate));
        page.Crop = new CropRect(bx < 0.5 ? 0 : 0.5, by < 0.5 ? 0 : 0.5, 0.5, 0.5);
        page.CropMode = CropFit.Mask;
        var outp = TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([page]));
        Assert.True(TestPdf.IsBluish(Shown(outp, bx, by)), "the blue square is kept where it was");
        Assert.True(TestPdf.IsWhitish(Shown(outp, Red(rotate).X, Red(rotate).Y)), "the red square is masked");
    }

    [Theory]
    [InlineData(0)]
    [InlineData(90)]
    [InlineData(180)]
    [InlineData(270)]
    public async Task Margins_and_resizing_keep_a_turned_page_as_shown(int rotate)
    {
        var (rx, ry) = Red(rotate);
        var page = BenchOf(Turned(rotate));
        page.Margins = new MarginSet(20, 20, 20, 20);
        var withMargins = RedSquare(TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([page])));
        Assert.Equal(rotate is 90 or 270 ? 400 : 200, withMargins.W);
        Assert.Equal(rx < 0.5, withMargins.X < 0.5);
        Assert.Equal(ry < 0.5, withMargins.Y < 0.5);

        var resized = RedSquare(TestPdf.WriteTemp(await new BenchComposer().ComposeAsync([BenchOf(Turned(rotate))], default, "A4")));
        Assert.Equal(rx < 0.5, resized.X < 0.5);
        Assert.Equal(ry < 0.5, resized.Y < 0.5);
    }
}
