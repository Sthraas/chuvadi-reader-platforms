using System.Globalization;
using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Graphics;
using Chuvadi.Pdf.Images;
using Chuvadi.Pdf.Objects;
using Chuvadi.Pdf.Primitives;
using Chuvadi.Pdf.Rendering;
using Chuvadi.Pdf.Svg;

namespace ChuvadiReader.Core.Reader;

/// <summary>
/// Real reader over the chuvadi-pdf distribution. As a factory it opens a file
/// into an independent <see cref="ChuvadiPdfSession"/>; several can be open at
/// once (one per tab), each holding its own document handle and page cache.
/// </summary>
public sealed class ChuvadiPdfReader : IPdfReader
{
    public async Task<IPdfSession> OpenAsync(
        string path,
        string fileName,
        string? password = null,
        CancellationToken cancellationToken = default,
        bool transparentBackground = false)
    {
        // Open straight from the path with the library's async open, so it can read
        // the file efficiently instead of us buffering the whole thing into memory.
        var document = string.IsNullOrEmpty(password)
            ? await PdfDocument.OpenAsync(path, cancellationToken).ConfigureAwait(false)
            : await PdfDocument.OpenAsync(path, password!, cancellationToken).ConfigureAwait(false);

        var vm = new PdfDocumentVm
        {
            FileName = fileName,
            PageCount = document.PageCount,
            IsEncrypted = !string.IsNullOrEmpty(password),
            AllowsPrinting = PrintPermission.Allows(document),
            IsXfaForm = IsXfaForm(document),
        };

        return new ChuvadiPdfSession(document, vm, transparentBackground);
    }

    /// <summary>True only for XFA documents that <em>cannot</em> be displayed — i.e. pure
    /// dynamic XFA whose content lives solely in the form layer, so the page renders blank.
    /// Hybrid/static XFA (an /XFA entry alongside real page content) renders fine and is NOT
    /// flagged: we probe-render the first page and only flag when it has no drawable content.</summary>
    private static bool IsXfaForm(PdfDocument document)
    {
        try
        {
            var catalog = document.Catalog;
            if (catalog is null)
            {
                return false;
            }

            var acroForm = document.Objects.ResolveDictionaryEntry<PdfDictionary>(catalog, PdfName.Intern("AcroForm"));
            var hasXfa = acroForm is not null && acroForm.ContainsKey(PdfName.Intern("XFA"));
            if (!hasXfa)
            {
                return false;
            }

            // Hybrid XFA renders normally; only block when the first page is truly empty.
            return document.PageCount == 0 || !PageHasDrawableContent(document, 0);
        }
        catch
        {
            return false;
        }
    }

    /// <summary>Renders one page and reports whether it produced any drawable content
    /// (text, vector paths, or images) as opposed to a blank/background-only page.</summary>
    private static bool PageHasDrawableContent(PdfDocument document, int pageIndex)
    {
        try
        {
            var svg = new SvgRenderer(new SvgExportOptions { TextStrategy = SvgTextStrategy.Selectable })
                .RenderPage(document, pageIndex);
            if (string.IsNullOrEmpty(svg))
            {
                return false;
            }

            return svg.Contains("<text", StringComparison.Ordinal)
                || svg.Contains("<image", StringComparison.Ordinal)
                || svg.Contains("<path", StringComparison.Ordinal);
        }
        catch
        {
            // If we cannot render it at all, treat it as undisplayable (keep the notice).
            return false;
        }
    }
}

/// <summary>
/// One open document over chuvadi-pdf: renders each page to selectable-text SVG
/// via <see cref="SvgRenderer"/> and caches the result. Disposing closes the
/// underlying document handle.
/// </summary>
public sealed class ChuvadiPdfSession : IPdfSession
{
    // A page whose area exceeds this (≈ larger than A2, i.e. CAD/large-format sheets)
    // is displayed as a rasterised image rather than SVG: dense vector drawings emit
    // tens of MB of SVG with 100k+ <path> nodes that no WebView can hold.
    private const double LargeFormatAreaPt = 1_500_000d;
    // A normal-size page whose SVG still comes out this large also falls back to raster.
    private const int HeavySvgBytes = 6_000_000;
    private const double RasterDpi = 150d;

    private readonly bool _transparentBackground;
    private SvgRenderer _svgRenderer;
    private readonly Dictionary<int, string> _svgCache = new(); // guarded by lock (_svgCache): the Ui thread reads, renders write
    private PdfDocument? _document;

