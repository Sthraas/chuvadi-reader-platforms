using ChuvadiReader.Linux.Platform;
using Xunit;

namespace ChuvadiReader.Linux.Tests;

/// <summary>D-194 on Linux: when the session lock is taken and given up, and what the desktop's "about to end" does.</summary>
public class SessionEndGuardTests
{
    private sealed class Desk
    {
        public bool Unsaved;
        public readonly List<bool> Holds = [];
        public int Closes;
        public readonly SessionEndGuard Guard;

        public Desk() => Guard = new SessionEndGuard(() => Unsaved, Holds.Add, () => Closes++);
    }

    [Fact]
    public void Nothing_unsaved_takes_no_lock_and_a_sign_out_goes_on()
    {
        var d = new Desk();
        d.Guard.Refresh();
        d.Guard.OnSessionEnding();
        Assert.Empty(d.Holds);
        Assert.Equal(0, d.Closes);
    }

    [Fact]
    public void The_lock_follows_the_unsaved_work_and_is_not_asked_for_twice()
    {
        var d = new Desk { Unsaved = true };
        d.Guard.Refresh();
        d.Guard.Refresh();
        Assert.Equal([true], d.Holds);

        d.Unsaved = false; // saved, or discarded
        d.Guard.Refresh();
        d.Guard.Refresh();
        Assert.Equal([true, false], d.Holds);
    }

    [Fact]
    public void A_sign_out_with_unsaved_work_is_held_and_the_window_asks()
    {
        var d = new Desk { Unsaved = true };
        d.Guard.Refresh();
        d.Guard.OnSessionEnding();
        Assert.Equal([true], d.Holds);
        Assert.Equal(1, d.Closes); // the window's own close: it asks Save / Save as / Discard / Cancel
    }

    [Fact]
    public void A_sign_out_takes_the_lock_itself_when_it_was_not_yet_taken()
    {
        var d = new Desk { Unsaved = true }; // unsaved work the guard has not been told about
        d.Guard.OnSessionEnding();
        Assert.Equal([true], d.Holds);
        Assert.Equal(1, d.Closes);
    }

    [Fact]
    public void After_the_work_is_saved_a_sign_out_gives_the_lock_up_and_goes_on()
    {
        var d = new Desk { Unsaved = true };
        d.Guard.Refresh();
        d.Unsaved = false;
        d.Guard.OnSessionEnding();
        Assert.Equal([true, false], d.Holds);
        Assert.Equal(0, d.Closes);
    }
}
