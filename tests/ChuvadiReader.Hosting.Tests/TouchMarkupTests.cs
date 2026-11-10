using System.Text.RegularExpressions;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>
/// AT-15: Mark › Text with a finger. The live proof is tools/PixelProof/touch-markup.js on the tablet preview;
/// these keep the two rules it depends on in the shared Ui's source.
/// </summary>
public sealed class TouchMarkupTests
{
    private static string Ui(params string[] path) =>
        File.ReadAllText(Path.Combine([AppContext.BaseDirectory, "UiSources", .. path]));

    [Fact]
    public void A_finger_pans_instead_of_marking_only_after_a_pen_has_touched_the_desk()
    {
        // Hosts say "pen" when the system supports one (Android always does), so "pen" in data-input
        // alone must never take the finger away from the markup layer.
        var js = Ui("wwwroot", "js", "reader.js");
        var split = Regex.Match(js, @"penSplit = \(e\) => \{(?<body>.*?)\n    \};", RegexOptions.Singleline);
        Assert.True(split.Success, "reader.js: the pen split handler was not found");
        var body = split.Groups["body"].Value;
        Assert.Contains("if (e.pointerType === 'pen') { penSeen = true; return; }", body);
        var gate = body.IndexOf("!penSeen) return;", StringComparison.Ordinal);
        Assert.True(gate >= 0, "the split must return until a pen has been seen");
        Assert.True(gate < body.IndexOf("stopPropagation", StringComparison.Ordinal), "the gate must come before the finger is taken");
        Assert.Single(Regex.Matches(js, @"penSeen = false"));   // only its declaration: once seen, kept for the run
    }

    [Fact]
    public void Every_markup_press_is_tracked_so_pointerup_waits_for_it()
    {
        // A press reads the layer's rectangle from JS before it sets the gesture; pointerup waits for it.
        foreach (var (file, field, presses) in new[]
        {
            ("Reader.razor", "_mkPress", new[] { "MkDown", "StartMove", "StartResize", "StartMoveShape", "StartResizeShape", "StartLineEnd", "StartMoveImage", "StartResizeImage" }),
            ("Redact.razor", "_press", new[] { "MkDown" }),
        })
        {
            var src = Ui("Pages", file);
            foreach (var name in presses)
                Assert.Matches($@"private Task {name}\(PointerEventArgs e[^)]*\) => {field} = {name}Press\(e", src);
            // Every pointerdown handler on the markup layer that awaits the rectangle goes through a tracked press.
            var untracked = Regex.Matches(src, @"private async Task (\w+)\(PointerEventArgs e[^)]*\)\s*\{[^}]*?await CacheLayerRect")
                .Select(m => m.Groups[1].Value).Where(n => !n.EndsWith("Press", StringComparison.Ordinal) && n != "MsDown").ToList();
            Assert.Empty(untracked);
            Assert.Matches($@"private async Task MkUp\(PointerEventArgs e\)\s*\{{\s*if \(!{field}\.IsCompleted\)", src);
        }
    }
}
