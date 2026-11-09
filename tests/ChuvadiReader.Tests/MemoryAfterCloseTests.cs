using System.Runtime;
using Chuvadi.Pdf.Authoring;
using Chuvadi.Pdf.Graphics;
using Chuvadi.Pdf.Images;
using ChuvadiReader.Core.Reader;
using Xunit;
using Path = System.IO.Path;

namespace ChuvadiReader.Tests;

[CollectionDefinition(nameof(MemoryAfterCloseTests), DisableParallelization = true)]
public sealed class MemoryMeasurementCollection;

/// <summary>
/// Sixteenth patch (Linux 36c): closing a heavy document gives its memory back. Measured on its own (no other test
/// runs alongside), with a large-format page of noise, which takes the raster path the CAD sheets take.
/// </summary>
[Collection(nameof(MemoryAfterCloseTests))]
public sealed class MemoryAfterCloseTests
{
    private static string HeavyLargeFormatPage()
    {
        // 3125 × 2917 random pixels (one per drawn pixel) on a 1500 × 1400 pt page (larger than A2, so it is drawn as one PNG at 150 dpi):
        // the drawn page is ~96 MB of SVG text, above MemoryRelief.HeavyBytes.
        var pixels = new PixelBuffer(3125, 2917);
        var noise = new Random(7);
        for (var y = 0; y < 2917; y++)
        {
            for (var x = 0; x < 3125; x++)
            {
                pixels.SetPixel(x, y, ColorF.FromRgb((float)noise.NextDouble(), (float)noise.NextDouble(), (float)noise.NextDouble(), 1f));
            }
        }
        using var png = new MemoryStream();
        PngEncoder.Encode(new ImageFrame(pixels, ImageColorFormat.Rgba32), png, false);
        var b = PdfDocumentBuilder.Create();
        b.AddPage(new PageSize(1500, 1400)).DrawImage(png.ToArray(), 0, 0, 1500, 1400);
        return TestPdf.WriteTemp(b.ToByteArray());
    }

    private static (long Live, long Committed) Measure()
    {
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        GC.WaitForPendingFinalizers();
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        return (GC.GetTotalMemory(false), GC.GetGCMemoryInfo().TotalCommittedBytes);
    }

    [Fact]
    public async Task Closing_a_heavy_document_brings_memory_back_near_where_it_was()
    {
        var path = HeavyLargeFormatPage();
        MemoryRelief.ResetForTests();
        MemoryRelief.Settle = TimeSpan.Zero;
        var before = Measure();

        var drawnChars = await OpenDrawClose(path);
        await (MemoryRelief.Last ?? Task.CompletedTask).WaitAsync(TimeSpan.FromSeconds(30));
        var after = Measure();

        const long mb = 1024 * 1024;
        Assert.True(drawnChars * sizeof(char) >= MemoryRelief.HeavyBytes, $"the test page is too light ({drawnChars * 2 / mb} MB)");
        Assert.True(after.Live - before.Live < 16 * mb, $"live memory after close: {before.Live / mb} → {after.Live / mb} MB");
        Assert.True(after.Committed - before.Committed < 64 * mb, $"memory kept by the runtime after close: {before.Committed / mb} → {after.Committed / mb} MB");
    }

    [Fact]
    public async Task A_light_document_never_asks_for_a_collection()
    {
        MemoryRelief.ResetForTests();
        var last = MemoryRelief.Last;
        var session = await new ChuvadiPdfReader().OpenAsync(TestPdf.TextPage("light"), "light.pdf");
        await session.RenderPageSvgAsync(0);
        session.Dispose();

        Assert.Same(last, MemoryRelief.Last);
    }

    [Fact]
    public void The_drawn_page_text_is_exactly_what_it_was_before_character_for_character()
    {
        var png = new byte[1000];
        new Random(3).NextBytes(png);
        foreach (var length in new[] { 0, 1, 2, 3, 998, 999, 1000 })
        {
            var (w, h) = ("595.276", "841.89");
            var before = $"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}pt\" height=\"{h}pt\" " +
                         $"viewBox=\"0 0 {w} {h}\" preserveAspectRatio=\"xMidYMid meet\">" +
                         $"<image x=\"0\" y=\"0\" width=\"{w}\" height=\"{h}\" preserveAspectRatio=\"none\" " +
                         $"href=\"{"data:image/png;base64," + Convert.ToBase64String(png, 0, length)}\"/></svg>";

            Assert.Equal(before, ChuvadiPdfSession.RasterSvg(w, h, png, length));
        }
    }

    private static async Task<long> OpenDrawClose(string path)
    {
        var session = await new ChuvadiPdfReader().OpenAsync(path, Path.GetFileName(path));
        var chars = (await session.RenderPageSvgAsync(0)).Length;
        session.Dispose();
        return chars;
    }
}
