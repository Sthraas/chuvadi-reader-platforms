using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Text;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>The PDF handed to an OS print system: chosen pages, in order, unencrypted, still vector.</summary>
public class PrintDocumentBuilderTests
{
    private static async Task<string> ThreePagesAsync()
    {
        var parts = new[] { TestPdf.TextPage("PAGE-ONE"), TestPdf.TextPage("PAGE-TWO"), TestPdf.TextPage("PAGE-THREE") };
        var output = TestPdf.TempOutput();
        await new PdfToolsService().MergeAsync(parts, output);
        return output;
    }

    private static List<string> PageTexts(byte[] pdf)
    {
        using var doc = PdfDocument.Open(new MemoryStream(pdf), leaveOpen: false);
        var ex = new TextExtractor(doc.Objects, ExtractionStrategy.Layout);
        return Enumerable.Range(0, doc.PageCount).Select(p => ex.ExtractText(doc.Pages[p]) ?? string.Empty).ToList();
    }

    [Fact]
    public async Task Range_keeps_the_typed_order_and_only_those_pages()
    {
        var src = await ThreePagesAsync();
        var result = await PrintDocumentBuilder.BuildAsync(src, new PrintRequest { PageRange = "3, 1" });

        Assert.Equal(2, result.PageCount);
        var texts = PageTexts(result.Pdf);
        Assert.Equal(2, texts.Count);
        Assert.Contains("PAGE-THREE", texts[0]);
        Assert.Contains("PAGE-ONE", texts[1]);
    }

    [Fact]
    public async Task Current_page_and_default_job_name()
    {
        var src = await ThreePagesAsync();
        var result = await PrintDocumentBuilder.BuildAsync(src, new PrintRequest { PageRange = "current", CurrentPage = 1 });

        Assert.Equal(1, result.PageCount);
        Assert.Contains("PAGE-TWO", PageTexts(result.Pdf)[0]);
        Assert.Equal(Path.GetFileName(src), result.JobName);
    }

    [Fact]
    public async Task Text_stays_text_not_an_image()
    {
        var src = await ThreePagesAsync();
        var result = await PrintDocumentBuilder.BuildAsync(src, new PrintRequest());

        // Extractable text in every page proves the pages were copied as vector content.
        Assert.All(PageTexts(result.Pdf), t => Assert.False(string.IsNullOrWhiteSpace(t)));
    }

    [Fact]
    public async Task Protected_file_prints_with_its_password_and_the_copy_is_unencrypted()
    {
        var src = await ThreePagesAsync();
        var locked = TestPdf.TempOutput();
        await new PasswordService().ProtectAsync(src, locked, new PasswordProtectOptions { OpenPassword = "open-sesame" });

        var result = await PrintDocumentBuilder.BuildAsync(locked, new PrintRequest { PageRange = "2", Password = "open-sesame" });

        using var doc = PdfDocument.Open(new MemoryStream(result.Pdf), leaveOpen: false);
        Assert.Null(doc.Encryption);
        Assert.Contains("PAGE-TWO", PageTexts(result.Pdf)[0]);
    }

    [Fact]
    public async Task Annotations_are_baked_into_the_page_and_none_stay_live()
    {
        // A red filled square annotation in the middle of a blank page.
        var src = TestPdf.BlankPage(200, 200);
        var annotated = TestPdf.TempOutput();
        using (var doc = PdfDocument.Open(src))
        using (var fs = File.Create(annotated))
        {
            var red = Chuvadi.Pdf.Graphics.ColorF.FromRgb(1, 0, 0, 1);
            var square = new Chuvadi.Pdf.Annotations.SquareAnnotation(
                0, new Chuvadi.Pdf.Graphics.RectangleF(50, 50, 100, 100),
                new Chuvadi.Pdf.Annotations.BorderStyle(1, Chuvadi.Pdf.Annotations.BorderStyleType.Solid, Array.Empty<float>()),
                red, string.Empty, red, string.Empty, 1f);
            Chuvadi.Pdf.Annotations.AnnotationWriter.Add(fs, doc, new[] { square });
        }

        var result = await PrintDocumentBuilder.BuildAsync(annotated, new PrintRequest());
        var printed = TestPdf.TempOutput();
        await File.WriteAllBytesAsync(printed, result.Pdf);

        using (var doc = PdfDocument.Open(printed))
        {
            Assert.Empty(Chuvadi.Pdf.Annotations.AnnotationReader.GetAllAnnotations(doc));
        }

        Assert.True(TestPdf.IsReddish(TestPdf.SamplePixel(printed, 0, 0.50, 0.50)), "the square should be baked into the page");
        Assert.True(TestPdf.IsWhitish(TestPdf.SamplePixel(printed, 0, 0.05, 0.05)), "outside the square stays white");
    }

    [Fact]
    public async Task Bad_range_gives_the_parser_message()
    {
        var src = await ThreePagesAsync();
        var ex = await Assert.ThrowsAsync<ArgumentException>(() => PrintDocumentBuilder.BuildAsync(src, new PrintRequest { PageRange = "9" }));
        Assert.Equal("Pages run from 1 to 3.", ex.Message);
    }
}
