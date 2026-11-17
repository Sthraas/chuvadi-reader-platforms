using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>D-194: Arrange knows when desks have changed since they were last bound to a PDF or saved in a
/// session, says so when that changes, and is asked about before the app closes.</summary>
public sealed class BenchUnsavedTests
{
    private static BenchService NewBench() =>
        new(new PlaceholderPdfReader(), new BenchComposer(), new ExportService());

    [Fact]
    public void An_empty_Arrange_has_nothing_unsaved_and_pages_on_a_desk_are_unsaved()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        int told = 0;
        bench.UnsavedChanged += () => told++;
        Assert.False(bench.HasUnsavedWork);

        bench.AddBlankToDesk(bench.Desks[0].Id);
        Assert.True(bench.HasUnsavedWork);
        Assert.Equal(1, bench.UnsavedDeskCount);
        Assert.Equal(1, told);

        bench.AddBlankToDesk(bench.Desks[0].Id);     // more of the same: still unsaved, nothing new to tell
        Assert.Equal(1, told);
    }

    [Fact]
    public void A_bound_desk_is_kept_until_it_changes_and_undoing_the_change_makes_it_kept_again()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        var desk = bench.Desks[0];
        bench.AddBlankToDesk(desk.Id);
        bench.AddBlankToDesk(desk.Id);

        bench.MarkDeskKept(desk.Id);
        Assert.False(bench.HasUnsavedWork);

        bench.ReverseDesk(desk.Id);
        Assert.True(bench.HasUnsavedWork);
        bench.Undo();
        Assert.False(bench.HasUnsavedWork);          // back to exactly what was bound
        bench.Redo();
        Assert.True(bench.HasUnsavedWork);
    }

    [Fact]
    public void Each_desk_is_counted_by_itself_and_a_session_save_keeps_them_all()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        var first = bench.Desks[0];
        bench.AddBlankToDesk(first.Id);
        var second = bench.AddDesk();
        bench.AddBlankToDesk(second.Id);
        Assert.Equal(2, bench.UnsavedDeskCount);

        bench.MarkDeskKept(first.Id);                 // one desk bound: the other is still unsaved
        Assert.True(bench.HasUnsavedWork);
        Assert.Equal(1, bench.UnsavedDeskCount);

        bench.MarkAllKept();                          // session saved
        Assert.False(bench.HasUnsavedWork);

        bench.AddDesk();                              // an empty desk is nothing to lose
        Assert.False(bench.HasUnsavedWork);
        bench.RemoveDesk(second.Id);                  // removing a kept desk leaves nothing unsaved either
        Assert.False(bench.HasUnsavedWork);
    }

    [Fact]
    public void Starting_over_leaves_nothing_unsaved()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        bench.AddBlankToDesk(bench.Desks[0].Id);
        Assert.True(bench.HasUnsavedWork);
        bench.Reset();
        Assert.False(bench.HasUnsavedWork);
    }

    [Fact]
    public async Task The_close_question_is_asked_only_when_something_is_unsaved()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        int asked = 0;
        bool answer = false;
        bench.CloseGuard = () => { asked++; return Task.FromResult(answer); };

        Assert.True(await bench.ConfirmCloseAsync());
        Assert.Equal(0, asked);

        bench.AddBlankToDesk(bench.Desks[0].Id);
        Assert.False(await bench.ConfirmCloseAsync());   // Cancel
        answer = true;
        Assert.True(await bench.ConfirmCloseAsync());
        Assert.Equal(2, asked);

        bench.CloseGuard = null;                          // no Ui up: never trap the person
        Assert.True(await bench.ConfirmCloseAsync());
    }

    [Fact]
    public async Task A_session_just_opened_is_as_its_file_holds_it()
    {
        var bench = NewBench();
        bench.EnsureDesk();
        bench.AddBlankToDesk(bench.Desks[0].Id);
        var session = bench.ExportSession();

        var other = NewBench();
        await other.ImportSessionAsync(session);
        Assert.False(other.HasUnsavedWork);
        other.AddBlankToDesk(other.Desks[0].Id);
        Assert.True(other.HasUnsavedWork);
    }
}
