using System.Text;
using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>Reading a text file as an encoding chosen by hand: the list, the read, and the count of bytes that do
/// not fit. The data rule is the same as everywhere: show what the file holds, and say so when it does not fit.</summary>
public sealed class TextEncodingTests
{
    [Fact]
    public void Every_listed_encoding_exists_and_is_listed_once()
    {
        Assert.Equal(TextEncodings.All.Count, TextEncodings.All.Select(c => c.CodePage).Distinct().Count());
        Assert.Equal(TextEncodings.All.Count, TextEncodings.All.Select(c => c.Name).Distinct().Count());
        foreach (var choice in TextEncodings.All)
        {
            // Plain ASCII reads the same in every one of them (ISO-2022-JP included), with nothing left over.
            var text = TextEncodings.Decode("plain 123"u8, choice.CodePage, out int bad);
            if (choice.CodePage is TextEncodings.Utf16Le or TextEncodings.Utf16Be) continue; // not ASCII-compatible
            Assert.True(text == "plain 123" && bad == 0, choice.Name);
            Assert.Same(choice, TextEncodings.Find(choice.CodePage));
        }
        Assert.Null(TextEncodings.Find(1));
    }

    [Theory]
    [InlineData(1251, "Привет, мир")]
    [InlineData(20866, "Привет, мир")]
    [InlineData(866, "Привет, мир")]
    [InlineData(1253, "Καλημέρα")]
    [InlineData(1250, "Zażółć gęślą jaźń")]
    [InlineData(1254, "İstanbul ğüşöç")]
    [InlineData(1255, "שלום")]
    [InlineData(1256, "مرحبا")]
    [InlineData(874, "สวัสดี")]
    [InlineData(1258, "Tiêng")]
    [InlineData(932, "こんにちは 世界")]
    [InlineData(51932, "こんにちは 世界")]
    [InlineData(50220, "こんにちは 世界")]
    [InlineData(54936, "你好，世界")]
    [InlineData(936, "你好，世界")]
    [InlineData(950, "你好，世界")]
    [InlineData(949, "안녕하세요")]
    [InlineData(51949, "안녕하세요")]
    [InlineData(57004, "வணக்கம்")]
    [InlineData(57002, "नमस्ते")]
    [InlineData(28605, "5 € œ")]
    [InlineData(10000, "café – ƒ")]
    [InlineData(65001, "வணக்கம் café")]
    [InlineData(1200, "வணக்கம் café")]
    [InlineData(1201, "வணக்கம் café")]
    public void A_chosen_encoding_reads_its_own_bytes_back_exactly(int codePage, string text)
    {
        // The bytes are made with .NET's own encoder for that code page, then read through our path.
        TextEncodings.Decode("x"u8, codePage, out _); // makes sure the provider is on for GetEncoding below
        var bytes = Encoding.GetEncoding(codePage).GetBytes(text);
        Assert.Equal(text, TextEncodings.Decode(bytes, codePage, out int bad));
        Assert.Equal(0, bad);
    }

    [Fact]
    public void Bytes_that_do_not_fit_are_shown_as_a_mark_and_counted_never_dropped()
    {
        // Windows-1251 text read as UTF-8: every Cyrillic byte is invalid there.
        TextEncodings.Decode("x"u8, 1251, out _);
        var cyr = Encoding.GetEncoding(1251).GetBytes("Привет");
        byte[] bytes = [(byte)'a', .. cyr, (byte)'b'];
        var text = TextEncodings.Decode(bytes, TextEncodings.Utf8, out int bad);
        Assert.Equal(6, bad);
        Assert.StartsWith("a", text);
        Assert.EndsWith("b", text);
        Assert.Contains('�', text);
        Assert.DoesNotContain('?', text);

        // A lone trail byte in Shift-JIS, and an odd byte at the end of UTF-16.
        TextEncodings.Decode([0x82], 932, out int sjis);
        Assert.Equal(1, sjis);
        Assert.Equal("A�", TextEncodings.Decode([0x41, 0x00, 0x42], TextEncodings.Utf16Le, out int odd));
        Assert.Equal(1, odd);
    }