    // D-152 (AT-13): pages render on a worker thread, one at a time per document. A PdfDocument is not for concurrent
    // use (chuvadi-pdf: "loads objects and pages on demand into plain caches and reads through one stream"), so every
    // use of _document after the open holds this gate: the render, a measurement, and closing the document.
    // Layers are read once at the open, before anything else can touch the document.
    private readonly SemaphoreSlim _gate = new(1, 1);

    // Sixteenth patch, part 2 (Linux step 47): the page being drawn stops when nobody wants it any more, its page left
    // the view or the document closed, instead of drawing a CAD sheet for a tab that's gone. Raster pages stop
    // part-way (the library's rasteriser takes a token); vector pages can't be stopped inside the library.
    // Under lock (_queue).
    private readonly CancellationTokenSource _closing = new();
    private CancellationTokenSource? _drawing;
    private int _drawingPage = -1;

    // Bytes the renders of this document allocated (library included): a heavy document is one whose drawing cost
    // a lot, even if what it kept is small (a vector CAD sheet's SVG is small; drawing it isn't).
    private long _renderAllocatedBytes;

    /// <summary>Tests only: what this document's renders have allocated so far.</summary>
    internal long RenderAllocatedBytes => Interlocked.Read(ref _renderAllocatedBytes);
    private volatile bool _closeRequested;

    // Fifteenth patch (Linux, fast paging): renders wait in this queue, not on the gate, so one that is no longer wanted
    // (its page scrolled out of view) is dropped before it starts, and the next one taken is the queued page nearest
    // the page in view. One worker at a time drains it; guarded by lock (_queue).
    private sealed class QueuedRender(int page, long order)
    {
        public int Page { get; } = page;
        public long Order { get; } = order;
        public TaskCompletionSource<string> Done { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public CancellationTokenRegistration Cancel { get; set; }
    }

    private readonly List<QueuedRender> _queue = new();
    private long _queueOrder;
    private bool _draining;
    private int? _focusPage;

    /// <summary>Tests only: runs on the render's thread, inside the gate, before the page is drawn.</summary>
    internal Action<int>? BeforeRenderForTests { get; set; }

    // Layers: the file's groups (read once, lazily) and this view's overrides (name → visible).
    // Overrides only ever reach the renderers — the document itself is never modified.
    private List<LayerEntry>? _layerEntries;
    private readonly Dictionary<string, bool> _layerOverrides = new(StringComparer.Ordinal);
    private int _renderGeneration;

    public ChuvadiPdfSession(PdfDocument document, PdfDocumentVm vm, bool transparentBackground = false)
    {
        _document = document;
        Document = vm;
        _transparentBackground = transparentBackground;
        _layerEntries = ReadLayers(document); // on the open's thread, before any render can run (D-152)
        _svgRenderer = CreateSvgRenderer();
    }

    public PdfDocumentVm Document { get; }

    /// <summary>
    /// Runs <paramref name="use"/> on the open document, for Core services that work on the same handle
    /// (<see cref="MeasureService"/>). Never waits: while a page is rendering (a heavy page can take seconds) it
    /// returns false at once instead of holding up the Ui thread, and the caller tries again on the next move.
    /// </summary>
    internal bool TryUseDocument<T>(Func<PdfDocument, T> use, out T result)
    {
        result = default!;
        if (!_gate.Wait(0))
        {
            return false;
        }

        try
        {
            if (_document is null || _closeRequested)
            {
                return false;
            }

            result = use(_document);
            return true;
        }
        finally
        {
            _gate.Release();
        }
    }

    public event EventHandler? RenderInvalidated;

    public int RenderGeneration => _renderGeneration;

    public bool CanToggleLayers => _document is not null && LayerEntries.Count > 0;

    public IReadOnlyList<PdfLayerInfo> Layers =>
        LayerEntries.Select(e => new PdfLayerInfo(
                e.Name, e.Name, e.DefaultVisible, IsLayerShown(e), e.Locked, e.Intents, e.Count))
            .ToList();

    public void SetLayerVisible(string layerId, bool visible)
    {
        var entry = LayerEntries.FirstOrDefault(e => string.Equals(e.Name, layerId, StringComparison.Ordinal));
        if (entry is null || entry.Locked || IsLayerShown(entry) == visible)
        {
            return;
        }

        // Store only real deviations from the file's default, so "back to default" leaves no override.
        if (visible == entry.DefaultVisible)
        {
            _layerOverrides.Remove(entry.Name);
        }
        else
        {
            _layerOverrides[entry.Name] = visible;
        }

        InvalidateRender();
    }

