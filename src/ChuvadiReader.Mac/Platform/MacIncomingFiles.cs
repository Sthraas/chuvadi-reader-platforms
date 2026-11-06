using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using Foundation;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Files arriving from outside the app — dropped from Finder, opened with Chuvadi from Finder
/// ("Open With", double-click when Chuvadi is the default), or handed over at launch — go where
/// HANDOFF §2 says: to the Bench shelf when the Bench is open, otherwise to the Reader. Files that
/// arrive before the Ui has rendered wait until it has, then go in their arrival order.
/// Must be created before the first render (AppDelegate does), since the ready signal fires once.
/// </summary>
public sealed class MacIncomingFiles
{
    private readonly BenchDropService _bench;
    private readonly OpenDocumentService _open;
    private readonly object _gate = new();
    private List<string>? _waiting = new();

    public MacIncomingFiles(BenchDropService bench, OpenDocumentService open, IAppReadySignal ready)
    {
        _bench = bench;
        _open = open;
        ready.Ready += Release;
    }

    /// <summary>The file types the Open panel accepts (HANDOFF §2: arrivals accept the same).</summary>
    public static bool IsSupported(string path)
        => MacFilePicker.DocumentTypes.Contains(Path.GetExtension(path).TrimStart('.').ToLowerInvariant());

    /// <summary>Takes file URLs from the system, keeping only readable files of a supported type.</summary>
    public void Receive(IEnumerable<NSUrl> urls)
        => Receive(urls.Where(u => u.IsFileUrl).Select(u => u.Path).OfType<string>());

    public void Receive(IEnumerable<string> paths)
    {
        var supported = paths.Where(p => File.Exists(p) && IsSupported(p)).ToArray();
        if (supported.Length == 0)
        {
            return;
        }

        lock (_gate)
        {
            if (_waiting is not null)
            {
                _waiting.AddRange(supported);
                return;
            }
        }

        Deliver(supported);
    }

    private void Release()
    {
        string[] pending;
        lock (_gate)
        {
            pending = _waiting?.ToArray() ?? Array.Empty<string>();
            _waiting = null;
        }

        if (pending.Length > 0)
        {
            Deliver(pending);
        }
    }

    private void Deliver(string[] paths) => MainPage.Dispatch(() =>
    {
        if (_bench.IsBenchActive)
        {
            _bench.Drop(paths);
        }
        else
        {
            // The Reader opens one document per request: the first, as the Windows drop does.
            _open.Request(paths[0]);
        }

        return Task.CompletedTask;
    });
}
