using ChuvadiReader.Platform;
using ChuvadiReader.Web.Platform;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.JSInterop;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-181: the browser asks before leaving only while an open document has unsaved marks (D-190's answer).</summary>
public class LeaveGuardTests
{
    private sealed class FakeCommands : IAppCommands, IUnsavedWork
    {
        private readonly List<AppCommandInfo> _list = [new("r.find", "Find", "Read", "Ctrl F", true)];

        public IReadOnlyList<AppCommandInfo> Commands => _list;

        public IReadOnlyList<AppCommandInfo> DocumentMenu => [];

        public event Action? Changed;

        public Task<bool> InvokeAsync(string id) => Task.FromResult(false);

        /// <summary>What the kit says closing would lose; the Ui's commands change whenever marks do.</summary>
        public bool Unsaved { get; private set; }

        public bool HasUnsavedWork => Unsaved;

        public int Asked { get; private set; }

        public Task<bool> ConfirmCloseAsync()
        {
            Asked++;
            return Task.FromResult(true);
        }

        event Action? IUnsavedWork.Changed
        {
            add => WorkChanged += value;
            remove => WorkChanged -= value;
        }

        private event Action? WorkChanged;

        public int WorkListeners => WorkChanged?.GetInvocationList().Length ?? 0;

        /// <summary>Unsaved work that no Reader command reflects (Arrange's desks): only the kit's signal tells.</summary>
        public void Desks(bool unsaved)
        {
            Unsaved = unsaved;
            WorkChanged?.Invoke();
        }

        public void Marks(bool? unsaved)
        {
            Unsaved = unsaved == true;
            Changed?.Invoke();
        }

        public int Listeners => Changed?.GetInvocationList().Length ?? 0;
    }

    private sealed class RecordingJs : IJSRuntime
    {
        public List<bool> Told { get; } = new();

        public bool Fail { get; set; }

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, object?[]? args) => InvokeAsync<TValue>(identifier, CancellationToken.None, args);

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, CancellationToken cancellationToken, object?[]? args)
        {
            Assert.Equal("chvdPortal.guardLeave", identifier);
            if (Fail)
            {
                throw new JSDisconnectedException("the page is gone");
            }

            Told.Add((bool)args![0]!);
            return ValueTask.FromResult(default(TValue)!);
        }
    }

    [Fact]
    public void The_browser_is_told_only_when_unsaved_marks_appear_or_go()
    {
        var commands = new FakeCommands();
        var js = new RecordingJs();
        using var guard = new LeaveGuard(commands, commands, new BrowserBridge(js), NullLogger<LeaveGuard>.Instance);

        commands.Marks(true); // before the page can run script: nothing is sent
        Assert.Empty(js.Told);

        guard.Start();
        guard.Start(); // once
        Assert.Equal([true], js.Told);
        Assert.True(guard.HasUnsavedMarks);

        commands.Marks(true);  // more marks, other commands changing: no repeat
        commands.Marks(true);
        Assert.Equal([true], js.Told);

        commands.Marks(false); // saved into the file, or cleared
        Assert.Equal([true, false], js.Told);

        commands.Marks(null);  // the Reader isn't the page any more
        commands.Marks(false);
        Assert.Equal([true, false], js.Told);

        commands.Marks(true);
        Assert.Equal([true, false, true], js.Told);
    }

    [Fact]
    public void Nothing_unsaved_at_the_start_sends_nothing_and_a_gone_page_is_not_an_error()
    {
        var commands = new FakeCommands();
        var js = new RecordingJs();
        var guard = new LeaveGuard(commands, commands, new BrowserBridge(js), NullLogger<LeaveGuard>.Instance);
        guard.Start();
        Assert.Empty(js.Told);

        js.Fail = true;
        commands.Marks(true); // the page is already leaving: swallowed
        Assert.Empty(js.Told);

        guard.Dispose();
        Assert.Equal(0, commands.Listeners); // stops following the Ui
        Assert.Equal(0, commands.WorkListeners);
        Assert.Equal(0, commands.Asked);     // the guard only reads; the Ui's card is never raised by it
    }

    [Fact]
    public void Unsaved_work_that_no_reader_command_shows_arms_the_browser_too()
    {
        // D-194: Arrange's desks, neither bound nor saved, count as unsaved work; only the kit's own signal tells.
        var commands = new FakeCommands();
        var js = new RecordingJs();
        using var guard = new LeaveGuard(commands, commands, new BrowserBridge(js), NullLogger<LeaveGuard>.Instance);
        guard.Start();
        commands.Desks(true);
        commands.Desks(true);
        Assert.Equal([true], js.Told);
        commands.Desks(false); // bound, saved in a session, or discarded on the card
        Assert.Equal([true, false], js.Told);
    }
}
