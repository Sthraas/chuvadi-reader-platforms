using System.Text;
using ChuvadiReader.Web.Files;

namespace ChuvadiReader.Web.Tests;

public class UploadTests
{
    private static readonly byte[] Pdf = Encoding.ASCII.GetBytes("%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n");

    private static UploadTicket NewTicket(PickKind kind = PickKind.Document, bool multiple = false, long maxBytes = 1024 * 1024)
    {
        var reg = new TransferRegistry(TimeProvider.System);
        return reg.CreateUpload(new string('a', 32), "s1", SpaceLayoutTests.NewTempDir(), kind, multiple, 3, maxBytes, TimeSpan.FromMinutes(5));
    }

    [Fact]
    public async Task A_pdf_uploaded_in_chunks_is_complete_and_byte_identical()
    {
        var t = NewTicket();
        var (f, error) = t.Begin("Report.pdf", Pdf.Length);
        Assert.Null(error);
        Assert.Null(await f!.AppendAsync(0, new MemoryStream(Pdf[..10]), 1024, default));
        Assert.False(f.IsComplete);
        Assert.Null(await f.AppendAsync(10, new MemoryStream(Pdf[10..]), 1024, default));
        Assert.True(f.IsComplete);
        Assert.Equal(Pdf, File.ReadAllBytes(f.Path));
        Assert.Equal("Report.pdf", Path.GetFileName(f.Path));
        Assert.Single(t.Completed(["0"]));
    }

    [Fact]
    public async Task Chunks_out_of_order_or_beyond_the_announced_size_are_refused()
    {
        var t = NewTicket();
        var (f, _) = t.Begin("a.pdf", Pdf.Length);
        Assert.NotNull(await f!.AppendAsync(5, new MemoryStream(Pdf[..5]), 1024, default));
        Assert.Null(await f.AppendAsync(0, new MemoryStream(Pdf[..5]), 1024, default));
        Assert.NotNull(await f.AppendAsync(5, new MemoryStream(new byte[Pdf.Length]), 1024, default));
        Assert.Equal(5, f.Received);
        Assert.Equal(5, new FileInfo(f.Path).Length);
    }

    [Fact]
    public async Task A_chunk_larger_than_the_chunk_limit_is_refused()
    {
        var t = NewTicket();
        var (f, _) = t.Begin("a.pdf", Pdf.Length);
        Assert.NotNull(await f!.AppendAsync(0, new MemoryStream(Pdf), 8, default));
        Assert.Equal(0, f.Received);
    }

    [Fact]
    public async Task A_renamed_file_is_refused_and_removed()
    {
        var t = NewTicket();
        var fake = Encoding.ASCII.GetBytes("MZ\u0090\u0000 not a pdf at all");
        var (f, _) = t.Begin("invoice.pdf", fake.Length);
        var error = await f!.AppendAsync(0, new MemoryStream(fake), 1024, default);
        Assert.Contains("isn't a valid PDF", error, StringComparison.Ordinal);
        Assert.False(f.IsComplete);
        Assert.False(File.Exists(f.Path));
        Assert.Empty(t.Completed(["0"]));
    }

    [Theory]
    [InlineData("setup.exe")]
    [InlineData("macro.docm")]
    [InlineData("noextension")]
    public void Types_the_desktop_doesnt_open_are_refused_before_any_bytes(string name)
    {
        var (f, error) = NewTicket().Begin(name, 10);
        Assert.Null(f);
        Assert.NotNull(error);
    }

    [Fact]
    public void Size_and_count_limits_hold()
    {
        var t = NewTicket(PickKind.Pdf, multiple: true, maxBytes: 100);
        Assert.NotNull(t.Begin("big.pdf", 101).Error);
        Assert.NotNull(t.Begin("empty.pdf", 0).Error);
        Assert.Null(t.Begin("1.pdf", 10).Error);
        Assert.Null(t.Begin("2.pdf", 10).Error);
        Assert.Null(t.Begin("3.pdf", 10).Error);
        Assert.NotNull(t.Begin("4.pdf", 10).Error);
    }

    [Fact]
    public void A_single_pick_takes_one_file()
    {
        var t = NewTicket(multiple: false);
        Assert.Null(t.Begin("1.pdf", 10).Error);
        Assert.NotNull(t.Begin("2.pdf", 10).Error);
    }

    [Fact]
    public void Two_files_with_the_same_name_do_not_overwrite_each_other()
    {
        var t = NewTicket(PickKind.Pdf, multiple: true);
        var a = t.Begin("same.pdf", 10).File!;
        var b = t.Begin("same.pdf", 10).File!;
        Assert.NotEqual(a.Path, b.Path);
        Assert.Equal("same.pdf", Path.GetFileName(b.Path));
    }

    [Fact]
    public async Task Incomplete_files_are_discarded()
    {
        var t = NewTicket();
        var (f, _) = t.Begin("half.pdf", Pdf.Length);
        await f!.AppendAsync(0, new MemoryStream(Pdf[..5]), 1024, default);
        t.DiscardIncomplete();
        Assert.False(File.Exists(f.Path));
    }

    [Theory]
    [InlineData("a.png", new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A }, true)]
    [InlineData("a.jpg", new byte[] { 0xFF, 0xD8, 0xFF, 0xE0 }, true)]
    [InlineData("a.docx", new byte[] { 0x50, 0x4B, 0x03, 0x04 }, true)]
    [InlineData("a.xlsx", new byte[] { 0x25, 0x50, 0x44, 0x46 }, false)]
    [InlineData("a.txt", new byte[] { 0x68, 0x00, 0x69 }, false)]
    [InlineData("a.md", new byte[] { 0x23, 0x20, 0x48 }, true)]
    [InlineData("a.p12", new byte[] { 0x30, 0x82 }, true)]
    public void Content_must_match_the_extension(string name, byte[] head, bool ok)
        => Assert.Equal(ok, FileKinds.ContentMatches(name, head));
}
