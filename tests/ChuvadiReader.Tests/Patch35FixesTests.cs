using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>Patch 35's smaller fixes from the Windows test (23 Nov): BUG-14/15, HO33, BUG-12, the shared open.</summary>
public class Patch35FixesTests
{
    [Fact]
    public void Markdown_nested_far_too_deep_is_refused_before_it_is_parsed()
    {
        var quotes = new string('>', 5000) + " deep";
        var ex = Assert.Throws<DocumentViewException>(() => MarkdownRenderer.Render(quotes));
        Assert.Equal(MarkdownRenderer.TooDeepText, ex.Message);

        var lists = string.Join("\n", Enumerable.Range(0, 400).Select(i => new string(' ', i * 2) + "- item " + i));
        Assert.Throws<DocumentViewException>(() => MarkdownRenderer.Render(lists));
    }

    [Fact]
    public void Ordinary_Markdown_nesting_still_draws()
    {
        var md = "> quote\n>> inner\n\n- a\n  - b\n    - c\n      1. d\n\n10. ten\n> - in a quote";
        var r = MarkdownRenderer.Render(md);
        Assert.Contains("<blockquote", r.Html);
        Assert.True(MarkdownRenderer.DeepestNesting(md.Split('\n')) < 10);
    }

    [Fact]
    public async Task A_file_the_app_closed_while_opening_comes_back_held_not_opened()
    {
        var storage = new MemoryStorage();
        var path = TestPdf.TextPage("Crashed once");
        var first = new TabsService(new ChuvadiPdfReader(), storage);
        var tab = await first.OpenAsync(path, "crash.pdf", DocumentFormat.Pdf);
        Assert.NotNull(tab.Session);
        await first.MarkOpeningAsync(tab);   // as if the app died while opening it (a viewer tab marks itself like this)

        var next = new TabsService(new ChuvadiPdfReader(), storage);
        await next.RestoreAsync();
        var held = Assert.Single(next.Tabs);
        Assert.True(held.HeldAfterCrash);
        Assert.Null(held.Session);
        Assert.Equal(TabsService.HeldAfterCrashText, held.Error);

        await next.OpenHeldAsync(held.Id);
        Assert.False(held.HeldAfterCrash);
        Assert.NotNull(held.Session);

        // And the start after that one holds nothing.
        var third = new TabsService(new ChuvadiPdfReader(), storage);
        await third.RestoreAsync();
        Assert.False(Assert.Single(third.Tabs).HeldAfterCrash);
    }

    [Fact]
    public async Task A_failed_repair_writes_nothing()
    {
        var folder = Path.Combine(Path.GetTempPath(), "chvd-rec-" + Guid.NewGuid().ToString("N"));
        var junk = TestPdf.WriteTemp(System.Text.Encoding.ASCII.GetBytes("not a pdf at all, just words"));
        var svc = new RecoveryService(new SaveFolderService(new MemoryStorage()));
        await Assert.ThrowsAnyAsync<Exception>(() => svc.RecoverAsync(junk, folder));
        Assert.True(!Directory.Exists(folder) || Directory.GetFiles(folder).Length == 0);
    }

    [Fact]
    public void A_file_another_program_holds_open_for_writing_still_reads()
    {
        var path = TestPdf.TextPage("Held");
        using var holder = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite);
        Assert.NotEmpty(SharedRead.AllBytes(path));
        using var doc = PdfFiles.Open(path);
        Assert.Equal(1, doc.PageCount);
    }
}

/// <summary>VW01: merged Word table cells draw as one cell, with no extra column.</summary>
public class WordMergedCellsTests
{
    [Fact]
    public void Merged_cells_skip_their_placeholders_and_span_rows()
    {
        var doc = new Chuvadi.Docs.Model.Document();
        var t = doc.AddTable(columns: 3);
        t.AddRow("Wide", "", "C");
        t.AddRow("Tall", "B2", "C2");
        t.AddRow("", "B3", "C3");
        t.Rows[0].Cell(0).ColumnSpan = 2;
        t.Rows[1].Cell(0).VerticalMerge = Chuvadi.Docs.Model.VerticalMerge.Restart;
        t.Rows[2].Cell(0).VerticalMerge = Chuvadi.Docs.Model.VerticalMerge.Continue;
        var path = Path.Combine(Path.GetTempPath(), "chvd-merge-" + Guid.NewGuid().ToString("N") + ".docx");
        doc.SaveTo(path);

        var view = new DocxViewService().Load(path);
        var table = Assert.IsType<WordTableBlock>(Assert.Single(view.Blocks, b => b is WordTableBlock));
        Assert.Equal(new[] { 2, 3, 2 }, table.Rows.Select(r => r.Cells.Count).ToArray());   // no drawn placeholders
        Assert.Equal(2, table.Rows[0].Cells[0].ColSpan);
        Assert.Equal(2, table.Rows[1].Cells[0].RowSpan);
        // Every row still covers the three grid columns: 2+1, 1+1+1, and (under the tall cell) 1+1.
        Assert.Equal(new[] { 3, 3, 2 }, table.Rows.Select(r => r.Cells.Sum(c => c.ColSpan)).ToArray());
    }
}
