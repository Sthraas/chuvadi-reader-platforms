using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>
/// Mobile UI F-1 and F-2 (seen on patch 26): on a page shown turned by its /Rotate, Find's highlight was drawn where
/// the text would be unturned, and Fit page fitted every page by the first page's shape, so a turned page ran off the
/// side of a phone. D-188: Find matches in hidden rows and columns of a sheet are named. The live proof is
/// tools/PixelProof/patch28.js; the mapping itself is tested in PageRotateTests (Core).
/// </summary>
public sealed class TurnedPageUiTests
{
    private static string Ui(params string[] path) =>
        File.ReadAllText(Path.Combine([AppContext.BaseDirectory, "UiSources", .. path]));

    [Fact]
    public void A_sideways_match_gets_its_extra_room_across_the_text()
    {
        var razor = Ui("Pages", "Reader.razor");
        Assert.Contains("width:@Pct(fm.Sideways ? hb.W * 1.3 : hb.W);height:@Pct(fm.Sideways ? hb.H : hb.H * 1.3)", razor);
    }

    [Fact]
    public void While_a_fit_is_on_a_page_of_another_shape_gets_its_own_fit()
    {
        var js = Ui("wwwroot", "js", "reader.js");
        Assert.Contains("export function fitEachPage(deskEl, mode) {", js);
        Assert.Contains("wrap.style.setProperty('--rpage-zoom', s);", js);
        Assert.Contains("wrap.style.removeProperty('--rpage-zoom');", js);   // the person's own zoom: one zoom for all again

        var razor = Ui("Pages", "Reader.razor");
        Assert.Contains(@"InvokeVoidAsync(""fitEachPage"", _desk, tab.FitMode switch { ReaderFitMode.Width => ""width"", ReaderFitMode.Page => ""page"", _ => """" })", razor);
        Assert.Contains("if (tab.FitMode != ReaderFitMode.Free || _pageFitsOn)", razor);
    }

    [Fact]
    public void Find_matches_in_hidden_rows_and_columns_are_named()
    {
        var razor = Ui("Components", "Viewers", "XlsxView.razor");
        Assert.Contains(@"<div class=""xv-hiddenhits"" role=""status"">@hiddenHits</div>", razor);
        Assert.Contains(@"""1 match is in a hidden cell: """, razor);
        Assert.Contains(@"matches are in hidden cells: """, razor);
        Assert.Contains("hidden.Take(5)", razor);
    }
}
