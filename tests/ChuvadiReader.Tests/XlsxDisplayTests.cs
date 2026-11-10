using System.Globalization;
using System.IO.Compression;
using System.Xml.Linq;
using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// D-161: every Excel cell shows its number format, by Chuvadi.Sheets, in the system culture; the stored value stays
/// underneath, unchanged. Fixture: <c>Fixtures/Office/formats.xlsx</c> from <c>tools/OfficeCorpus/make_formats.py</c>,
/// one row per format (label in A, value in B). The expected texts are what Excel shows on an en-IN system, written
/// by hand; the cases the library can't show yet are library items (docs/foundation/FILE-FIDELITY-AUDIT.md), not here.
/// </summary>
public sealed class XlsxDisplayTests
{
    private static readonly string File_ = Path.Combine(AppContext.BaseDirectory, "Fixtures", "Office", "formats.xlsx");
    private static readonly CultureInfo India = CultureInfo.GetCultureInfo("en-IN");

    private static Dictionary<string, SheetCell> ByLabel(CultureInfo culture)
    {
        var sheet = new XlsxViewService { Culture = culture }.Load(File_).Sheets[0];
        var labels = sheet.Cells.Where(c => c.Col == 1).ToDictionary(c => c.Row, c => c.Value);
        return sheet.Cells.Where(c => c.Col == 2).ToDictionary(c => labels[c.Row], c => c);
    }

    [Theory]
    [InlineData("#,##0 (3)", "12,34,567")]
    [InlineData("#,##0.00 (4)", "-12,34,567.89")]
    [InlineData("rupee custom", "₹ 12,34,567.50")]
    [InlineData("en-IN grouping custom", "1,23,45,678")]
    [InlineData("0.00 (2)", "1234.50")]
    [InlineData("0% (9)", "26%")]
    [InlineData("0.00% (10)", "25.60%")]
    [InlineData("0.00E+00 (11)", "1.23E+05")]
    [InlineData("# ?/? (12)", "1 1/4")]
    [InlineData("fraction ??/100", " 37/100")]
    [InlineData("scale ,", "1,235K")]
    [InlineData("d-mmm-yy 15", "15-Mar-23")]
    [InlineData("dd/mm/yyyy", "15/03/2023")]
    [InlineData("dddd dd mmmm yyyy", "Wednesday, 15 March 2023")]
    [InlineData("[h]:mm:ss 46", "36:00:00")]
    [InlineData("4 sections pos", "5.0")]
    [InlineData("4 sections neg", "(5.0)")]
    [InlineData("4 sections zero", "zero")]
    [InlineData("4 sections text", "txt:abc")]
    [InlineData("condition [>100]", "big 150")]
    [InlineData("percent text", "50% done")]
    [InlineData("negative red no sign", "3")]
    [InlineData("text @ 49", "007")]
    [InlineData("bool", "TRUE")]
    [InlineData("error", "#DIV/0!")]
    [InlineData("conditional numFmt", "CF: 7.000")]
    public void A_cell_shows_its_number_format_in_the_system_culture(string label, string shown) =>
        Assert.Equal(shown, ByLabel(India)[label].Text);

    [Theory]
    [InlineData("4 sections neg", "#FF0000")]
    [InlineData("negative red no sign", "#FF0000")]
    [InlineData("condition [>100]", "#0000FF")]
    [InlineData("color10", "#008000")]
    public void A_colour_section_colours_the_text(string label, string colour) =>
        Assert.Equal(colour, ByLabel(India)[label].Color);

    [Fact]
    public void An_accounting_fill_keeps_the_symbol_at_the_left_edge()
    {
        var cell = ByLabel(India)["fill *"];
        Assert.Equal(" $12.00 ", cell.Text);
        Assert.Equal(' ', cell.FillCharacter);
        Assert.Equal(2, cell.FillIndex);
    }

