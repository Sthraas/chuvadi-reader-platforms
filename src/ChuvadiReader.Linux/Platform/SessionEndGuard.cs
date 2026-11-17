namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// D-194: a sign-out or shutdown with unsaved work is held, and the person is asked first. On Linux the desktop
/// ends the session without asking the window to close, and it can only be held by a lock on the session taken
/// beforehand (<c>chvd_session_hold</c>). So the lock is taken when unsaved work appears and given up when it
/// goes (<see cref="Refresh"/>, on <c>IUnsavedWork.Changed</c>), and when the desktop says the session is about
/// to end (<see cref="OnSessionEnding"/>) the window is asked to close: that is the close the window already
/// asks about (<see cref="WindowCloseGuard"/>: Save / Save as / Discard / Cancel), and once every file has an
/// answer the window closes, the lock goes with the process, and the sign-out goes on.
/// </summary>
/// <param name="hasUnsavedWork"><c>IUnsavedWork.HasUnsavedWork</c>.</param>
/// <param name="hold">Takes the session lock (true) or gives it up (false). The window's thread.</param>
/// <param name="requestClose">Asks the window to close, as its close button does.</param>
public sealed class SessionEndGuard(Func<bool> hasUnsavedWork, Action<bool> hold, Action requestClose)
{
    private bool _held;

    /// <summary>Takes or gives up the lock to match the unsaved work. The window's thread.</summary>
    public void Refresh()
    {
        bool unsaved = hasUnsavedWork();
        if (unsaved != _held)
        {
            _held = unsaved;
            hold(unsaved);
        }
    }

    /// <summary>The desktop is about to end the session and waits a moment. The window's thread.</summary>
    public void OnSessionEnding()
    {
        Refresh(); // the lock must be in place before the desktop gets its answer
        if (_held)
        {
            requestClose();
        }
    }
}
