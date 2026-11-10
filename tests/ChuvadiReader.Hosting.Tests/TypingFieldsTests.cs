using System.Text.RegularExpressions;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>
/// Android Test AT-10 drift guard: a text field the person types into is bound with <c>@bind</c> (or
/// <c>@bind:get/@bind:set</c>), never <c>value="@x"</c> plus <c>@oninput</c>. With the second form every answer
/// from the app writes the field back to what it had seen so far, so keys typed in between are lost
/// ("burstwordtest" became "burtwordt" in the Find box). <c>@bind</c> tells Blazor the field already holds
/// the typed text. Sliders, number boxes and colour pickers aren't typed into, so they're left alone.
/// </summary>
public sealed class TypingFieldsTests
{
    private static readonly Regex InputTag = new(@"<input\b[^>]*>", RegexOptions.Singleline);
    private static readonly Regex NotTyped = new(@"type=""(range|number|color|checkbox|radio|file)""");

    [Fact]
    public void Typed_fields_never_pair_a_one_way_value_with_oninput()
    {
        var dir = Path.Combine(AppContext.BaseDirectory, "UiSources");
        var files = Directory.GetFiles(dir, "*.razor", SearchOption.AllDirectories);
        Assert.True(files.Length > 20, "Ui sources not copied");

        var leaks = (from f in files
                     let text = File.ReadAllText(f)
                     from Match m in InputTag.Matches(text)
                     where m.Value.Contains("value=\"@") && m.Value.Contains("@oninput") && !NotTyped.IsMatch(m.Value)
                     let line = text[..m.Index].Count(c => c == '\n') + 1
                     select $"{Path.GetRelativePath(dir, f)}:{line}").ToList();

        Assert.Empty(leaks);
    }
}

/// <summary>Nineteenth patch (Linux finding 3): the Reader keys every PageSvg by its document.</summary>
public sealed class PageKeyTests
{
    [Fact]
    public void Every_page_the_Reader_draws_is_keyed_by_its_document()
    {
        var reader = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UiSources", "Pages", "Reader.razor"));
        var pages = Regex.Matches(reader, @"<PageSvg\b[^>]*>").Select(m => m.Value).ToList();

        Assert.NotEmpty(pages);
        Assert.All(pages, p => Assert.Contains("@key=", p));
        Assert.Contains("_renderToRelease = true;", reader);
    }

    /// <summary>Linux finding 1: a page back in view after its render was cancelled is asked for again.</summary>
    [Fact]
    public void A_cancelled_page_request_never_stops_the_page_being_asked_for_again()
    {
        var reader = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UiSources", "Pages", "Reader.razor"));
        Assert.Contains("(_rendering.TryGetValue((session, n), out var asked) && !asked.IsCancellationRequested)", reader);
    }
}

/// <summary>H-20 (D-134, D-151): every tools rail shows TOOLS; a screen reader still hears the mode's name.</summary>
public sealed class ToolsRailHeadingTests
{
    [Fact]
    public void Every_tools_rail_shows_TOOLS_and_keeps_its_mode_name_for_screen_readers()
    {
        var dir = Path.Combine(AppContext.BaseDirectory, "UiSources");
        var rails = Directory.GetFiles(dir, "*.razor", SearchOption.AllDirectories)
            .SelectMany(f => Regex.Matches(File.ReadAllText(f), @"<SideRail\b[^>]*Kind=""tools""[^>]*>").Select(m => (File: Path.GetFileName(f), Tag: m.Value)))
            .ToList();
        var labels = rails.Select(r => Regex.Match(r.Tag, @"\bLabel=""([^""]*)""").Groups[1].Value).ToList();

        Assert.Equal(6, rails.Count);
        Assert.All(rails, r => Assert.Contains(@"Heading=""TOOLS""", r.Tag));
        // The view-only document's rail always said TOOLS and has no mode name; the other five keep theirs.
        Assert.Equal(["", "ARRANGE", "MARK", "PROTECT", "PROTECT", "READ"], labels.Order().ToList());

        var rail = File.ReadAllText(Path.Combine(dir, "Components", "Rails", "SideRail.razor"));
        Assert.Contains(@"aria-label=""@(Label ?? Heading)""", rail);
    }
}
