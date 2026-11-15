using ChuvadiReader.Mac.Platform;
using Xunit;

namespace ChuvadiReader.Mac.Tests;

public class PrintFitTests
{
    // Letter, landscape, 18 pt margins: the sheet Mac Test's M-26 page should fill.
    private const double X = 18, Y = 18, W = 756, H = 576;

    [Fact]
    public void A_turned_A4_page_fits_inside_a_landscape_letter_sheet()
    {
        var (w, h) = PrintFit.Shown(595, 842, 90);
        Assert.Equal((842d, 595d), (w, h));
        var p = PrintFit.Place(w, h, X, Y, W, H, fitToPage: true);
        Assert.Equal(756d / 842d, p.Scale, 6);
        Assert.True(p.X >= X - 0.001 && p.Y >= Y - 0.001);
        Assert.True(p.X + p.Width <= X + W + 0.001 && p.Y + p.Height <= Y + H + 0.001);
        Assert.Equal(756d, p.Width, 3); // the full printable width — not the upright sheet's 576
    }

    [Theory]
    [InlineData(0, 595, 842)]
    [InlineData(180, 595, 842)]
    [InlineData(270, 842, 595)]
    [InlineData(-90, 842, 595)]
    [InlineData(450, 842, 595)]
    public void Shown_size_follows_the_turn(int rotation, double w, double h)
        => Assert.Equal((w, h), PrintFit.Shown(595, 842, rotation));

    [Fact]
    public void Fit_to_page_makes_a_small_page_larger_and_actual_size_leaves_it()
    {
        var fit = PrintFit.Place(200, 100, X, Y, W, H, fitToPage: true);
        Assert.Equal(3.78, fit.Scale, 2);
        var actual = PrintFit.Place(200, 100, X, Y, W, H, fitToPage: false);
        Assert.Equal(1d, actual.Scale);
        Assert.Equal(X + (W - 200) / 2, actual.X, 6);
        Assert.Equal(Y + (H - 100) / 2, actual.Y, 6);
    }

    [Fact]
    public void Actual_size_still_shrinks_a_page_larger_than_the_sheet()
    {
        var p = PrintFit.Place(2384, 3370, X, Y, W, H, fitToPage: false);
        Assert.True(p.Scale < 1);
        Assert.True(p.Width <= W + 0.001 && p.Height <= H + 0.001);
    }
}
