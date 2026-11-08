using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>B-07: a password-protected PDF asks for its password in its tab and opens with it.</summary>
public class PdfPasswordTabTests
{
    private static async Task<string> LockedPdf(string password)
    {
        var output = TestPdf.TempOutput();
        await new PasswordService().ProtectAsync(TestPdf.TextPage("Locked page"), output,
            new PasswordProtectOptions { OpenPassword = password });
        return output;
    }

    [Fact]
    public async Task A_locked_pdf_asks_for_its_password_instead_of_failing()
    {
        var path = await LockedPdf("open-sesame");
        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());

        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);

        Assert.True(tab.NeedsPassword);
        Assert.Null(tab.Error);
        Assert.Null(tab.PasswordError);
        Assert.Null(tab.Session);
    }

    [Fact]
    public async Task A_wrong_password_says_so_and_asks_again()
    {
        var path = await LockedPdf("open-sesame");
        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);

        await tabs.UnlockAsync(tab.Id, "nope");

        Assert.True(tab.NeedsPassword);
        Assert.Equal("That password doesn't open this file.", tab.PasswordError);
        Assert.Null(tab.Session);
        Assert.Null(tab.Password);
    }

    [Fact]
    public async Task The_right_password_opens_the_tab()
    {
        var path = await LockedPdf("open-sesame");
        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);

        await tabs.UnlockAsync(tab.Id, "nope");
        await tabs.UnlockAsync(tab.Id, "open-sesame");

        Assert.False(tab.NeedsPassword);
        Assert.Null(tab.PasswordError);
        Assert.NotNull(tab.Session);
        Assert.Equal(1, tab.Session!.Document.PageCount);
        Assert.True(tab.Session.Document.IsEncrypted);
    }
}

/// <summary>B-11: an unreadable PDF shows the damaged-file state with the library's text kept as detail.</summary>
public class DamagedPdfTabTests
{
    [Fact]
    public async Task A_bad_startxref_offset_is_reported_as_damaged_not_as_parser_text()
    {
        var src = TestPdf.TextPage("Page");
        var bytes = File.ReadAllText(src, System.Text.Encoding.Latin1);
        var at = bytes.LastIndexOf("startxref", StringComparison.Ordinal);
        var end = bytes.IndexOf("%%EOF", at, StringComparison.Ordinal);
        var broken = bytes[..at] + "startxref\n999999\n" + bytes[end..];
        var path = TestPdf.TempOutput();
        File.WriteAllText(path, broken, System.Text.Encoding.Latin1);

        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);

        Assert.Null(tab.Session);
        Assert.True(tab.IsDamaged);
        Assert.Equal("This PDF is damaged", tab.Error);
        Assert.False(string.IsNullOrEmpty(tab.ErrorDetail));

        // "Try to repair (new copy)" rebuilds it, and the copy opens.
        var repaired = await new RecoveryService(new SaveFolderService(new MemoryStorage())).RecoverAsync(path, Path.GetTempPath());
        Assert.True(repaired.Repaired);
        var copy = await tabs.OpenAsync(repaired.OutputPath, Path.GetFileName(repaired.OutputPath), DocumentFormat.Pdf);
        Assert.NotNull(copy.Session);
        Assert.Equal(1, copy.Session!.Document.PageCount);
    }

    [Fact]
    public async Task An_empty_file_is_reported_as_damaged()
    {
        var path = TestPdf.TempOutput();
        File.WriteAllBytes(path, []);

        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);

        Assert.True(tab.IsDamaged);
        Assert.Equal("This PDF is damaged", tab.Error);
        Assert.Contains("startxref", tab.ErrorDetail);
    }
}
