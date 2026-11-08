using ChuvadiReader.Linux.Platform;
using ChuvadiReader.Platform;
using Xunit;
using static ChuvadiReader.Platform.WindowButton;

namespace ChuvadiReader.Linux.Tests;

/// <summary>The window buttons follow the desktop's layout exactly, parsed as GTK 4.14's header bar does.</summary>
public class GtkButtonLayoutTests
{
    [Theory]
    // Vanilla GNOME: close only, on the right.
    [InlineData("appmenu:close", "", "Close")]
    // Ubuntu, KDE's GTK default.
    [InlineData(":minimize,maximize,close", "", "Minimize Maximize Close")]
    [InlineData("menu:minimize,maximize,close", "", "Minimize Maximize Close")]
    // macOS-like, all on the left, in the order given.
    [InlineData("close,minimize,maximize:", "Close Minimize Maximize", "")]
    [InlineData("close,maximize,minimize:appmenu", "Close Maximize Minimize", "")]
    // Split across both ends.
    [InlineData("close:maximize", "Close", "Maximize")]
    [InlineData("minimize:close", "Minimize", "Close")]
    // Any subset, any order.
    [InlineData(":close,minimize", "", "Close Minimize")]
    [InlineData(":maximize", "", "Maximize")]
    // No window buttons at all.
    [InlineData("appmenu:", "", "")]
    [InlineData("", "", "")]
    [InlineData(":", "", "")]
    // No ':' — everything is the left end (GTK: tokens[1] is NULL for the right end).
    [InlineData("close,minimize", "Close Minimize", "")]
    // Only the first ':' splits; the rest belongs to the right end's names (so "x:close" is not close).
    [InlineData("close:minimize:maximize", "Close", "")]
    [InlineData("close:maximize,minimize:close", "Close", "Maximize")]
    // icon, menu, appmenu, spacer and unknown names are not window buttons.
    [InlineData("icon,menu:spacer,minimize,foo,close", "", "Minimize Close")]
    // Exact names, as GTK's strcmp: no trimming, no case folding.
    [InlineData(": close,Minimize,maximize ", "", "")]
    // Named twice, drawn twice (GTK does).
    [InlineData("close:close", "Close", "Close")]
    public void Parses_like_gtk(string layout, string left, string right)
    {
        var parsed = GtkButtonLayout.Parse(layout);
        Assert.Equal(left, string.Join(' ', parsed.Left));
        Assert.Equal(right, string.Join(' ', parsed.Right));
    }

    [Fact]
    public void Unset_means_the_usual_three_on_the_right()
    {
        var parsed = GtkButtonLayout.Parse(null);
        Assert.Empty(parsed.Left);
        Assert.Equal([Minimize, Maximize, Close], parsed.Right);
    }

    [Theory]
    [InlineData("appmenu:close", WindowButtons.Right)]
    [InlineData("close,minimize,maximize:", WindowButtons.Left)]
    [InlineData("close:maximize", WindowButtons.Left)]
    [InlineData("minimize:close", WindowButtons.Right)]
    [InlineData("minimize:", WindowButtons.Left)]
    [InlineData("appmenu:", WindowButtons.Right)]
    public void Side_is_where_close_is(string layout, WindowButtons side) =>
        Assert.Equal(side, GtkButtonLayout.SideOf(GtkButtonLayout.Parse(layout)));
}
