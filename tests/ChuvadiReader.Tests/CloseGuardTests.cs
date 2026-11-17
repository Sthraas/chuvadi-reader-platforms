using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>D-190: a tab with unsaved marks is asked about before it closes, and before the app closes; Cancel
/// keeps everything. D-186 Q3 B: the marks are the tab's.</summary>
public sealed class CloseGuardTests
{
    private sealed class Marks(int count) : ITabMarks
    {
        public int Count { get; private set; } = count;
        public bool HasUnsaved => Count > 0;
        public void Discard() => Count = 0;
    }

    private static async Task<(TabsService Tabs, ReaderTab A, ReaderTab B, ReaderTab C)> ThreeTabsAsync()
    {
        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        var a = await tabs.OpenAsync(TestPdf.TextPage("a"), "a.pdf", DocumentFormat.Pdf);
        var b = await tabs.OpenAsync(TestPdf.TextPage("b"), "b.pdf", DocumentFormat.Pdf);
        var c = await tabs.OpenAsync(TestPdf.TextPage("c"), "c.pdf", DocumentFormat.Pdf);
        return (tabs, a, b, c);
    }

    [Fact]
    public async Task With_nothing_unsaved_nothing_is_asked()
    {
        var (tabs, a, _, _) = await ThreeTabsAsync();
        int asked = 0;
        tabs.CloseGuard = _ => { asked++; return Task.FromResult(false); };

        Assert.False(tabs.HasUnsavedMarks);
        Assert.True(await tabs.ConfirmCloseAllAsync());
        await tabs.CloseAsync(a.Id);
        Assert.Equal(2, tabs.Tabs.Count);
        await tabs.CloseAllAsync();
        Assert.Empty(tabs.Tabs);
        Assert.Equal(0, asked);
    }

    [Fact]
    public async Task Cancel_keeps_the_tab_and_its_marks_and_go_ahead_closes_it()
    {
        var (tabs, a, b, _) = await ThreeTabsAsync();
        a.Marks = new Marks(2);
        var askedAbout = new List<string>();
        bool answer = false;
        tabs.CloseGuard = unsaved => { askedAbout.AddRange(unsaved.Select(t => t.FileName)); return Task.FromResult(answer); };

        Assert.True(tabs.HasUnsavedMarks);
        await tabs.CloseAsync(a.Id);
        Assert.Contains(a, tabs.Tabs);
        Assert.Equal(2, a.Marks.Count);
        Assert.Equal(new[] { "a.pdf" }, askedAbout);

        await tabs.CloseAsync(b.Id);                 // no marks: closes without a question
        Assert.DoesNotContain(b, tabs.Tabs);
        Assert.Single(askedAbout);

        answer = true;
        await tabs.CloseAsync(a.Id);
        Assert.DoesNotContain(a, tabs.Tabs);
    }

    [Fact]
    public async Task Close_others_and_close_all_ask_only_about_the_tabs_that_would_close()
    {
        var (tabs, a, b, c) = await ThreeTabsAsync();   // c is in front
        a.Marks = new Marks(1);
        c.Marks = new Marks(1);
        List<string>? askedAbout = null;
        bool answer = false;
        tabs.CloseGuard = unsaved => { askedAbout = unsaved.Select(t => t.FileName).ToList(); return Task.FromResult(answer); };

        await tabs.CloseOthersAsync();
        Assert.Equal(new[] { "a.pdf" }, askedAbout);   // not c: it stays
        Assert.Equal(3, tabs.Tabs.Count);

        await tabs.CloseAllAsync();
        Assert.Equal(new[] { "a.pdf", "c.pdf" }, askedAbout);
        Assert.Equal(3, tabs.Tabs.Count);

        answer = true;
        await tabs.CloseOthersAsync();
        Assert.Equal(new[] { c }, tabs.Tabs);
        Assert.Same(c, tabs.Active);
        _ = b;
    }

    [Fact]
    public async Task The_app_close_question_closes_no_tab_and_puts_the_front_tab_back()
    {
        var (tabs, a, b, c) = await ThreeTabsAsync();
        a.Marks = new Marks(1);
        tabs.CloseGuard = async unsaved =>
        {
            await tabs.ActivateAsync(unsaved[0].Id);   // the shell shows the file it asks about
            unsaved[0].Marks!.Discard();
            return true;
        };

        Assert.True(await tabs.ConfirmCloseAllAsync());
        Assert.Equal(3, tabs.Tabs.Count);
        Assert.Same(c, tabs.Active);
        Assert.False(tabs.HasUnsavedMarks);
        _ = b;
    }

    [Fact]
    public async Task A_second_question_while_one_is_on_screen_answers_stay_open()
    {
        var (tabs, a, _, _) = await ThreeTabsAsync();
        a.Marks = new Marks(1);
        var onScreen = new TaskCompletionSource<bool>();
        tabs.CloseGuard = _ => onScreen.Task;

        var first = tabs.ConfirmCloseAllAsync();
        Assert.False(await tabs.ConfirmCloseAllAsync());   // e.g. the close button pressed again
        onScreen.SetResult(true);
        Assert.True(await first);
    }

    [Fact]
    public async Task Bookmark_edits_and_redaction_areas_are_asked_about_like_marks()
    {
        var (tabs, a, b, c) = await ThreeTabsAsync();
        a.Bookmarks = new Marks(3);            // D-195: bookmarks edited, not saved
        b.Redactions = new Marks(2);           // redaction areas in no redacted copy yet
        List<string>? askedAbout = null;
        tabs.CloseGuard = unsaved => { askedAbout = unsaved.Select(t => t.FileName).ToList(); return Task.FromResult(false); };

        Assert.True(a.HasUnsavedWork);
        Assert.False(a.HasUnsavedMarks);       // marks only
        Assert.True(tabs.HasUnsavedMarks);
        Assert.False(await tabs.ConfirmCloseAllAsync());
        Assert.Equal(new[] { "a.pdf", "b.pdf" }, askedAbout);
        await tabs.CloseAsync(b.Id);
        Assert.Contains(b, tabs.Tabs);         // Cancel keeps it
        _ = c;
    }

    [Fact]
    public async Task A_file_open_only_in_Protect_keeps_its_areas_and_is_asked_about_when_the_app_closes()
    {
        var (tabs, a, _, _) = await ThreeTabsAsync();

        var holder = tabs.WorkHolderFor("/elsewhere/contract.pdf", "contract.pdf");
        Assert.True(tabs.IsDetached(holder));
        Assert.DoesNotContain(holder, tabs.Tabs);                                     // never a tab in the strip
        Assert.Same(holder, tabs.WorkHolderFor("/ELSEWHERE/contract.pdf", "contract.pdf"));
        Assert.False(tabs.HasUnsavedMarks);

        holder.Redactions = new Marks(4);
        Assert.True(tabs.HasUnsavedMarks);
        List<string>? askedAbout = null;
        tabs.CloseGuard = unsaved => { askedAbout = unsaved.Select(t => t.FileName).ToList(); return Task.FromResult(true); };
        Assert.True(await tabs.ConfirmCloseAllAsync());
        Assert.Equal(new[] { "contract.pdf" }, askedAbout);

        // A file that has a tab keeps its work with the tab.
        Assert.Same(a, tabs.WorkHolderFor(a.Path, a.FileName));
        Assert.False(tabs.IsDetached(a));
    }
}
