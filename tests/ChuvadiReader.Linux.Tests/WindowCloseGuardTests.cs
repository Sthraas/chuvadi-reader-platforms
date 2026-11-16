using ChuvadiReader.Linux.Platform;
using Xunit;

namespace ChuvadiReader.Linux.Tests;

/// <summary>D-190 on Linux: the window's close request with unsaved marks. The window's thread is stood in for
/// by running posted actions where they are posted; the question by a task the test completes.</summary>
public class WindowCloseGuardTests
{
    private sealed class Window
    {
        public bool Unsaved = true;
        public TaskCompletionSource<bool> Answer = new();
        public int Asked, Held, Forward, Closed;
        public WindowCloseGuard Guard;
        private readonly SemaphoreSlim _answered = new(0);

        /// <summary>The person answers; returns when the guard has acted on it (its continuation may run on another thread).</summary>
        public void Reply(bool go) => Settle(() => Answer.SetResult(go));

        public void Fail() => Settle(() => Answer.SetException(new InvalidOperationException("no Ui")));

        private void Settle(Action answer)
        {
            answer();
            Assert.True(_answered.Wait(TimeSpan.FromSeconds(5)), "the guard never acted on the answer");
        }

        public Window() => Guard = new WindowCloseGuard(
            () => Unsaved,
            () => { Asked++; return Answer.Task; },
            () => Held++, () => Forward++,
            () => { Closed++; Guard!.OnCloseRequested(); }, // closing raises a close request again, as GTK does
            a => { a(); _answered.Release(); });

        /// <summary>A close request: true when the window closed (the request was not held).</summary>
        public bool Request()
        {
            var held = Held;
            Guard.OnCloseRequested();
            return Held == held;
        }
    }

    [Fact]
    public void Nothing_unsaved_closes_at_once_without_a_question()
    {
        var w = new Window { Unsaved = false };
        Assert.True(w.Request());
        Assert.Equal(0, w.Asked);
        Assert.Equal(0, w.Forward);
    }

    [Fact]
    public void Unsaved_marks_hold_the_close_bring_the_window_forward_and_ask()
    {
        var w = new Window();
        Assert.False(w.Request());
        Assert.Equal(1, w.Asked);
        Assert.Equal(1, w.Forward);
        Assert.Equal(0, w.Closed);
    }

    [Fact]
    public void Cancel_keeps_the_window_and_the_next_close_asks_again()
    {
        var w = new Window();
        w.Request();
        w.Reply(false);
        Assert.Equal(0, w.Closed);

        w.Answer = new TaskCompletionSource<bool>();
        Assert.False(w.Request());
        Assert.Equal(2, w.Asked);
    }

    [Fact]
    public void An_answer_that_allows_it_closes_the_window_once_and_does_not_ask_again()
    {
        var w = new Window();
        w.Request();
        var held = w.Held;
        w.Reply(true); // Save, Save as or Discard for every file
        Assert.Equal(1, w.Closed);
        Assert.Equal(held, w.Held); // the close it then asks for goes through, even if marks are still unsaved
        Assert.Equal(1, w.Asked);
    }

    [Fact]
    public void A_second_close_while_the_question_is_up_is_held_and_does_not_ask_twice()
    {
        var w = new Window();
        w.Request();
        Assert.False(w.Request());
        Assert.Equal(1, w.Asked);
        Assert.Equal(2, w.Forward);
    }

    [Fact]
    public void If_the_question_cannot_be_shown_the_next_close_goes_through()
    {
        var w = new Window();
        Assert.False(w.Request());
        w.Fail();
        Assert.Equal(0, w.Closed); // not closed behind the person's back
        Assert.True(w.Request()); // and never trapped in the app
    }

    [Fact]
    public void Saved_in_the_meantime_closes_at_once()
    {
        var w = new Window();
        w.Request();
        w.Reply(false);
        w.Unsaved = false;
        Assert.True(w.Request());
        Assert.Equal(1, w.Asked);
    }
}
