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
        await opening.WaitAsync(TimeSpan.FromSeconds(5)); // B-24: the slot is free before the library answers
        Assert.False(tab.IsLoading);

        reader.Gate.SetResult(); // the library finishes later
        await WaitUntil(() => reader.Last?.Disposed == true);

        Assert.Null(tab.Session); // never shown

        var next = await tabs.OpenAsync(TestPdf.TextPage("Next"), "next.pdf", DocumentFormat.Pdf); // B-10
        Assert.NotNull(next.Session);
        Assert.Same(next, Assert.Single(tabs.Tabs));
    }

    // ── B-07: the prompt follows the library's PasswordSupplied (missing vs wrong) ──

    private sealed class LockedReader(bool passwordSupplied) : IPdfReader
    {
        public Task<IPdfSession> OpenAsync(string path, string fileName, string? password = null, CancellationToken cancellationToken = default, bool transparentBackground = false) =>
            throw new Chuvadi.Pdf.Primitives.PdfPasswordRequiredException(passwordSupplied);
    }

    [Theory]
    [InlineData(false, null)]                       // none given: just the prompt
    [InlineData(true, TabsService.WrongPassword)]   // one given and it didn't open the file
    public async Task The_password_prompt_says_wrong_only_when_the_library_says_a_password_was_given(bool supplied, string? expected)
    {
        var tabs = new TabsService(new LockedReader(supplied), new MemoryStorage());

        var tab = await tabs.OpenAsync(TestPdf.TextPage("Locked"), "locked.pdf", DocumentFormat.Pdf);

        Assert.True(tab.NeedsPassword);
        Assert.Equal(expected, tab.PasswordError);
        Assert.Null(tab.Session);
        Assert.Null(tab.Error);
    }

    // ── B-24: a source that never delivers data doesn't freeze the Reader or later opens ──

    private static async Task WaitUntil(Func<bool> condition)
    {
        for (var i = 0; i < 100 && !condition(); i++)
        {
            await Task.Delay(50);
        }

        Assert.True(condition());
    }

    /// <summary>Blocks the calling thread inside OpenAsync, as the library does on open(2) of a hung
    /// mount or a FIFO (it runs synchronously until its first await). Other files open normally.</summary>
    private sealed class StallingReader : IPdfReader
    {
        public readonly ManualResetEventSlim Release = new(false);

        public Task<IPdfSession> OpenAsync(string path, string fileName, string? password = null, CancellationToken cancellationToken = default, bool transparentBackground = false)
        {
            if (fileName.StartsWith("stalled", StringComparison.Ordinal))
            {
                Release.Wait(); // never returns until the test lets it
                throw new IOException("the source went away");
            }

            return new ChuvadiPdfReader().OpenAsync(path, fileName, password, cancellationToken, transparentBackground);
        }
    }

    [Fact]
    public async Task A_stalled_read_shows_opening_at_once_cancels_at_once_and_never_blocks_later_opens()
    {
        var reader = new StallingReader();
        var tabs = new TabsService(reader, new MemoryStorage());
        try
        {
            // The caller gets control back at once with "Opening…", although the read never returns.
            var opening = tabs.OpenAsync(TestPdf.TextPage("Stalled"), "stalled.pdf", DocumentFormat.Pdf);
            var stalled = Assert.Single(tabs.Tabs);
            Assert.True(stalled.IsLoading);
            Assert.False(opening.IsCompleted);

            // A later open isn't stuck behind it.
            var next = await tabs.OpenAsync(TestPdf.TextPage("Next"), "next.pdf", DocumentFormat.Pdf).WaitAsync(TimeSpan.FromSeconds(10));
            Assert.NotNull(next.Session);
            Assert.True(stalled.IsLoading);

            // Cancel ("Stop opening") frees the slot at once, while the read is still stuck.
            await tabs.CloseAsync(stalled.Id);
            await opening.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(stalled.IsLoading);
            Assert.Null(stalled.Error); // stopped, not failed
            Assert.Same(next, Assert.Single(tabs.Tabs));
        }
        finally
        {
            reader.Release.Set();
        }
    }

    [Fact]
    public async Task A_fifo_that_never_delivers_data_doesnt_block_the_library_open_path()
    {
        if (OperatingSystem.IsWindows())
        {
            return; // no FIFOs on Windows; the stalling reader above covers the same path everywhere
        }

        var fifo = Path.Combine(Path.GetTempPath(), "chvd-stall-" + Guid.NewGuid().ToString("N") + ".pdf");
        using (var mk = System.Diagnostics.Process.Start("mkfifo", fifo))
        {
            await mk.WaitForExitAsync();
            Assert.Equal(0, mk.ExitCode);
        }

        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        try
        {
            var opening = tabs.OpenAsync(fifo, "slow.pdf", DocumentFormat.Pdf); // the real library, a real FIFO
            var stalled = Assert.Single(tabs.Tabs);
            Assert.True(stalled.IsLoading);

            var next = await tabs.OpenAsync(TestPdf.TextPage("Five"), "five.pdf", DocumentFormat.Pdf).WaitAsync(TimeSpan.FromSeconds(10));
            Assert.NotNull(next.Session);

            await tabs.CloseAsync(stalled.Id);
            await opening.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Same(next, Assert.Single(tabs.Tabs));
        }
        finally
        {
            // Unblock the stuck reader thread: open the FIFO for writing (the reader is waiting, so this
            // doesn't block), close it, and the read sees end-of-file.
            try
            {
                using (new FileStream(fifo, FileMode.Open, FileAccess.Write))
                {
                }
            }
            catch (IOException)
            {
            }

            File.Delete(fifo);
        }
    }
}