    public void ResetLayerVisibility()
    {
        if (_layerOverrides.Count == 0)
        {
            return;
        }

        _layerOverrides.Clear();
        InvalidateRender();
    }

    private bool IsLayerShown(LayerEntry e) =>
        _layerOverrides.TryGetValue(e.Name, out var v) ? v : e.DefaultVisible;

    private void InvalidateRender()
    {
        _svgRenderer = CreateSvgRenderer();
        lock (_svgCache)
        {
            _svgCache.Clear();
            _renderGeneration++; // a render already running for the old layers won't be kept (D-152)
        }

        RenderInvalidated?.Invoke(this, EventArgs.Empty);
    }

    private IReadOnlyDictionary<string, bool>? CurrentOverrides =>
        _layerOverrides.Count == 0 ? null : new Dictionary<string, bool>(_layerOverrides, StringComparer.Ordinal);

    private SvgRenderer CreateSvgRenderer() =>
        // The library now defaults the SVG page background to opaque white. The reader
        // opts out (null) so a CSS page tint can show through; the bench/export keep white.
        new(new SvgExportOptions
        {
            TextStrategy = SvgTextStrategy.Selectable,
            Background = _transparentBackground ? (ColorF?)null : ColorF.White,
            LayerVisibility = CurrentOverrides,
        });

    private List<LayerEntry> LayerEntries => _layerEntries ?? [];

    private sealed record LayerEntry(string Name, bool DefaultVisible, bool Locked, IReadOnlyList<string> Intents, int Count);

    /// <summary>Reads the layers once: names/default state/intents from the library's
    /// <see cref="OptionalContentReader"/>, plus the /D /Locked array (which the library
    /// doesn't surface) straight from /OCProperties. Never throws — a damaged
    /// /OCProperties just yields no layers.</summary>
    private static List<LayerEntry> ReadLayers(PdfDocument? document)
    {
        var result = new List<LayerEntry>();
        if (document is null)
        {
            return result;
        }

        try
        {
            var groups = OptionalContentReader.GetGroups(document);
            if (groups.Count == 0)
            {
                return result;
            }

            var locked = ReadLockedLayerNames(document);
            foreach (var g in groups.GroupBy(g => g.Name ?? string.Empty, StringComparer.Ordinal))
            {
                var first = g.First();
                result.Add(new LayerEntry(
                    g.Key,
                    first.IsVisibleByDefault,
                    locked.Contains(g.Key),
                    first.Intents ?? Array.Empty<string>(),
                    g.Count()));
            }
        }
        catch
        {
            result.Clear();
        }

        return result;
    }

    private static HashSet<string> ReadLockedLayerNames(PdfDocument document)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        try
        {
            var objects = document.Objects;
            var ocProps = objects.ResolveDictionaryEntry<PdfDictionary>(document.Catalog, PdfName.Intern("OCProperties"));
            var d = ocProps is null ? null : objects.ResolveDictionaryEntry<PdfDictionary>(ocProps, PdfName.Intern("D"));
            var lockedArr = d is null ? null : objects.ResolveDictionaryEntry<PdfArray>(d, PdfName.Intern("Locked"));
            if (lockedArr is null)
            {
                return names;
            }

            foreach (var item in lockedArr)
            {
                if (objects.Resolve(item) is PdfDictionary ocg
                    && objects.ResolveDictionaryEntry<PdfString>(ocg, PdfName.Intern("Name")) is { } name)
                {
                    names.Add(name.ToTextString());
                }
            }
        }
        catch
        {
            // Locked is advisory; failing to read it just means nothing is locked.
        }

        return names;
    }

    public bool TryGetRenderedSvg(int pageNumber, out string svg)
    {
        lock (_svgCache)
        {
            return _svgCache.TryGetValue(pageNumber, out svg!);
        }
    }

    public void SetFocusPage(int? pageNumber)
    {
        lock (_queue)
        {
            _focusPage = pageNumber;
        }
    }