    [Fact]
    public void The_system_culture_decides_grouping_and_names()
    {
        Assert.Equal("1,234,567", ByLabel(CultureInfo.InvariantCulture)["#,##0 (3)"].Text);
        Assert.Equal("12,34,567", ByLabel(India)["#,##0 (3)"].Text);
    }

    [Fact]
    public void Dates_and_numbers_align_right_and_booleans_centre_as_in_Excel()
    {
        var cells = ByLabel(India);
        Assert.Equal("Right", cells["dd/mm/yyyy"].Align);
        Assert.Equal("Right", cells["#,##0 (3)"].Align);
        Assert.Equal("Center", cells["bool"].Align);
        Assert.Equal("Left", cells["text @ 49"].Align);
    }

    /// <summary>Library item SH-L1 (Sheets 2.0.4): a time with no date (a stored value from 0 to 1, 1900 date system) is
    /// read one day early — 0.75 comes back as 1899-12-30 18:00, which is -0.25 — so its display is "########" and its
    /// stored value can't be recovered from the model. Excel shows 6:00 PM. Not worked around in the app (D-161).</summary>
    private static readonly HashSet<string> TimeOnly = ["h:mm AM/PM 18", "h:mm:ss 21", "system time F400", "ss.000"];

    [Fact(Skip = "Library item SH-L1: time-only values (stored 0 to 1) read one day early in Chuvadi.Sheets 2.0.4")]
    public void Time_only_values_keep_their_stored_value_and_show_as_times()
    {
        var cells = ByLabel(India);
        Assert.Equal("0.75", cells["h:mm AM/PM 18"].Value);
        Assert.Equal("6:00 PM", cells["h:mm AM/PM 18"].Text);
        Assert.Equal("12:15:00", cells["h:mm:ss 21"].Text);
    }

    /// <summary>The value under every cell is exactly what the file stores: read here from the sheet's own XML.</summary>
    [Fact]
    public void Every_cell_keeps_the_value_the_file_stores()
    {
        XNamespace ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
        using var zip = ZipFile.OpenRead(File_);
        var strings = XDocument.Load(zip.GetEntry("xl/sharedStrings.xml")!.Open()).Root!.Elements(ns + "si").Select(si => si.Value).ToList();
        var stored = XDocument.Load(zip.GetEntry("xl/worksheets/sheet1.xml")!.Open()).Descendants(ns + "c")
            .Where(c => ((string)c.Attribute("r")!).StartsWith('B'))
            .ToDictionary(c => int.Parse(((string)c.Attribute("r")!)[1..], CultureInfo.InvariantCulture), c =>
            {
                var v = (string)c.Element(ns + "v")!;
                return (string?)c.Attribute("t") switch
                {
                    "s" => strings[int.Parse(v, CultureInfo.InvariantCulture)],
                    "b" => v == "1" ? "TRUE" : "FALSE",
                    _ => v,
                };
            });

        var sheet = new XlsxViewService { Culture = India }.Load(File_).Sheets[0];
        var labels = sheet.Cells.Where(c => c.Col == 1).ToDictionary(c => c.Row, c => c.Value);
        var cells = sheet.Cells.Where(c => c.Col == 2).ToList();
        Assert.Equal(stored.Count, cells.Count);
        foreach (var cell in cells)
        {
            if (TimeOnly.Contains(labels[cell.Row]))
            {
                continue;   // see Time_only_values_keep_their_stored_value
            }


            var want = stored[cell.Row];
            if (double.TryParse(want, NumberStyles.Float, CultureInfo.InvariantCulture, out var number) && cell.IsNumber)
            {
                // The same number (the file may write 1.23456789012345E+20 where the shortest form is 1.23456789012345E+20).
                Assert.Equal(number, double.Parse(cell.Value, NumberStyles.Float, CultureInfo.InvariantCulture));
            }
            else
            {
                Assert.Equal(want, cell.Value);
            }
        }
    }
}
