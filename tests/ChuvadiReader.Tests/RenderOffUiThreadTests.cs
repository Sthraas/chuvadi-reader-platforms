using Chuvadi.Pdf.Authoring;
using Chuvadi.Pdf.Graphics;
using ChuvadiReader.Core.Reader;
using Xunit;
using Path = System.IO.Path;

namespace ChuvadiReader.Tests;

/// <summary>
/// D-152 (Android Test AT-13): pages render on a worker thread, one at a time per document, so a heavy page never
/// holds up the Ui or the next open. Stall tests, like B-24's: the hook holds a render open; on the old code, which
/// rendered on the caller's thread, each of these would hang the caller (they fail on the 5 s guard instead).
/// </summary>
public sealed class RenderOffUiThreadTests
{
    private static readonly TimeSpan Guard = TimeSpan.FromSeconds(5);

    private static string ThreePages()
    {
        var b = PdfDocumentBuilder.Create();
        for (var i = 1; i <= 3; i++)
        {
            b.AddPage(new PageSize(200, 200)).DrawText("Page " + i, 20, 90, "Helvetica", 18, Color.FromHex("#000000"));
        }

        return TestPdf.WriteTemp(b.ToByteArray());
    }

    private static async Task<ChuvadiPdfSession> Open(string path) =>
        (ChuvadiPdfSession)await new ChuvadiPdfReader().OpenAsync(path, Path.GetFileName(path));

    /// <summary>Starts a call on another thread, so a call that blocks fails the guard instead of hanging the test.</summary>
    private static Task<T> Call<T>(Func<T> call) => Task.Run(call).WaitAsync(Guard);

    [Fact]
    public async Task A_render_runs_off_the_callers_thread_and_the_caller_is_not_held()
    {
        using var session = await Open(ThreePages());
        using var release = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => release.Wait(Guard);

        // On the old code this call drew the page before returning, so it hung here (the guard fails it).
        var render = await Call(() => session.RenderPageSvgAsync(0));

        Assert.False(render.IsCompleted);            // the caller got its task back while the page is still rendering
        Assert.False(session.TryGetRenderedSvg(0, out _));
        release.Set();
        var svg = await render.WaitAsync(Guard);

        Assert.Contains("<svg", svg);
        Assert.True(session.TryGetRenderedSvg(0, out var cached));
        Assert.Equal(svg, cached);
    }

    [Fact]
    public async Task One_document_renders_one_page_at_a_time_in_the_order_asked()
    {
        using var session = await Open(ThreePages());
        int running = 0, most = 0;
        var order = new List<int>();
        session.BeforeRenderForTests = page =>
        {
            var now = Interlocked.Increment(ref running);
            InterlockedMax(ref most, now);
            lock (order) order.Add(page);
            Thread.Sleep(80);
            Interlocked.Decrement(ref running);
        };

        var renders = new[] { session.RenderPageSvgAsync(2), session.RenderPageSvgAsync(0), session.RenderPageSvgAsync(1), session.RenderPageSvgAsync(2) };
        await Task.WhenAll(renders).WaitAsync(Guard);

        Assert.Equal(1, most);                       // never two renders on one document at once
        Assert.Equal([2, 0, 1], order);              // in the order asked; the repeat of page 2 came from the cache
        Assert.All(renders, r => Assert.Contains("<svg", r.Result));
    }

    [Fact]
    public async Task Two_documents_render_at_the_same_time()
    {
        using var a = await Open(ThreePages());
        using var b = await Open(ThreePages());
        using var both = new CountdownEvent(2);
        void Meet(int _) { both.Signal(); Assert.True(both.Wait(Guard), "the other document's render never started"); }
        a.BeforeRenderForTests = Meet;
        b.BeforeRenderForTests = Meet;

        await Task.WhenAll(a.RenderPageSvgAsync(0), b.RenderPageSvgAsync(0)).WaitAsync(Guard);
    }

    [Fact]
    public async Task Closing_while_a_page_renders_never_waits_and_the_document_closes_when_the_render_ends()
    {
        var session = await Open(ThreePages());
        using var started = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => { started.Set(); release.Wait(Guard); };

        var render = session.RenderPageSvgAsync(0);
        Assert.True(started.Wait(Guard));
        await Call(() => { session.Dispose(); return true; }); // a tab closed mid-render: returns at once

        Assert.False(session.TryUseDocument(_ => true, out _)); // nothing new can start
        release.Set();
        await render.WaitAsync(Guard);                           // the render ends cleanly

        Assert.False(session.TryGetRenderedSvg(0, out _));       // and isn't kept for a closed document
        Assert.Equal(string.Empty, await session.RenderPageSvgAsync(1).WaitAsync(Guard));
    }

    [Fact]
    public async Task Measuring_never_waits_for_a_page_that_is_rendering()
    {
        using var session = await Open(ThreePages());
        using var started = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => { started.Set(); release.Wait(Guard); };
        var measure = new MeasureService();

        var render = session.RenderPageSvgAsync(0);
        Assert.True(started.Wait(Guard));
        var during = await Call(() => measure.Measure(session, 0, new PagePoint(0, 0), new PagePoint(72, 0)));
        release.Set();
        await render.WaitAsync(Guard);
        var after = measure.Measure(session, 0, new PagePoint(0, 0), new PagePoint(72, 0));

        Assert.Null(during);                 // skipped, not waited for: the next pointer move measures again
        Assert.NotNull(after);
    }

    [Fact]
    public async Task A_page_rendered_for_the_old_layers_is_not_kept_after_a_layer_change()
    {
        using var session = await Open(LayersMeasureSignatureTests.LayeredPdf());
        using var started = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        session.BeforeRenderForTests = _ => { started.Set(); release.Wait(Guard); };

        var render = session.RenderPageSvgAsync(0);
        Assert.True(started.Wait(Guard));
        session.SetLayerVisible("Green layer", true); // hidden by default; shown while the old view renders
        release.Set();
        await render.WaitAsync(Guard);

        Assert.False(session.TryGetRenderedSvg(0, out _)); // the stale page is dropped; the Reader asks again
        session.BeforeRenderForTests = null;
        var fresh = await session.RenderPageSvgAsync(0).WaitAsync(Guard);
        Assert.True(session.TryGetRenderedSvg(0, out var cached));
        Assert.Equal(fresh, cached);
    }

    private static void InterlockedMax(ref int target, int value)
    {
        int seen;
        while ((seen = Volatile.Read(ref target)) < value && Interlocked.CompareExchange(ref target, value, seen) != seen)
        {
        }
    }
}
