using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Hosting;

/// <summary><see cref="IUnsavedWork"/> read from the open tabs' marks (D-190) and Arrange's desks (D-194): a host
/// asks this before its window closes, or before Sign out on the portal.</summary>
public sealed class TabsUnsavedWork : IUnsavedWork, IDisposable
{
    private readonly TabsService _tabs;
    private readonly BenchService _bench;
    private int _last;   // 0 nothing unsaved, 1 something

    public TabsUnsavedWork(TabsService tabs, BenchService bench)
    {
        _tabs = tabs;
        _bench = bench;
        _last = HasUnsavedWork ? 1 : 0;
        _tabs.Changed += Note;               // a tab with unsaved marks closed
        _tabs.UnsavedMarksChanged += Note;   // a first mark drawn, the marks saved or discarded
        _bench.UnsavedChanged += Note;
    }

    public bool HasUnsavedWork => _tabs.HasUnsavedMarks || _bench.HasUnsavedWork;

    public event Action? Changed;

    /// <summary>Arrange first, then the files with marks, one at a time. False as soon as the person cancels.
    /// The files come last because a Discard there is the one answer that destroys something, and it must only
    /// take effect when nothing after it can still be cancelled.</summary>
    public async Task<bool> ConfirmCloseAsync() =>
        await _bench.ConfirmCloseAsync().ConfigureAwait(false) && await _tabs.ConfirmCloseAllAsync().ConfigureAwait(false);

    private void Note()
    {
        int now = HasUnsavedWork ? 1 : 0;
        if (Interlocked.Exchange(ref _last, now) != now)
        {
            Changed?.Invoke();
        }
    }

    public void Dispose()
    {
        _tabs.Changed -= Note;
        _tabs.UnsavedMarksChanged -= Note;
        _bench.UnsavedChanged -= Note;
    }
}
