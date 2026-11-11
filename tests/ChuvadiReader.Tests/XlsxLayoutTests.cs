using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// File-fidelity audit E-05 to E-16, D-172: the Excel view model holds what the file holds about layout — widths and
/// heights, hidden rows, columns and sheets, merged cells, borders and fills, rich text, data bars and icons, comments
/// and links, the sheet's own settings — with no cap on rows or columns. Fixture: <c>Fixtures/Office/layout.xlsx</c>
/// from <c>tools/OfficeCorpus/make_layout.py</c>.
/// </summary>
public sealed class XlsxLayoutTests
{
    private static readonly WorkbookView Book =
        new XlsxViewService { Culture = System.Globalization.CultureInfo.GetCultureInfo("en-IN") }
            .Load(Path.Combine(AppContext.BaseDirectory, "Fixtures", "Office", "layout.xlsx"));

    private static SheetView Layout => Book.Sheets[0];

    private static SheetCell At(string a1)
    {
        var at = XlsxViewService.ParseRange(a1)!.Value;
        return Layout.Cells.Single(c => c.Row == at.Row && c.Col == at.Col);
    }

    [Fact]
    public void Hidden_sheets_are_listed_and_marked()
    {
        Assert.Equal(["Layout", "Settings", "Secret", "Deep"], Book.Sheets.Select(s => s.Name));
        Assert.Equal([false, false, true, true], Book.Sheets.Select(s => s.Hidden));
        Assert.Equal("in a hidden sheet", Book.Sheets[2].Cells.Single().Value);
    }

    [Fact]
    public void Widths_and_heights_are_the_files_by_Excels_rule()
    {
        Assert.Equal(64, Layout.DefaultColPx);            // Excel's default column (shown as 8.43)
        Assert.Equal(20, Layout.DefaultRowPx);            // 15 pt
        Assert.Equal(140, Layout.ColWidthPx(1));          // stored width 20
        Assert.Equal(35, Layout.ColWidthPx(5));           // stored width 5
        Assert.Equal(64, Layout.ColWidthPx(2));
        Assert.Equal(40, Layout.RowHeightPx(3));          // 30 pt
        Assert.Equal(64, Layout.RowHeightPx(16));         // 48 pt
        Assert.Equal(20, Layout.RowHeightPx(4));
    }

    [Theory]
    [InlineData(9.140625, 64)]    // Excel's default column: shown as 8.43, 64 pixels
    [InlineData(20.7109375, 145)] // shown as 20.00 (145 pixels)
    [InlineData(10, 70)]
    [InlineData(1, 7)]
    [InlineData(0, 0)]
    public void A_width_in_characters_becomes_pixels_as_in_Excel(double characters, double pixels) =>
        Assert.Equal(pixels, XlsxViewService.WidthPx(characters));

    [Fact]
    public void Hidden_rows_and_columns_take_no_room_and_keep_their_cells()
    {
        Assert.Equal(0, Layout.RowHeightPx(5));
        Assert.Equal(0, Layout.ColWidthPx(3));
        Assert.Equal("in a hidden row", At("A5").Value);      // still there for copy and Find
        Assert.Equal("in a hidden column", At("C6").Value);
    }

    [Fact]
    public void Merged_ranges_are_kept()
    {
        Assert.Equal([new SheetMerge(1, 1, 2, 2)], Layout.Merges);
        Assert.Equal("Title merged", At("A1").Value);
        Assert.Equal("#FFFF00", At("A1").Fill);
        Assert.Equal("Center", At("A1").Align);
    }

    [Fact]
    public void Rows_and_columns_past_the_old_caps_are_in_the_sheet()
    {
        var far = At("KN6000");
        Assert.Equal((6000, 300), (far.Row, far.Col));
        Assert.Equal(6000, Layout.LastRow);
        Assert.Equal(300, Layout.LastCol);
    }

    [Fact]
    public void Borders_fills_and_font_effects_come_through()
    {
        Assert.Equal("1px solid #FF0000", At("A6").BorderLeft);
        Assert.Equal("3px solid #000000", At("A6").BorderBottom);
        Assert.Null(At("A6").BorderTop);

        var empty = At("B6");                                   // an empty cell with only a border
        Assert.True(empty.StyleOnly);
        Assert.Equal("", empty.Value);
        Assert.Equal("3px double #008000", empty.BorderTop);
        Assert.Equal("1px dashed #000000", empty.BorderBottom);

        Assert.True(At("A7").Strike);
        Assert.True(At("B7").DoubleUnderline);
        Assert.True(At("B7").Underline);
        Assert.Equal("super", At("D7").VPos);
        Assert.Equal("#BFBFFF", At("A14").FillCss);            // lightGray: a quarter blue on white
        Assert.Equal(2, At("A15").Indent);
        Assert.Equal(45, At("B15").Rotation);
        Assert.True(At("A16").Wrap);
        Assert.Equal("Top", At("A16").VAlign);
    }

    [Fact]
    public void Rich_text_keeps_its_runs()
    {
        var runs = At("A8").Runs!;
        Assert.Equal(["H", "2", "O ", "bold red"], runs.Select(r => r.Text));
        Assert.Equal("sub", runs[1].VPos);
        Assert.True(runs[3].Bold);
        Assert.Equal("#FF0000", runs[3].Color);
        Assert.Equal("H2O bold red", At("A8").Value);
    }

    [Fact]
    public void Data_bars_and_icons_are_drawn_from_the_rules()
    {
        Assert.True(At("A9").Bar!.Percent < At("A10").Bar!.Percent);
        Assert.True(At("A10").Bar!.Percent < At("A11").Bar!.Percent);
        Assert.Equal("#638EC6", At("A9").Bar!.Color);
        Assert.Equal(("3Arrows", 0, 3), (At("B9").Icon!.Set, At("B9").Icon!.Index, At("B9").Icon!.Count));
        Assert.Equal(1, At("B10").Icon!.Index);
        Assert.Equal(2, At("B11").Icon!.Index);
        Assert.Equal("10", At("A9").Value);                     // the value is untouched
    }

    [Fact]
    public void Comments_and_links_are_shown_as_the_file_holds_them()
    {
        Assert.Equal("Arun: Check this figure", At("A12").Note);
        Assert.Equal("https://example.org/page", At("A13").Link);
        Assert.Equal("Example site", At("A13").Value);
    }

    [Fact]
    public void A_sheets_own_settings_are_followed()
    {
        Assert.True(Layout.ShowGridLines);
        Assert.Equal((2, 1), (Layout.FreezeRows, Layout.FreezeCols));
        var settings = Book.Sheets[1];
        Assert.False(settings.ShowGridLines);
        Assert.True(settings.RightToLeft);
        Assert.Equal(150, settings.Zoom);
    }

    [Fact]
    public void A_formatted_number_keeps_its_value_and_shows_its_format()
    {
        Assert.Equal("7654321", At("A18").Value);
        Assert.Equal("76,54,321", At("A18").Text);   // #,##0 on en-IN
    }
}