    /// <summary>
    /// D-152 (AT-13): renders on a worker thread, one page at a time for this document, so a heavy page (a
    /// 6000 × 6000 image takes seconds) never holds up the Ui or the next open. A page already rendered (or rendered
    /// while it waited) comes straight from the cache. Fifteenth patch: a render still waiting is dropped when
    /// <paramref name="cancellationToken"/> is cancelled (its page left the view), and the waiting page nearest the
    /// focus page (<see cref="SetFocusPage"/>) goes next; without a focus, the order asked.
    /// </summary>
    public Task<string> RenderPageSvgAsync(int pageNumber, CancellationToken cancellationToken = default)
    {
        if (TryGetRenderedSvg(pageNumber, out var cached))
        {
            return Task.FromResult(cached);
        }

        if (_document is null || _closeRequested)
        {
            return Task.FromResult(string.Empty);
        }

        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<string>(cancellationToken);
        }

        QueuedRender entry;
        bool start;
        lock (_queue)
        {
            entry = new QueuedRender(pageNumber, _queueOrder++);
            _queue.Add(entry);
            start = !_draining;
            _draining = true;
        }

        if (cancellationToken.CanBeCanceled)
        {
            entry.Cancel = cancellationToken.Register(() =>
            {
                bool removed;
                lock (_queue)
                {
                    removed = _queue.Remove(entry);
                    if (removed && entry.Page == _drawingPage && !_queue.Any(q => q.Page == entry.Page))
                    {
                        _drawing?.Cancel(); // the page being drawn left the view and nobody else waits for it
                    }
                }

                if (removed)
                {
                    entry.Done.TrySetCanceled(cancellationToken); // never started: nothing is drawn for it
                }
            });
        }

        if (start)
        {
            _ = Task.Run(DrainAsync);
        }

