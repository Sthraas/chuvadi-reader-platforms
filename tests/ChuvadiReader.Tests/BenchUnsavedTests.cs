using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>D-203 (was D-194): Arrange's desks are kept for the next start when the person says Save at close, with
/// no file dialog; Discard and Reset clear them. The close question comes only when Arrange was used in this run and
/// its desks differ from what is kept.</summary>
public sealed class BenchUnsavedTests : IDisposable
{
    private sealed class Folder(string root) : IAppPaths
    {
        public string AppDataFolder { get; } = Path.Combine(root, "data");
        public string WorkingFolder { get; } = Path.Combine(root, "work");
        public string? DefaultSaveFolder => null;
    }

    private readonly string _root = Path.Combine(Path.GetTempPath(), "chvd-bench-" + Guid.NewGuid().ToString("N"));

    public void Dispose()
    {
        try { Directory.Delete(_root, true); } catch (IOException) { }
    }

    private BenchService NewBench(out SessionService sessions)
    {
        var paths = new Folder(_root);
        sessions = new SessionService(paths);
        return new(new PlaceholderPdfReader(), new BenchComposer(), new ExportService(), paths, sessions);
    }

    private async Task<BenchService> OpenedBench()
    {
        var bench = NewBench(out _);
        bench.EnsureDesk();
        await bench.EnsureRestoredAsync();
        return bench;
    }

    [Fact]
    public async Task An_Arrange_not_used_in_this_run_is_never_asked_about()
    {
        var bench = NewBench(out _);
        bench.EnsureDesk();
        bench.AddBlankToDesk(bench.Desks[0].Id);       // (only the page does this, after the restore)
        Assert.False(bench.HasUnsavedWork);
        await bench.EnsureRestoredAsync();
        Assert.False(bench.HasUnsavedWork);              // a restore with nothing kept takes the desks as they are
    }

    [Fact]
    public async Task Pages_on_a_desk_are_unsaved_and_the_change_is_told_once()
    {
        var bench = await OpenedBench();
        int told = 0;
        bench.UnsavedChanged += () => told++;
        Assert.False(bench.HasUnsavedWork);

        bench.AddBlankToDesk(bench.Desks[0].Id);
        Assert.True(bench.HasUnsavedWork);
        Assert.Equal(1, bench.UnsavedDeskCount);
        Assert.Equal(1, told);

        bench.AddBlankToDesk(bench.Desks[0].Id);
        Assert.Equal(1, told);
    }

    [Fact]
    public async Task Save_keeps_the_desks_for_the_next_start_with_no_file_dialog()
    {
        var bench = await OpenedBench();
        var desk = bench.Desks[0];
        bench.AddBlankToDesk(desk.Id);
        bench.AddBlankToDesk(desk.Id);
        var second = bench.AddDesk();
        bench.AddBlankToDesk(second.Id);
        Assert.Equal(2, bench.UnsavedDeskCount);

        await bench.KeepAsync();
        Assert.False(bench.HasUnsavedWork);

        bench.ReverseDesk(desk.Id);
        Assert.True(bench.HasUnsavedWork);
        bench.Undo();
        Assert.False(bench.HasUnsavedWork);              // back to exactly what is kept
        bench.RemoveDesk(second.Id);
        Assert.True(bench.HasUnsavedWork);               // a kept desk gone is a change too

        var next = NewBench(out var sessions);           // the next start
        Assert.True(File.Exists(sessions.KeptDesksPath));
        next.EnsureDesk();
        await next.EnsureRestoredAsync();
        Assert.Equal(2, next.Desks.Count(d => !d.IsEmpty));
        Assert.Equal(2, next.Desks.First(d => !d.IsEmpty).Pages.Count);
        Assert.False(next.HasUnsavedWork);
    }

    [Fact]
    public async Task Discard_and_Reset_leave_nothing_for_the_next_start()
    {
        var bench = await OpenedBench();
        bench.AddBlankToDesk(bench.Desks[0].Id);
        await bench.KeepAsync();

        bench.AddBlankToDesk(bench.Desks[0].Id);
        bench.DiscardKept();                             // the close card's Discard
        Assert.False(File.Exists(NewSessions().KeptDesksPath));

        await bench.KeepAsync();
        bench.Reset();
        Assert.False(bench.HasUnsavedWork);
        Assert.False(File.Exists(NewSessions().KeptDesksPath));

        var next = NewBench(out _);
        next.EnsureDesk();
        await next.EnsureRestoredAsync();
        Assert.True(next.IsEmpty);
    }

    [Fact]
    public async Task An_Arrange_emptied_by_hand_is_kept_empty_without_asking()
    {
        var bench = await OpenedBench();
        var desk = bench.Desks[0];
        bench.AddBlankToDesk(desk.Id);
        await bench.KeepAsync();
        int asked = 0;
        bench.CloseGuard = () => { asked++; return Task.FromResult(true); };

        bench.SelectAllInDesk(desk.Id);
        bench.RemoveSelectedAll();
        Assert.True(bench.IsEmpty);
        Assert.True(await bench.ConfirmCloseAsync());
        Assert.Equal(0, asked);
        Assert.False(File.Exists(NewSessions().KeptDesksPath));
    }

    [Fact]
    public async Task The_close_question_is_asked_only_when_something_changed()
    {
        var bench = await OpenedBench();
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
    public async Task A_session_opened_from_a_file_is_not_what_is_kept()
    {
        var bench = await OpenedBench();
        bench.AddBlankToDesk(bench.Desks[0].Id);
        var session = bench.ExportSession();

        var other = await OpenedBench();
        await other.ImportSessionAsync(session);
        Assert.True(other.HasUnsavedWork);               // Save at close would keep it for the next start
    }

    private SessionService NewSessions() => new(new Folder(_root));
}
