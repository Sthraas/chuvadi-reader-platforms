using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>D-190: sizes set on screen for an Excel sheet are kept per file and sheet, within limits, and can be
/// put back. They are memory only; nothing here touches a file.</summary>
public sealed class SheetSizeMemoryTests
{
    [Fact]
    public void A_sheet_with_nothing_set_has_no_sizes_of_its_own()
    {
        var m = new SheetSizeMemory();
        Assert.Null(m.Find("a.xlsx", "Sheet1"));
        m.ClearColumn("a.xlsx", "Sheet1", 2);   // nothing to clear: still nothing
        Assert.Null(m.Find("a.xlsx", "Sheet1"));
    }

    [Fact]
    public void Sizes_are_per_file_and_sheet_and_within_limits()
    {
        var m = new SheetSizeMemory();
        m.SetColumn("a.xlsx", "Sheet1", 2, 150);
        m.SetRow("a.xlsx", "Sheet1", 7, 33);
        m.SetColumn("a.xlsx", "Sheet1", 3, 0);        // never out of sight
        m.SetColumn("a.xlsx", "Sheet1", 4, 99999);
        m.SetRow("a.xlsx", "Sheet1", 8, 99999);

        var own = m.Find("a.xlsx", "Sheet1")!;
        Assert.Equal(150, own.Cols[2]);
        Assert.Equal(33, own.Rows[7]);
        Assert.Equal(SheetSizeMemory.Smallest, own.Cols[3]);
        Assert.Equal(SheetSizeMemory.LargestWidth, own.Cols[4]);
        Assert.Equal(SheetSizeMemory.LargestHeight, own.Rows[8]);
        Assert.Null(m.Find("a.xlsx", "Sheet2"));
        Assert.Null(m.Find("b.xlsx", "Sheet1"));
    }

    [Fact]
    public void One_size_or_the_whole_sheet_can_go_back_to_the_files_own()
    {
        var m = new SheetSizeMemory();
        m.SetColumn("a.xlsx", "S", 2, 150);
        m.SetRow("a.xlsx", "S", 7, 33);
        m.SetColumn("a.xlsx", "T", 1, 90);

        m.ClearColumn("a.xlsx", "S", 2);
        Assert.False(m.Find("a.xlsx", "S")!.Cols.ContainsKey(2));
        m.ClearRow("a.xlsx", "S", 7);
        Assert.Null(m.Find("a.xlsx", "S"));           // nothing left: shown as the file holds it

        m.SetColumn("a.xlsx", "S", 2, 150);
        m.Reset("a.xlsx", "S");
        Assert.Null(m.Find("a.xlsx", "S"));
        Assert.NotNull(m.Find("a.xlsx", "T"));        // another sheet keeps its own
    }

    [Fact]
    public void A_tab_carries_its_own_memory()
    {
        var a = new ReaderTab { Id = "1", Path = "a.xlsx", FileName = "a.xlsx" };
        var b = new ReaderTab { Id = "2", Path = "a.xlsx", FileName = "a.xlsx" };
        a.SheetSizes.SetColumn(a.Path, "S", 1, 120);
        Assert.NotNull(a.SheetSizes.Find(a.Path, "S"));
        Assert.Null(b.SheetSizes.Find(b.Path, "S"));
    }
}
