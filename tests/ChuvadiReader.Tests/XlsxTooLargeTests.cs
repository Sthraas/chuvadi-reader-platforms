using System.IO.Compression;
using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>WT-18: a workbook the library refuses for its size is called too large, not damaged. The library's
/// own refusal of an oversized part is a plain "invalid data" error (library item SH-L2), so the Core asks the
/// file's zip table of contents, and only after the refusal.</summary>
public sealed class XlsxTooLargeTests
{
    private const string Types = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>";
    private const string Rels = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>";
    private const string Book = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"S\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>";
    private const string BookRels = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>";

    /// <summary>A workbook whose one sheet holds a single text cell of <paramref name="megabytes"/> MB.</summary>
    private static string Workbook(int megabytes, CompressionLevel level = CompressionLevel.Fastest)
    {
        var path = Path.Combine(Path.GetTempPath(), $"chvd-big-{Guid.NewGuid():N}.xlsx");
        using var zip = ZipFile.Open(path, ZipArchiveMode.Create);
        void Add(string name, string text) { using var w = new StreamWriter(zip.CreateEntry(name).Open()); w.Write(text); }
        Add("[Content_Types].xml", Types);
        Add("_rels/.rels", Rels);
        Add("xl/workbook.xml", Book);
        Add("xl/_rels/workbook.xml.rels", BookRels);
        using var sheet = zip.CreateEntry("xl/worksheets/sheet1.xml", level).Open();
        sheet.Write("<?xml version=\"1.0\" encoding=\"UTF-8\"?><worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData><row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><is><t>"u8);
        var block = new byte[1 << 20];
        Array.Fill(block, (byte)'x');
        for (int i = 0; i < megabytes; i++) sheet.Write(block);
        sheet.Write("</t></is></c></row></sheetData></worksheet>"u8);
        return path;
    }

    [Fact]
    public void A_part_over_the_size_limit_is_called_too_large_not_damaged()
    {
        var path = Workbook(megabytes: 300);
        try
        {
            var ex = Assert.Throws<DocumentViewException>(() => new XlsxViewService().Load(path));
            Assert.Equal(ViewErrorReason.TooLarge, ex.Reason);
            Assert.Contains("too large to open", ex.Message);
            Assert.NotNull(ex.InnerException); // the library's own words stay as the detail
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Each_declared_limit_is_recognised_and_a_file_within_them_is_not()
    {
        var path = Workbook(megabytes: 2, CompressionLevel.NoCompression);
        try
        {
            var limits = XlsxViewService.ReadOptions(default);
            Assert.False(XlsxViewService.BeyondPackageLimits(path, limits));

            var part = XlsxViewService.ReadOptions(default); part.MaxPartBytes = 1 << 20;
            Assert.True(XlsxViewService.BeyondPackageLimits(path, part));
            var total = XlsxViewService.ReadOptions(default); total.MaxTotalUncompressedBytes = 1 << 20;
            Assert.True(XlsxViewService.BeyondPackageLimits(path, total));
            var entries = XlsxViewService.ReadOptions(default); entries.MaxPackageEntries = 3;
            Assert.True(XlsxViewService.BeyondPackageLimits(path, entries));
        }
        finally { File.Delete(path); }

        var squeezed = Workbook(megabytes: 2, CompressionLevel.SmallestSize); // 2 MB of one letter: far over 500 to 1
        try { Assert.True(XlsxViewService.BeyondPackageLimits(squeezed, XlsxViewService.ReadOptions(default))); }
        finally { File.Delete(squeezed); }
    }

    [Fact]
    public void A_damaged_file_is_still_called_damaged()
    {
        var path = Path.Combine(Path.GetTempPath(), $"chvd-bad-{Guid.NewGuid():N}.xlsx");
        File.WriteAllBytes(path, [0x50, 0x4B, 0x03, 0x04, 1, 2, 3, 4, 5, 6, 7, 8]);
        try
        {
            Assert.False(XlsxViewService.BeyondPackageLimits(path, XlsxViewService.ReadOptions(default)));
            var ex = Assert.ThrowsAny<Exception>(() => new XlsxViewService().Load(path));
            Assert.False(ex is DocumentViewException { Reason: ViewErrorReason.TooLarge });
        }
        finally { File.Delete(path); }
    }
}
