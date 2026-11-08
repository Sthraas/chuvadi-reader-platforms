using ChuvadiReader.Mac.Platform;
using Xunit;

namespace ChuvadiReader.Mac.Tests;

/// <summary>D-132: the Mac error log never holds what the person was reading.</summary>
public sealed class LogScrubberTests
{
    private static readonly LogScrubber Scrub = new(new byte[16]);

    [Theory]
    [InlineData("Could not find file '/Users/arun/Documents/Patient chart 2026.pdf'.", "Patient", "arun", "/Users")]
    [InlineData("Access to the path \"/Volumes/USB/secret plans.docx\" is denied.", "secret", "Volumes", "plans")]
    [InlineData("open failed: /Users/arun/Desktop/budget.xlsx", "budget", "arun", "Desktop")]
    [InlineData("Could not open my annual report.pdf here", "annual", "report", "my annual")]
    [InlineData("file:///Users/arun/Notes/diary.md not found", "diary", "arun", "Notes")]
    public void File_names_and_paths_become_extension_and_hash(string message, string a, string b, string c)
    {
        var s = Scrub.Clean(message);
        Assert.DoesNotContain(a, s);
        Assert.DoesNotContain(b, s);
        Assert.DoesNotContain(c, s);
        Assert.Matches(@"<\.(pdf|docx|xlsx|md) #[0-9a-f]{8}>|<file:// #[0-9a-f]{8}>", s);
    }

    [Fact]
    public void Quoted_values_are_hashed_so_passwords_and_document_text_stay_out()
    {
        var s = Scrub.Clean("Wrong password 'hunter2' for the file; text near \"Diagnosis: carcinoma\" failed to parse");
        Assert.DoesNotContain("hunter2", s);
        Assert.DoesNotContain("carcinoma", s);
        Assert.Matches("<text #[0-9a-f]{8}>", s);
        Assert.Contains("Wrong password", s); // the shape of the failure stays readable
    }

    [Fact]
    public void Links_keep_only_scheme_and_host()
    {
        var s = Scrub.Clean("There was an error trying to open URL: https://example.org/records/42?patient=Ravi");
        Assert.Contains("<https://example.org #", s);
        Assert.DoesNotContain("records", s);
        Assert.DoesNotContain("Ravi", s);
    }

    [Fact]
    public void Ordinary_apostrophes_are_not_quotes()
    {
        Assert.Equal("Can't render: the renderer isn't ready", Scrub.Clean("Can't render: the renderer isn't ready"));
    }

    [Fact]
    public void Same_name_gives_the_same_hash_and_a_different_salt_a_different_one()
    {
        var a = Scrub.Clean("x '/Users/a/b.pdf'");
        Assert.Equal(a, Scrub.Clean("x '/Users/a/b.pdf'"));
        var other = new LogScrubber(Enumerable.Repeat((byte)7, 16).ToArray());
        Assert.NotEqual(a, other.Clean("x '/Users/a/b.pdf'"));
    }

    [Fact]
    public void Code_names_that_contain_an_extension_are_kept()
    {
        Assert.Equal("Version 3.31.2 of Chuvadi.Pdf.dll failed", Scrub.Clean("Version 3.31.2 of Chuvadi.Pdf.dll failed"));
    }

    [Fact]
    public void Long_messages_are_capped()
    {
        var s = Scrub.Clean(new string('x', 5000));
        Assert.True(s.Length <= LogScrubber.MaxMessage + 1);
    }

    [Fact]
    public void Stack_traces_keep_code_names_and_lose_file_paths()
    {
        var s = Scrub.CleanStack("   at ChuvadiReader.Ui.Pages.Reader.OnOpen() in /Users/runner/work/x/Reader.razor:line 12\n   at System.Threading.Tasks.Task.Run()");
        Assert.Contains("ChuvadiReader.Ui.Pages.Reader.OnOpen()", s);
        Assert.DoesNotContain("/Users/runner", s);
    }
}
