using System.Text;
using ChuvadiReader.Linux.Platform;
using Xunit;

namespace ChuvadiReader.Linux.Tests;

/// <summary>The host page is served in the saved theme, so its first paint isn't light parchment in a dark theme.</summary>
public sealed class HostPageThemeTests
{
    private static readonly string HostPage = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "index.html"));

    private static string Apply(string page, string? theme) =>
        Encoding.UTF8.GetString(HostPageTheme.Apply(Encoding.UTF8.GetBytes(page), theme));

    [Theory]
    [InlineData("light")]
    [InlineData("dark")]
    [InlineData("palm")]
    [InlineData("indigo")]
    [InlineData("contrast")]
    public void The_real_host_page_gets_the_saved_theme_on_its_root(string theme)
    {
        var page = Apply(HostPage, theme);
        Assert.StartsWith($"<!DOCTYPE html>\n<html data-theme=\"{theme}\" lang=\"en\"", page.ReplaceLineEndings("\n"));
        Assert.Equal(HostPage.Length + $"data-theme=\"{theme}\" ".Length, page.Length); // nothing else changed
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("neon")]
    [InlineData("dark\" onload=\"x")]
    public void An_unknown_theme_leaves_the_page_as_it_is(string? theme) =>
        Assert.Equal(HostPage, Apply(HostPage, theme));

    [Fact]
    public void A_page_that_already_names_a_theme_or_is_not_the_host_page_is_left_alone()
    {
        Assert.Equal("<html data-theme=\"palm\" lang=\"en\">", Apply("<html data-theme=\"palm\" lang=\"en\">", "dark"));
        Assert.Equal("{\"not\": \"html\"}", Apply("{\"not\": \"html\"}", "dark"));
    }

    [Theory]
    [InlineData("html, body { margin: 0; background: #F2EAD6; }")]
    [InlineData("html[data-theme=\"dark\"] body { background: #1b1410; }")]
    [InlineData("html[data-theme=\"palm\"] body { background: #ebe5c9; }")]
    [InlineData("html[data-theme=\"indigo\"] body { background: #edf0f6; }")]
    [InlineData("html[data-theme=\"contrast\"] body { background: #f5f5f2; }")]
    public void The_host_page_paints_the_same_colour_as_the_window_before_it(string rule)
    {
        // Program.PrePaintColour: the window, the start-up mark's cover and the host page are one flat colour, so
        // nothing changes shade between the window appearing and the app's first render (dark was #100b08 here).
        Assert.Contains(rule, HostPage);
    }
}
