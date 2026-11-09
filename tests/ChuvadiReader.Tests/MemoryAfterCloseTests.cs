using System.Diagnostics;
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
    public MemoryAfterCloseTests()
    {
        // No waiting in tests: the relief runs at once, and its one-minute second pass is off.
        MemoryRelief.Settle = TimeSpan.Zero;
        MemoryRelief.FollowUp = TimeSpan.Zero;
        (MemoryRelief.Last ?? Task.CompletedTask).Wait(TimeSpan.FromSeconds(30));
        MemoryRelief.ResetForTests();
    }

    private static string HeavyLargeFormatPage(int pages = 1)
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
        var image = png.ToArray();
        for (var i = 0; i < pages; i++)
        {
            b.AddPage(new PageSize(1500, 1400)).DrawImage(image, 0, 0, 1500, 1400);
        }

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

    // ── Sixteenth patch, part 2 (Linux step 47): the drawing stops, and a costly drawing counts as heavy ──────────

    private static string BlankA1Sheets(int count)
    {
        var b = PdfDocumentBuilder.Create();
        for (var i = 0; i < count; i++)
        {
            b.AddPage(new PageSize(2384, 1684)).DrawText("Sheet " + (i + 1), 100, 100, "Helvetica", 48, Chuvadi.Pdf.Authoring.Color.FromHex("#000000"));
        }

        return TestPdf.WriteTemp(b.ToByteArray());
    }

    private static string StrokedSheets(int pages, int strokes)
    {
        var b = PdfDocumentBuilder.Create();
        for (var p = 0; p < pages; p++)
        {
            var rnd = new Random(p + 1);
            var page = b.AddPage(new PageSize(2384, 1684));
            for (var i = 0; i < strokes; i++)
            {
                double x = 30 + rnd.NextDouble() * 2324, y = 30 + rnd.NextDouble() * 1624;
                page.DrawLine(x, y, x + (rnd.NextDouble() * 80 - 40), y + (rnd.NextDouble() * 80 - 40), Chuvadi.Pdf.Authoring.Color.FromHex("#000099"), 0.2);
            }
        }

        return TestPdf.WriteTemp(b.ToByteArray());
    }

    [Fact]
    public async Task A_document_whose_drawing_cost_a_lot_gives_memory_back_even_when_its_pages_are_small()
    {
        // A vector CAD sheet keeps a small SVG but costs hundreds of MB to draw (Linux step 47: the relief never ran).
        var path = BlankA1Sheets(2);
        MemoryRelief.ResetForTests();
        var before = Measure();
        var last = MemoryRelief.Last;

        var session = (ChuvadiPdfSession)await new ChuvadiPdfReader().OpenAsync(path, "sheets.pdf");
        long kept = (await session.RenderPageSvgAsync(0)).Length + (await session.RenderPageSvgAsync(1)).Length;
        var drawing = session.RenderAllocatedBytes;
        session.Dispose();
        await (MemoryRelief.Last ?? Task.CompletedTask).WaitAsync(TimeSpan.FromSeconds(30));
        var after = Measure();

        const long mb = 1024 * 1024;
        Assert.True(kept * sizeof(char) < MemoryRelief.HeavyBytes, $"the pages keep {kept * 2 / mb} MB");
        Assert.True(drawing >= MemoryRelief.HeavyDrawingBytes, $"drawing allocated only {drawing / mb} MB");
        Assert.NotSame(last, MemoryRelief.Last);
        Assert.True(after.Committed - before.Committed < 64 * mb, $"memory kept by the runtime after close: {before.Committed / mb} → {after.Committed / mb} MB");
    }

    [Fact]
    public async Task Closing_a_document_while_a_sheet_draws_stops_the_drawing_part_way()
    {
        var path = StrokedSheets(pages: 1, strokes: 12_000);
        var whole = Stopwatch.StartNew();
        using (var full = await new ChuvadiPdfReader().OpenAsync(path, "full.pdf"))
        {
            await full.RenderPageSvgAsync(0);
        }

        whole.Stop();

        var session = (ChuvadiPdfSession)await new ChuvadiPdfReader().OpenAsync(path, "closed.pdf");
        using var started = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => started.Set();
        var render = session.RenderPageSvgAsync(0);
        Assert.True(started.Wait(TimeSpan.FromSeconds(10)));
        var stop = Stopwatch.StartNew();
        session.Dispose();
        var result = await render.WaitAsync(TimeSpan.FromSeconds(30));
        stop.Stop();

        Assert.Equal(string.Empty, result);
        Assert.True(stop.Elapsed < whole.Elapsed / 2, $"stopped after {stop.ElapsedMilliseconds} ms; the whole sheet takes {whole.ElapsedMilliseconds} ms");
    }

    [Fact]
    public async Task A_sheet_that_left_the_view_while_drawing_stops_and_the_next_page_starts()
    {
        // Two vector sheets (A1, many strokes: drawing them is the rasteriser's work, as Linux's CAD stand-in).
        // Sheet 1 starts drawing, then leaves the view; sheet 2 is asked for. Stopped, sheet 2 is ready about one
        // sheet's time later; not stopped, it would wait for the rest of sheet 1 first.
        var path = StrokedSheets(pages: 2, strokes: 12_000);
        var whole = new Stopwatch();
        using (var full = await new ChuvadiPdfReader().OpenAsync(path, "full.pdf"))
        {
            await full.RenderPageSvgAsync(0);   // warms up
            whole.Start();
            await full.RenderPageSvgAsync(1);   // one whole sheet, warm
            whole.Stop();
        }

        using var session = (ChuvadiPdfSession)await new ChuvadiPdfReader().OpenAsync(path, "left.pdf");
        using var started = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => started.Set();
        using var left = new CancellationTokenSource();
        var first = session.RenderPageSvgAsync(0, left.Token);
        Assert.True(started.Wait(TimeSpan.FromSeconds(10)));
        await Task.Delay(whole.Elapsed / 4);   // a quarter of the way into sheet 1
        var stop = Stopwatch.StartNew();
        left.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => first.WaitAsync(TimeSpan.FromSeconds(30)));
        session.BeforeRenderForTests = null;
        var next = await session.RenderPageSvgAsync(1).WaitAsync(TimeSpan.FromSeconds(60));
        stop.Stop();

        Assert.Contains("<svg", next);
        Assert.False(session.TryGetRenderedSvg(0, out _));   // the stopped sheet isn't kept
        Assert.True(stop.Elapsed < whole.Elapsed * 1.4, $"sheet 2 was ready {stop.ElapsedMilliseconds} ms after sheet 1 left; one whole sheet takes {whole.ElapsedMilliseconds} ms");
    }

    private static async Task<long> OpenDrawClose(string path)
    {
        var session = await new ChuvadiPdfReader().OpenAsync(path, Path.GetFileName(path));
        var chars = (await session.RenderPageSvgAsync(0)).Length;
        session.Dispose();
        return chars;
    }
}
