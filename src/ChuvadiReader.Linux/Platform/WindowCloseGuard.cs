namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// D-190: the window does not close over unsaved marks without asking. Every way the window is asked to close
/// (the title bar's close button, Alt F4, the desktop's own Close, the in-app close) raises GTK's close request,
/// and that calls <see cref="OnCloseRequested"/>. With nothing unsaved the close goes on at once, as before.
/// Otherwise the request is held, the window comes forward, the Ui asks about each file (Save / Save as /
/// Discard / Cancel), and the window closes only when the answer allows. The same rules as the Windows host.
/// </summary>
/// <param name="hasUnsavedWork"><c>IUnsavedWork.HasUnsavedWork</c>.</param>
/// <param name="confirmClose"><c>IUnsavedWork.ConfirmCloseAsync</c>: true = close now.</param>
/// <param name="hold">Holds the close request in hand (valid only inside it).</param>
/// <param name="bringForward">Brings the window to the front, out of minimized.</param>
/// <param name="close">Asks the window to close (raises a new close request).</param>
/// <param name="onMain">Runs an action on the window's thread.</param>
public sealed class WindowCloseGuard(
    Func<bool> hasUnsavedWork,
    Func<Task<bool>> confirmClose,
    Action hold,
    Action bringForward,
    Action close,
    Action<Action> onMain)
{
    private bool _confirmed;
    private bool _asking;

    /// <summary>The window's thread, from inside the close request.</summary>
    public void OnCloseRequested()
    {
        if (_confirmed || !hasUnsavedWork())
        {
            return; // nothing to lose, or already answered: the window closes
        }

        hold();
        bringForward();
        if (_asking)
        {
            return; // the question is already on screen
        }

        _asking = true;
        _ = AskThenCloseAsync();
    }

    private async Task AskThenCloseAsync()
    {
        bool go;
        try
        {
            go = await confirmClose().ConfigureAwait(false);
        }
        catch (Exception)
        {
            // The question could not be shown. Never trap the person in the app: the next close goes through.
            onMain(() =>
            {
                _asking = false;
                _confirmed = true;
            });
            return;
        }

        onMain(() =>
        {
            _asking = false;
            if (go)
            {
                _confirmed = true;
                close();
            }
        });
    }
}
