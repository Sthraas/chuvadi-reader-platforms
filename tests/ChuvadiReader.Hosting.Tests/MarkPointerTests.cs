using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>
/// Mac Test M-27 (S1): a mark drawn with the mouse landed at about "pointer times zoom". A pointer becomes a place on the
/// page in one way only: (pointer − the mark layer's left) ÷ the layer's width, with the layer's rectangle read by the
/// script. The page is zoomed with CSS zoom, and older WebKit reports a rectangle under it in the element's own
/// unzoomed pixels. The script asks the engine once which it does and puts the rectangle right. The live proof is
/// tools/PixelProof/mark-pointer.js (Chromium, WebKit, and Chromium made to report rectangles as older WebKit does).
/// </summary>
public sealed class MarkPointerTests
{
    private static string Ui(params string[] path) =>
        File.ReadAllText(Path.Combine([AppContext.BaseDirectory, "UiSources", .. path]));

    [Theory]
    [InlineData("reader.js", "chuvadiReaderMkRect")]
    [InlineData("redact.js", "chuvadiRedactMkRect")]
    public void The_mark_layers_rectangle_is_the_one_on_screen_on_every_engine(string file, string function)
    {
        var js = Ui("wwwroot", "js", file);
        Assert.Matches(@"window\." + function + @" = function \(page\) \{[^}]*\{ return null; \}\s*return screenRect\(el\);\s*\};", js);
        // The engine is asked, not guessed from its name.
        Assert.Contains("zoom:2;visibility:hidden", js);
        Assert.Contains("chvdUnzoomedRects = Math.abs(probe.getBoundingClientRect().width - 10) < 0.5;", js);
        Assert.Contains("return { left: r.left * zoom, top: r.top * zoom, width: r.width * zoom, height: r.height * zoom };", js);
    }

    [Fact]
    public void A_pointer_becomes_a_place_on_the_page_from_that_rectangle_only()
    {
        var razor = Ui("Pages", "Reader.razor");
        Assert.Contains(@"JS.InvokeAsync<MkRect?>(""chuvadiReaderMkRect"", page)", razor);
        Assert.DoesNotContain("OffsetX", razor);   // offsets under CSS zoom differ between engines too
        Assert.DoesNotContain("_zoom * e.Client", razor);
    }
}
