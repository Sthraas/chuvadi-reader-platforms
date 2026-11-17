using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// D-181: while any open document has marks not yet saved (or, since D-194, Arrange has desks neither bound nor saved), the browser asks "Leave site? Changes you made may
/// not be saved" before a reload, a close or a move to another site (signing out included). A reload brings the
/// tabs back (D-174) but not unsaved marks, which live in memory with the tab. "Unsaved" is the kit's own answer
/// (<see cref="IUnsavedWork"/>, D-190): every tab counts, and marks written by "Save as new PDF" count as saved.
/// Closing a tab inside the portal is the Ui's business (its Save / Save as / Discard / Cancel card); this is
/// only for the browser tab itself, which a page cannot hold open to ask its own question.
/// The browser is told only when the answer changes. Scoped (per connection).
/// </summary>
public sealed class LeaveGuard : IDisposable
{
    private readonly IAppCommands _commands;
    private readonly IUnsavedWork _work;
    private readonly TabsService? _tabs;
    private readonly BrowserBridge _browser;
    private readonly ILogger<LeaveGuard> _log;
    private readonly object _gate = new();
    private bool _started;
    private bool _sent;

    /// <param name="commands">The Ui's commands: they change whenever a mark is drawn, saved or cleared.</param>
    /// <param name="work">What closing now would lose.</param>
    /// <param name="tabs">The open tabs (a closed tab takes its marks with it); null in tests.</param>
    public LeaveGuard(IAppCommands commands, IUnsavedWork work, BrowserBridge browser, ILogger<LeaveGuard> log, TabsService? tabs = null)
    {
        _commands = commands;
        _work = work;
        _tabs = tabs;
        _browser = browser;
        _log = log;
    }

    /// <summary>True while any open document has marks not yet saved into a file.</summary>
    public bool HasUnsavedMarks => _work.HasUnsavedWork;

    /// <summary>Starts following the Ui (once the page can run script).</summary>
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
        _work.Changed += Update; // D-194: the kit's own signal (marks on any tab, Arrange's desks)
        if (_tabs is not null)
        {
            _tabs.Changed += Update;
        }

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
            _work.Changed -= Update;
            if (_tabs is not null)
            {
                _tabs.Changed -= Update;
            }
        }
    }
}
