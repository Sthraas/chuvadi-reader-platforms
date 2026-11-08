using System.Globalization;
using System.IO.Compression;
using System.Text.Json;
using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>
/// D-136: Word and Excel viewing on Chuvadi.Docs 2.0.0 and Chuvadi.Sheets 2.0.2. Every value comes through as
/// the file holds it. The truth is <c>Fixtures/Office/expected.json</c>, written by
/// <c>tools/OfficeCorpus/make.py</c> from the files' own XML and openpyxl, never from Chuvadi. Plus the
/// libraries' limits (B-08) and cancellation (B-08b).
/// </summary>
public sealed class OfficeViewTests
{
    private static readonly string Dir = Path.Combine(AppContext.BaseDirectory, "Fixtures", "Office");

    private static readonly JsonElement Expected =
        JsonDocument.Parse(File.ReadAllText(Path.Combine(Dir, "expected.json"))).RootElement;

    private static (int Row, int Col) Address(string a)
    {
        int col = 0, i = 0;
        for (; i < a.Length && char.IsLetter(a[i]); i++) col = (col * 26) + (char.ToUpperInvariant(a[i]) - 'A' + 1);
        return (int.Parse(a[i..], CultureInfo.InvariantCulture), col);
    }

    private static Dictionary<(int, int), string> Cells(WorkbookView wb, int sheet) =>
        wb.Sheets[sheet].Cells.ToDictionary(c => (c.Row, c.Col), c => c.Text);

    private static void SameNumber(double want, string shown, string where)
    {
        Assert.True(double.TryParse(shown, NumberStyles.Float, CultureInfo.CurrentCulture, out var got), $"{where}: '{shown}' isn't a number");
        Assert.True(Math.Abs(got - want) <= Math.Abs(want) * 1e-12, $"{where}: file holds {want}, viewer shows {shown}");
    }

    [Theory]
    [InlineData("values.xlsx")]
    [InlineData("dates1904.xlsx")]
    public void Every_kind_of_cell_value_shows_as_the_file_holds_it(string file)
    {
        var cells = Cells(new XlsxViewService().Load(Path.Combine(Dir, file)), 0);
        foreach (var group in Expected.GetProperty(file).EnumerateObject().Where(g => g.Name != "note"))
        {
            foreach (var cell in group.Value.EnumerateObject())
            {
                var where = $"{file} {cell.Name} ({group.Name})";
                Assert.True(cells.TryGetValue(Address(cell.Name), out var shown), $"{where}: missing");
                switch (group.Name)
                {
                    case "numbers":
                        SameNumber(cell.Value.GetDouble(), shown!, where);
                        break;
                    case "booleans":
                        Assert.Equal(cell.Value.GetBoolean() ? "TRUE" : "FALSE", shown);
                        break;
                    default: // strings (spaces, Tamil, line breaks, & and < kept), errors, dates in both systems
                        Assert.True(cell.Value.GetString() == shown, $"{where}: file holds '{cell.Value.GetString()}', viewer shows '{shown}'");
                        break;
                }
            }
        }
    }

    [Fact]
    public void A_200_row_workbook_shows_every_cell_as_the_file_holds_it()
    {
        var wb = new XlsxViewService().Load(Path.Combine(Dir, "realistic.xlsx"));
        var e = Expected.GetProperty("realistic.xlsx");
        var count = 0;
        foreach (var cell in e.GetProperty("cells").EnumerateObject())
        {
            var bang = cell.Name.IndexOf('!');
            var sheet = int.Parse(cell.Name[..bang], CultureInfo.InvariantCulture);
            var shown = Cells(wb, sheet).GetValueOrDefault(Address(cell.Name[(bang + 1)..]));
            Assert.True(shown is not null, $"{cell.Name}: missing");
            if (cell.Value.GetProperty("kind").GetString() == "number")
            {
                SameNumber(cell.Value.GetProperty("value").GetDouble(), shown!, cell.Name);
            }
            else
            {
                Assert.Equal(cell.Value.GetProperty("value").GetString(), shown);
            }

            count++;
        }

        Assert.Equal(1153, count);
        foreach (var empty in e.GetProperty("empty").EnumerateArray().Select(x => x.GetString()!))
        {
            var bang = empty.IndexOf('!');
            Assert.Equal(string.Empty, Cells(wb, 0).GetValueOrDefault(Address(empty[(bang + 1)..]), string.Empty));
        }
    }