    [Theory]
    [InlineData(1253, 0xAA, 1)]   // undefined in Greek
    [InlineData(1255, 0xD9, 1)]   // undefined in Hebrew
    [InlineData(1251, 0x98, 1)]   // undefined in Cyrillic
    [InlineData(1250, 0x81, 1)]
    [InlineData(28597, 0xAE, 1)]
    [InlineData(1251, 0xC0, 0)]   // А
    [InlineData(28591, 0x85, 0)]  // a real control code in ISO-8859-1
    [InlineData(10000, 0xF0, 0)]  // Mac Roman's Apple sign
    [InlineData(437, 0xB0, 0)]
    public void A_byte_a_one_byte_code_page_leaves_undefined_is_counted_and_still_shown(int codePage, int value, int expected)
    {
        var text = TextEncodings.Decode([(byte)'a', (byte)value, (byte)'b'], codePage, out int bad);
        Assert.Equal(expected, bad);
        Assert.Equal(3, text.Length); // one character per byte, none dropped
        Assert.Equal('a', text[0]);
        Assert.Equal('b', text[2]);
    }

    [Fact]
    public void Windows_1252_by_hand_matches_the_automatic_read()
    {
        var all = Enumerable.Range(1, 255).Select(i => (byte)i).ToArray();
        var auto = TextViewService.Decode([0x63, 0xE9, .. all], out var name);
        Assert.Equal("Windows-1252", name);
        Assert.Equal(auto, TextEncodings.Decode([0x63, 0xE9, .. all], TextEncodings.Windows1252, out int bad));
        Assert.Equal(5, bad); // 81, 8D, 8F, 90, 9D: shown as Windows shows them, and counted
        Assert.Equal("café", TextEncodings.Decode([0x63, 0x61, 0x66, 0xE9], TextEncodings.Windows1252, out int none));
        Assert.Equal(0, none);
        Assert.Equal(TextEncodings.Windows1252, TextEncodings.CodePageOfDetected(name));
    }

    [Fact]
    public void A_byte_order_mark_is_consumed_only_by_its_own_encoding()
    {
        byte[] utf8 = [0xEF, 0xBB, 0xBF, (byte)'h', (byte)'i'];
        Assert.Equal("hi", TextEncodings.Decode(utf8, TextEncodings.Utf8, out _));
        Assert.Equal("ï»¿hi", TextEncodings.Decode(utf8, TextEncodings.Windows1252, out _)); // shown, since asked
        byte[] utf16 = [0xFF, 0xFE, (byte)'h', 0, (byte)'i', 0];
        Assert.Equal("hi", TextEncodings.Decode(utf16, TextEncodings.Utf16Le, out _));
    }

    [Fact]
    public void Load_with_a_chosen_encoding_reports_it_and_the_automatic_load_is_unchanged()
    {
        var path = Path.Combine(Path.GetTempPath(), $"chvd-enc-{Guid.NewGuid():N}.txt");
        TextEncodings.Decode("x"u8, 1251, out _);
        File.WriteAllBytes(path, Encoding.GetEncoding(1251).GetBytes("Привет\r\nмир"));
        try
        {
            var service = new TextViewService();

            var auto = service.Load(path);
            Assert.Equal("Windows-1252", auto.EncodingName);
            Assert.Equal(TextEncodings.Windows1252, auto.CodePage);
            Assert.False(auto.EncodingChosen);
            Assert.Equal(0, auto.BytesNotFitting);

            var chosen = service.Load(path, 1251);
            Assert.Equal(new[] { "Привет", "мир" }, chosen.Lines);
            Assert.Equal("Cyrillic (Windows-1251)", chosen.EncodingName);
            Assert.Equal(1251, chosen.CodePage);
            Assert.True(chosen.EncodingChosen);
            Assert.Equal(0, chosen.BytesNotFitting);

            var wrong = service.Load(path, TextEncodings.Utf8);
            Assert.Equal(9, wrong.BytesNotFitting);
            Assert.Equal(2, wrong.Lines.Count); // the line break is still a line break

            Assert.Throws<DocumentViewException>(() => service.Load(path, 99999));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void A_chosen_encoding_is_not_refused_as_binary()
    {
        // UTF-16 without a mark is full of zero bytes; the automatic read calls that binary, a chosen read shows it.
        var bytes = Encoding.Unicode.GetBytes("hello வணக்கம்");
        Assert.Throws<DocumentViewException>(() => TextViewService.Decode(bytes, out _));
        Assert.Equal("hello வணக்கம்", TextEncodings.Decode(bytes, TextEncodings.Utf16Le, out int bad));
        Assert.Equal(0, bad);
    }
}
