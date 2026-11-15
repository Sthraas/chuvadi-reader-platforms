using ChuvadiReader.Platform;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// D-181: while the open document has marks not yet saved, the browser asks "Leave site? Changes you made may
/// not be saved" before a reload, a close or a move to another site. A reload brings the tabs back (D-174) but
/// not unsaved marks, which live in the page. "Unsaved" is the Ui's own signal: its "Save as new PDF" command
/// (<c>m.saveas</c>) is enabled exactly while the Reader shows "unsaved" for the open document. The browser is
/// told only when that changes. Scoped (per connection).
/// </summary>
public sealed class LeaveGuard : IDisposable
{
    /// <summary>The Ui command that is enabled while the open document has unsaved marks.</summary>
    public const string UnsavedMarksCommand = "m.saveas";

    private readonly IAppCommands _commands;
    private readonly BrowserBridge _browser;
    private readonly ILogger<LeaveGuard> _log;
    private readonly object _gate = new();
    private bool _started;
    private bool _sent;

    public LeaveGuard(IAppCommands commands, BrowserBridge browser, ILogger<LeaveGuard> log)
    {
        _commands = commands;
        _browser = browser;
        _log = log;
    }

    /// <summary>True while the open document has marks not yet saved into a file.</summary>
    public bool HasUnsavedMarks => _commands.Commands.Any(c => c.Id == UnsavedMarksCommand && c.IsEnabled);

    /// <summary>Starts following the Ui's commands (once the page can run script).</summary>
    public void Start()
    {
        lock (_gate)
        {
            if (_started)
            {
                return;
            }

            _started = true;
        }

        _commands.Changed += Update;
        Update();
    }

    private void Update()
    {
        bool on;
        lock (_gate)
        {
            on = HasUnsavedMarks;
            if (on == _sent)
            {
                return; // the browser already knows
            }

            _sent = on;
        }

        _ = TellAsync(on);
    }

    private async Task TellAsync(bool on)
    {
        try
        {
            await _browser.SetLeaveGuardAsync(on).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is JSDisconnectedException or JSException or OperationCanceledException or InvalidOperationException)
        {
            // The page is already going (the very thing the guard is for) or not there yet: nothing to tell.
            _log.LogDebug("Could not set the leave guard: {Message}", ex.Message);
        }
    }

    public void Dispose()
    {
        if (_started)
        {
            _commands.Changed -= Update;
        }
    }
}