    [Fact]
    public void A_stray_cell_at_the_sheets_far_corner_opens_quickly()
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var wb = new XlsxViewService().Load(Path.Combine(Dir, "far-cell.xlsx")); // B-09: cell at XFD1048576
        Assert.True(sw.Elapsed < TimeSpan.FromSeconds(20), $"took {sw.Elapsed}");
        Assert.NotEmpty(wb.Sheets);
    }

    private static List<string> Texts(IEnumerable<WordBlock> blocks) => blocks
        .Select(b => b switch { WordHeading h => h.Runs, WordPara p => p.Runs, _ => null })
        .Where(runs => runs is not null && !runs.All(r => r.ImageDataUrl is not null))
        .Select(runs => string.Concat(runs!.Select(r => r.Text)))
        .ToList();

    [Theory]
    [InlineData("discharge.docx")]
    [InlineData("landscape.docx")]
    public void Word_text_tables_headers_and_pages_come_through_as_the_file_holds_them(string file)
    {
        var view = new DocxViewService().Load(Path.Combine(Dir, file));
        var e = Expected.GetProperty(file);

        // Tabs and line breaks stay in the text (\t, \n); double, leading and trailing spaces stay.
        Assert.Equal(e.GetProperty("paragraph_texts_in_order").EnumerateArray().Select(x => x.GetString()), Texts(view.Blocks));
        if (e.TryGetProperty("table", out var table))
        {
            var t = Assert.Single(view.Blocks.OfType<WordTableBlock>());
            var shown = t.Rows.Select(r => r.Cells.Select(c => string.Concat(Texts(c.Content))).ToList()).ToList();
            Assert.Equal(table.EnumerateArray().Select(r => r.EnumerateArray().Select(x => x.GetString()!).ToList()).ToList(), shown);
        }

        if (e.TryGetProperty("header", out var header))
        {
            Assert.Equal(header.GetString(), string.Concat(Texts(view.Header)));
            Assert.Equal(e.GetProperty("footer").GetString(), string.Concat(Texts(view.Footer)));
        }

        if (e.TryGetProperty("landscape", out var landscape))
        {
            Assert.Equal(landscape.GetBoolean(), view.Landscape);
            Assert.Equal(e.GetProperty("images").GetInt32(), view.Blocks.OfType<WordPara>().SelectMany(p => p.Runs).Count(r => r.ImageDataUrl is not null));
        }
    }

    // ── B-08: zip bombs are refused by the libraries' own limits ──

    private static string Bomb(string extension, string part, long bytes)
    {
        var path = Path.Combine(Path.GetTempPath(), $"bomb-{Guid.NewGuid():N}{extension}");
        using (var zip = ZipFile.Open(path, ZipArchiveMode.Create))
        {
            using (var w = new StreamWriter(zip.CreateEntry("[Content_Types].xml").Open()))
            {
                w.Write("<?xml version=\"1.0\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"/>");
            }

            using var s = zip.CreateEntry(part, CompressionLevel.SmallestSize).Open();
            var zeros = new byte[1 << 20];
            for (long written = 0; written < bytes; written += zeros.Length)
            {
                s.Write(zeros, 0, (int)Math.Min(zeros.Length, bytes - written));
            }
        }

        return path;
    }

    [Fact]
    public void A_word_zip_bomb_is_refused_by_the_library_as_too_large()
    {
        var path = Bomb(".docx", "word/document.xml", 100L * 1024 * 1024); // 100 MB of zeros: over the 64 MB total
        Assert.True(new FileInfo(path).Length < 2 * 1024 * 1024, "the bomb itself is small");

        var ex = Assert.Throws<DocumentViewException>(() => new DocxViewService().Load(path));

        Assert.Equal(ViewErrorReason.TooLarge, ex.Reason);
        Assert.Contains("too large to open", ex.Message);
    }

    [Fact]
    public void An_excel_zip_bomb_is_refused_by_the_library_as_too_large()
    {
        var path = Bomb(".xlsx", "xl/worksheets/sheet1.xml", 100L * 1024 * 1024); // compresses far beyond 500:1

        var ex = Assert.Throws<DocumentViewException>(() => new XlsxViewService().Load(path));

        Assert.Equal(ViewErrorReason.TooLarge, ex.Reason);
    }

    [Fact]
    public void The_word_limits_are_the_agreed_ones()
    {
        var o = DocxViewService.ReadOptions();
        Assert.Equal(20L * 1024 * 1024, o.MaxPartBytes);
        Assert.Equal(64L * 1024 * 1024, o.MaxTotalUncompressedBytes);
    }

    // ── B-08b: the read's cancellation reaches the library ──

    [Fact]
    public void A_cancelled_word_read_stops_in_the_library()
    {
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();

        Assert.ThrowsAny<OperationCanceledException>(() => new DocxViewService().Load(Path.Combine(Dir, "discharge.docx"), null, cancelled.Token));
    }

    [Fact]
    public void A_cancelled_excel_read_stops_in_the_library()
    {
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();

        Assert.ThrowsAny<OperationCanceledException>(() => new XlsxViewService().Load(Path.Combine(Dir, "realistic.xlsx"), null, cancelled.Token));
        Assert.Equal(cancelled.Token, XlsxViewService.ReadOptions(cancelled.Token).CancellationToken);
    }
}
