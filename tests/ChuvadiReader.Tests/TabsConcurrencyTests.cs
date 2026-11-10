using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// Mac smoke, 10 Nov (Foundation 741930b): two files handed to the app at once killed the Ui with "Collection was
/// modified; enumeration operation may not execute" from TabsService.DropOtherCaches. OpenAsync continues on the
/// thread pool after ConfigureAwait(false), so DropOtherCaches (and PersistAsync) walked the tab list while the next
/// open added to it. Opens that overlap must never throw or lose a tab.
/// </summary>
public sealed class TabsConcurrencyTests
{
    /// <summary>Real sessions whose cache drop takes a moment — the window in which another open adds a tab.</summary>
    private sealed class SlowDropReader : IPdfReader
    {
        public async Task<IPdfSession> OpenAsync(string path, string fileName, string? password = null, CancellationToken cancellationToken = default, bool transparentBackground = false)
            => new SlowDropSession(await new ChuvadiPdfReader().OpenAsync(path, fileName, password, cancellationToken, transparentBackground));
    }

    private sealed class SlowDropSession(IPdfSession inner) : IPdfSession
    {
        public PdfDocumentVm Document => inner.Document;

        public bool TryGetRenderedSvg(int pageNumber, out string svg) => inner.TryGetRenderedSvg(pageNumber, out svg);

        public Task<string> RenderPageSvgAsync(int pageNumber, CancellationToken cancellationToken = default) => inner.RenderPageSvgAsync(pageNumber, cancellationToken);

        public void DropRenderCache()
        {
            Thread.Sleep(30);
            inner.DropRenderCache();
        }

        public void Dispose() => inner.Dispose();
    }

    [Fact]
    public async Task An_open_that_adds_a_tab_while_another_drops_caches_never_throws_and_keeps_every_tab()
    {
        var tabs = new TabsService(new SlowDropReader(), new MemoryStorage());
        for (var i = 0; i < 5; i++)
        {
            await tabs.OpenAsync(TestPdf.TextPage($"Open {i}"), $"open{i}.pdf", DocumentFormat.Pdf);
        }

        // The sixth open walks the other five (~150 ms); the seventh adds its tab in the middle of that walk.
        var walking = Task.Run(() => tabs.OpenAsync(TestPdf.TextPage("Walker"), "walker.pdf", DocumentFormat.Pdf));
        await Task.Delay(60);
        var adding = Task.Run(() => tabs.OpenAsync(TestPdf.TextPage("Adder"), "adder.pdf", DocumentFormat.Pdf));

        await Task.WhenAll(walking, adding).WaitAsync(TimeSpan.FromSeconds(30));
        Assert.Equal(7, tabs.Tabs.Count);
        foreach (var t in tabs.Tabs)
        {
            t.Session?.Dispose();
        }
    }

    [Fact]
    public async Task Overlapping_opens_from_several_threads_never_throw_and_keep_every_tab()
    {
        for (var round = 0; round < 5; round++)
        {
            var tabs = new TabsService(new SlowDropReader(), new MemoryStorage());
            var opens = Enumerable.Range(0, 8)
                .Select(i => Task.Run(() => tabs.OpenAsync(TestPdf.TextPage($"Round {round} file {i}"), $"f{i}.pdf", DocumentFormat.Pdf)))
                .ToArray();
            await Task.WhenAll(opens).WaitAsync(TimeSpan.FromSeconds(60));
            Assert.Equal(8, tabs.Tabs.Count);
            foreach (var t in tabs.Tabs)
            {
                t.Session?.Dispose();
            }
        }
    }
}