        return entry.Done.Task;
    }

    /// <summary>The one worker: takes the next wanted page, draws it inside the gate, answers everyone waiting for it.</summary>
    private async Task DrainAsync()
    {
        while (true)
        {
            int page;
            lock (_queue)
            {
                if (_queue.Count == 0 || _closeRequested)
                {
                    _draining = false;
                    break;
                }

                page = Next().Page;
                _drawing = CancellationTokenSource.CreateLinkedTokenSource(_closing.Token);
                _drawingPage = page;
            }

            string? svg = null;
            Exception? failed = null;
            var stopped = false;
            if (!TryGetRenderedSvg(page, out var cached))
            {
                await _gate.WaitAsync().ConfigureAwait(false);
                var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
                try
                {
                    svg = RenderInGate(page, _drawing!.Token);
                }
                catch (OperationCanceledException)
                {
                    svg = string.Empty; // stopped part-way: nobody waited for it any more, or the document closed
                    stopped = true;
                }
                catch (Exception e)
                {
                    failed = e;
                }
                finally
                {
                    Interlocked.Add(ref _renderAllocatedBytes, GC.GetAllocatedBytesForCurrentThread() - allocatedBefore);
                    lock (_queue)
                    {
                        _drawing.Dispose();
                        _drawing = null;
                        _drawingPage = -1;
                    }

                    if (_closeRequested)
                    {
                        CloseDocument(); // Dispose came while this render held the document; close it now
                    }

                    _gate.Release();
                }
            }
            else
            {
                svg = cached;
            }

            if (stopped && !_closeRequested)
            {
                continue; // anyone who asked for this page since the stop waits for a fresh draw
            }

            foreach (var waiting in TakeAll(page))
            {
                waiting.Cancel.Dispose();
                if (failed is not null)
                {
                    waiting.Done.TrySetException(failed);
                }
                else
                {
                    waiting.Done.TrySetResult(svg ?? string.Empty);
                }
            }
        }

        // Closed while renders still waited: they get the closed document's answer, an empty page.
        foreach (var waiting in TakeAll(null))
        {
            waiting.Cancel.Dispose();
            waiting.Done.TrySetResult(string.Empty);
        }
    }

    /// <summary>Under lock (_queue): the queued render nearest the focus page, oldest first among equals.</summary>
    private QueuedRender Next()
    {
        var best = _queue[0];
        foreach (var q in _queue)
        {
            var d = _focusPage is { } f ? Math.Abs(q.Page - f) : 0;
            var bd = _focusPage is { } bf ? Math.Abs(best.Page - bf) : 0;
            if (d < bd || (d == bd && q.Order < best.Order))
            {
                best = q;
            }
        }

        return best;
    }

    private List<QueuedRender> TakeAll(int? page)
    {
        lock (_queue)
        {
            var taken = _queue.Where(q => page is null || q.Page == page).ToList();
            _queue.RemoveAll(q => page is null || q.Page == page);
            return taken;
        }
    }

    /// <summary>Draws one page while holding the gate, and keeps it unless the layers changed or the document closed meanwhile.</summary>
    private string RenderInGate(int pageNumber, CancellationToken cancellationToken)
    {
        if (TryGetRenderedSvg(pageNumber, out var cached))
        {
            return cached;
        }

        if (_document is not { } document || _closeRequested)
        {
            return string.Empty;
        }

        // Taken now, on one side of any layer change: a render for the old layers is never kept.
        int generation;
        SvgRenderer renderer;
        IReadOnlyDictionary<string, bool>? overrides;
        lock (_svgCache)
        {
            generation = _renderGeneration;
            renderer = _svgRenderer;
            overrides = CurrentOverrides;
        }

        var svg = RenderPage(document, renderer, overrides, pageNumber, cancellationToken);
        lock (_svgCache)
        {
            if (generation == _renderGeneration && !_closeRequested)
            {
                _svgCache[pageNumber] = svg;
            }
        }

        return svg;
    }

    private string RenderPage(PdfDocument document, SvgRenderer renderer, IReadOnlyDictionary<string, bool>? overrides, int pageNumber, CancellationToken cancellationToken)
    {
        BeforeRenderForTests?.Invoke(pageNumber);
        var page = document.Pages[pageNumber];

        // Large-format sheets (CAD/architectural) are rasterised up front: their vector
        // SVG is too dense for the WebView. Everything else renders as selectable-text SVG,
        // with a safety fallback if a normal-size page's SVG is unexpectedly huge.
        if (page.Width * page.Height > LargeFormatAreaPt)
        {
            return RenderPageAsRasterSvg(document, page, overrides, cancellationToken);
        }

        // SvgRenderer renders at the page's natural size; zoom is applied in the
        // UI (CSS), so there is no scale parameter here.
        var svg = renderer.RenderPage(document, pageNumber);
        if (svg.Length <= HeavySvgBytes)
        {
            return svg;
        }

        cancellationToken.ThrowIfCancellationRequested();
        return RenderPageAsRasterSvg(document, page, overrides, cancellationToken);
    }

    /// <summary>Renders a page to a raster image (via the library rasteriser + PNG encoder)
    /// and wraps it in a minimal SVG carrying a single &lt;image&gt;, so the UI's SVG display
    /// path is unchanged while the WebView only has to hold one image node instead of
    /// hundreds of thousands of vector paths.</summary>
    private static string RenderPageAsRasterSvg(PdfDocument document, PdfPage page, IReadOnlyDictionary<string, bool>? overrides, CancellationToken cancellationToken)
    {
        var buffer = new PageRasterizer(
                document.Objects,
                new RenderOptions
                {
                    Dpi = RasterDpi,
                    Background = ColorF.White,
                    AntiAlias = true,
                    LayerVisibility = overrides,
                })
            .Rasterize(page, cancellationToken);

        using var ms = new MemoryStream();
        PngEncoder.Encode(new ImageFrame(buffer, ImageColorFormat.Rgba32), ms, false);

        string w = page.Width.ToString("0.###", CultureInfo.InvariantCulture);
        string h = page.Height.ToString("0.###", CultureInfo.InvariantCulture);
        return RasterSvg(w, h, ms.GetBuffer(), (int)ms.Length);
    }

    /// <summary>
    /// The SVG that carries a rendered page as one PNG, written straight into its final string (sixteenth patch).
    /// Before, the base64 text was built three times over (the base64, the data URI, then an interpolated string,
    /// which grew through a pooled buffer): a large sheet (≈ 39 M characters) left a 134 MB buffer in the shared
    /// pool for the life of the app, and three 77 MB copies at once while drawing. Same characters as before.
    /// </summary>
    internal static string RasterSvg(string w, string h, byte[] png, int length)
    {
        var head = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" + w + "pt\" height=\"" + h + "pt\" " +
                   "viewBox=\"0 0 " + w + " " + h + "\" preserveAspectRatio=\"xMidYMid meet\">" +
                   "<image x=\"0\" y=\"0\" width=\"" + w + "\" height=\"" + h + "\" preserveAspectRatio=\"none\" " +
                   "href=\"data:image/png;base64,";
        var base64Length = checked((length + 2) / 3 * 4);
        return string.Create(head.Length + base64Length + RasterSvgTail.Length, (head, png, length), static (span, st) =>
        {
            st.head.AsSpan().CopyTo(span);
            if (!Convert.TryToBase64Chars(st.png.AsSpan(0, st.length), span[st.head.Length..], out var written)
                || written != span.Length - st.head.Length - RasterSvgTail.Length)
            {
                throw new InvalidOperationException("Unexpected base64 length.");
            }

            RasterSvgTail.AsSpan().CopyTo(span[(st.head.Length + written)..]);
        });
    }

    private const string RasterSvgTail = "\"/></svg>";

    public void DropRenderCache() => DropCacheChars();

    /// <summary>Clears the page cache and returns how many characters of page SVG it held.</summary>
    private long DropCacheChars()
    {
        lock (_svgCache)
        {
            long chars = 0;
            foreach (var svg in _svgCache.Values)
            {
                chars += svg.Length;
            }

            _svgCache.Clear();
            return chars;
        }
    }

    /// <summary>Closes the document. If a page is rendering, the render closes it when it ends (it holds the
    /// document); nothing new starts after this. Never waits.</summary>
    public void Dispose()
    {
        _closeRequested = true;
        _closing.Cancel(); // the page being drawn, if any, stops
        _closedCacheChars = DropCacheChars();
        if (_gate.Wait(0))
        {
            try
            {
                CloseDocument();
            }
            finally
            {
                _gate.Release();
            }
        }
    }

    private long _closedCacheChars;

    private void CloseDocument()
    {
        if (_document is null)
        {
            return;
        }

        _document.Dispose();
        _document = null;
        if (_closedCacheChars * sizeof(char) >= MemoryRelief.HeavyBytes
            || Interlocked.Read(ref _renderAllocatedBytes) >= MemoryRelief.HeavyDrawingBytes)
        {
            MemoryRelief.Request(); // after the close, so the document and its pages can go
        }
    }
}

