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
