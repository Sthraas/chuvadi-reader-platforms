using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Microsoft.AspNetCore.Components;

namespace ChuvadiReader.Linux;

/// <summary>
/// Opens files arriving from outside — the command line / desktop entry (%F), a window drop, a second
/// launch (single instance) — each in its own tab, in order (D-83; B-04, B-05, B-06).
///
/// The Reader takes one request at a time (<see cref="OpenDocumentService"/> holds a single pending path,
/// which the Reader clears as it starts opening), so each file is handed over only after the Reader has
/// taken the one before; a later request never overwrites an earlier one. No Core change: the same calls
/// a single file uses.
/// </summary>
internal sealed class DocumentOpener(OpenDocumentService open, Dispatcher dispatcher)
{
    /// <summary>How long one file may wait for the Reader to take it before the next is handed over anyway.</summary>
    private static readonly TimeSpan TakeTimeout = TimeSpan.FromSeconds(20);

    private readonly SemaphoreSlim _order = new(1, 1);

    /// <summary>The openable, existing files among <paramref name="candidates"/> (paths or file:// URIs),
    /// as full paths, first occurrence of each kept, in the order given.</summary>
    public static IReadOnlyList<string> Openable(IEnumerable<string> candidates)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var list = new List<string>();
        foreach (var raw in candidates)
        {
            string path;
            try
            {
                path = Path.GetFullPath(raw.StartsWith("file://", StringComparison.Ordinal) ? new Uri(raw).LocalPath : raw);
            }
            catch (Exception ex) when (ex is ArgumentException or UriFormatException or NotSupportedException or PathTooLongException)
            {
                continue;
            }

            if (DocumentFormatExtensions.IsOpenable(path) && File.Exists(path) && seen.Add(path))
            {
                list.Add(path);
            }
        }

        return list;
    }

    /// <summary>Hands the files to the Reader one after another (returns when the last has been taken).</summary>
    public Task OpenAsync(IReadOnlyList<string> paths) => paths.Count == 0 ? Task.CompletedTask : Task.Run(async () =>
    {
        await _order.WaitAsync();
        try
        {
            foreach (var path in paths)
            {
                await dispatcher.InvokeAsync(() => open.Request(path));
                var until = DateTime.UtcNow + TakeTimeout;
                while (DateTime.UtcNow < until && await dispatcher.InvokeAsync(() => open.PendingPath) == path)
                {
                    await Task.Delay(25);
                }
            }
        }
        finally
        {
            _order.Release();
        }
    });
}
