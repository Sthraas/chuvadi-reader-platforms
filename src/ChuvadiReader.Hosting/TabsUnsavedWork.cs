using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Hosting;

/// <summary><see cref="IUnsavedWork"/> read from the open tabs (D-190): a host asks this before its window closes.</summary>
public sealed class TabsUnsavedWork(TabsService tabs) : IUnsavedWork
{
    public bool HasUnsavedWork => tabs.HasUnsavedMarks;

    public Task<bool> ConfirmCloseAsync() => tabs.ConfirmCloseAllAsync();
}
