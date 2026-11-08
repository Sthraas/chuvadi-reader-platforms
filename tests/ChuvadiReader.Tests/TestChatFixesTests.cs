using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>Shared fixes from the Web Test and Linux Test chats in the eighth combined patch (D-120).</summary>
public sealed class TestChatFixesTests
{
    // ── WT-02: "Current page" printed (and Measure labelled) the next page ──

    [Theory]
    [InlineData(1, 0)]
    [InlineData(4, 3)]
    [InlineData(13, 12)]
    [InlineData(0, 0)] // never negative, even before a page is known
    public void The_page_in_view_has_a_zero_based_index_for_code_that_indexes_pages(int shown, int index) =>
        Assert.Equal(index, new ReaderTab { Id = "t", Path = "a.pdf", FileName = "a.pdf", CurrentPage = shown }.CurrentPageIndex);

    [Theory]
    [InlineData(1, 0)]   // page 1 of 13 prints page 1, not page 2
    [InlineData(13, 12)] // the last page prints itself, not (clamped) the last page by accident
    public void Print_current_takes_the_page_in_view(int shown, int printedIndex)
    {
        var tab = new ReaderTab { Id = "t", Path = "a.pdf", FileName = "a.pdf", CurrentPage = shown };

        Assert.True(PageRangeParser.TryParse("current", 13, tab.CurrentPageIndex, out var pages, out _));

        Assert.Equal([printedIndex], pages);
    }

    // ── WT-10 / B-11b: no raw parser text as the message ──

    [Fact]
    public async Task A_file_that_isnt_a_readable_pdf_gets_a_plain_message_with_the_parser_text_as_detail()
    {
        var path = TestPdf.TempOutput();
        await File.WriteAllTextAsync(path, "%PDF-1.7\nthis is not really a PDF at all\n");
        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());

        var tab = await tabs.OpenAsync(path, "notreally.pdf", DocumentFormat.Pdf);

        Assert.Null(tab.Session);
        Assert.Contains(tab.Error, new[] { TabsService.OpenFailed, "This PDF is damaged" });
        Assert.False(string.IsNullOrWhiteSpace(tab.ErrorDetail));
        Assert.DoesNotContain(tab.ErrorDetail!, tab.Error!);
    }

    // ── B-08b: "Stop opening" closes the tab; a load that finishes later is dropped ──

    private sealed class GatedReader : IPdfReader
    {
        public readonly TaskCompletionSource Gate = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TrackedSession? Last;

        public async Task<IPdfSession> OpenAsync(string path, string fileName, string? password = null, CancellationToken cancellationToken = default, bool transparentBackground = false)
        {
            await Gate.Task;
            return Last = new TrackedSession(await new PlaceholderPdfReader().OpenAsync(path, fileName, password, cancellationToken, transparentBackground));
        }
    }

    private sealed class TrackedSession(IPdfSession inner) : IPdfSession
    {
        public bool Disposed { get; private set; }

        public PdfDocumentVm Document => inner.Document;

        public bool TryGetRenderedSvg(int pageNumber, out string svg) => inner.TryGetRenderedSvg(pageNumber, out svg);

        public Task<string> RenderPageSvgAsync(int pageNumber, CancellationToken cancellationToken = default) => inner.RenderPageSvgAsync(pageNumber, cancellationToken);

        public void DropRenderCache() => inner.DropRenderCache();

        public void Dispose()
        {
            Disposed = true;
            inner.Dispose();
        }
    }

    [Fact]
    public async Task A_tab_closed_while_it_opens_drops_the_late_document_and_later_opens_still_work()
    {
        var slow = TestPdf.TextPage("Slow");
        var reader = new GatedReader();
        var tabs = new TabsService(reader, new MemoryStorage());

        var opening = tabs.OpenAsync(slow, "slow.pdf", DocumentFormat.Pdf);
        var tab = Assert.Single(tabs.Tabs);
        Assert.True(tab.IsLoading);

        await tabs.CloseAsync(tab.Id); // "Stop opening"
        Assert.Empty(tabs.Tabs);

        reader.Gate.SetResult(); // the library finishes later
        await opening;

        Assert.True(reader.Last!.Disposed);
        Assert.Null(tab.Session);
        Assert.False(tab.IsLoading);

        var next = await tabs.OpenAsync(TestPdf.TextPage("Next"), "next.pdf", DocumentFormat.Pdf); // B-10
        Assert.NotNull(next.Session);
        Assert.Same(next, Assert.Single(tabs.Tabs));
    }
}