/// <summary>
/// Sixteenth patch (Linux 36c): gives memory back to the system after a heavy document closes. The runtime keeps the
/// memory a big drawing used (a CAD sheet: ~1.7 GB resident) for later use even when nothing in it is alive any
/// more, so the app stayed at that size after the tab closed. One aggressive collection returns it (measured:
/// 1745 MB → 129 MB resident, a 74 ms pause). Asked for only when the closed document's pages held at least
/// <see cref="HeavyBytes"/>, run on a worker after the close, and at most once per <see cref="MinGap"/> so a shared
/// server (Web) never runs them back to back.
/// </summary>
internal static class MemoryRelief
{
    internal const long HeavyBytes = 64L * 1024 * 1024;

    /// <summary>A document whose drawing allocated this much is heavy too, whatever its pages keep.</summary>
    internal const long HeavyDrawingBytes = 64L * 1024 * 1024;
    internal static readonly TimeSpan MinGap = TimeSpan.FromSeconds(30);
    internal static TimeSpan Settle { get; set; } = TimeSpan.FromMilliseconds(500);

    /// <summary>
    /// The second pass. Showing a heavy page sends its text through the Ui's transport, which grows buffers in .NET's
    /// shared byte pool (seen in the Web preview after closing two CAD sheets: 8 to 128 MB arrays, ~260 MB in all).
    /// The pool lets go of a buffer only at a full collection after it has gone unused for about a minute, so a
    /// second pass then gives that back too (measured: the heap dropped from ~423 MB to ~2 MB of large arrays).
    /// </summary>
    internal static TimeSpan FollowUp { get; set; } = TimeSpan.FromSeconds(65);

    private static long _lastTicks = long.MinValue / 2;
    private static int _running;

    /// <summary>Tests only: the last relief started, if any.</summary>
    internal static Task? Last { get; private set; }

    internal static void Request()
    {
        var now = Environment.TickCount64;
        var last = Interlocked.Read(ref _lastTicks);
        if (now - last < (long)MinGap.TotalMilliseconds || Interlocked.CompareExchange(ref _running, 1, 0) != 0)
        {
            return;
        }

        Interlocked.Exchange(ref _lastTicks, now);
        Last = Task.Run(async () =>
        {
            try
            {
                await Task.Delay(Settle).ConfigureAwait(false); // the Ui lets go of the closed tab's pages first
                GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
                if (FollowUp > TimeSpan.Zero)
                {
                    await Task.Delay(FollowUp).ConfigureAwait(false);
                    GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true); // the pool drops buffers idle for a minute
                    GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
                }
            }
            finally
            {
                Volatile.Write(ref _running, 0);
            }
        });
    }

    /// <summary>Tests only: lets the next request run at once.</summary>
    internal static void ResetForTests() => Interlocked.Exchange(ref _lastTicks, long.MinValue / 2);
}
