using System.Text;

namespace ChuvadiReader.Core.Documents;

/// <summary>One encoding a text file can be read as. <see cref="CodePage"/> is the .NET code page number and is
/// the stable id (store that, not the name).</summary>
public sealed record TextEncodingChoice(int CodePage, string Name, string Group);

/// <summary>The encodings offered for reading a text file again when the automatic choice shows the wrong letters,
/// and the decoding itself. Everything here is .NET's own: Unicode and Latin-1 are always present, and the older
/// code pages come from the code-pages provider that ships inside .NET, which is switched on the first time one of
/// them is asked for and never at startup.</summary>
public static class TextEncodings
{
    public const int Utf8 = 65001;
    public const int Utf16Le = 1200;
    public const int Utf16Be = 1201;
    public const int Windows1252 = 1252;
    private const int Latin1 = 28591;
    private const int Utf32Le = 12000;
    private const int Utf32Be = 12001;

    /// <summary>The list for a picker, in the order to show it, grouped by <see cref="TextEncodingChoice.Group"/>.</summary>
    public static IReadOnlyList<TextEncodingChoice> All { get; } =
    [
        new(Utf8, "UTF-8", "Unicode"),
        new(Utf16Le, "UTF-16 LE", "Unicode"),
        new(Utf16Be, "UTF-16 BE", "Unicode"),

        new(Windows1252, "Western (Windows-1252)", "Western"),
        new(Latin1, "Western (ISO-8859-1)", "Western"),
        new(28605, "Western (ISO-8859-15)", "Western"),
        new(10000, "Western (Mac Roman)", "Western"),
        new(850, "Western (DOS 850)", "Western"),
        new(437, "US (DOS 437)", "Western"),

        new(1250, "Central European (Windows-1250)", "European"),
        new(28592, "Central European (ISO-8859-2)", "European"),
        new(1257, "Baltic (Windows-1257)", "European"),
        new(1253, "Greek (Windows-1253)", "European"),
        new(28597, "Greek (ISO-8859-7)", "European"),
        new(1254, "Turkish (Windows-1254)", "European"),

        new(1251, "Cyrillic (Windows-1251)", "Cyrillic"),
        new(20866, "Cyrillic (KOI8-R)", "Cyrillic"),
        new(21866, "Cyrillic (KOI8-U)", "Cyrillic"),
        new(866, "Cyrillic (DOS 866)", "Cyrillic"),
        new(28595, "Cyrillic (ISO-8859-5)", "Cyrillic"),

        new(1255, "Hebrew (Windows-1255)", "Middle Eastern"),
        new(1256, "Arabic (Windows-1256)", "Middle Eastern"),

        new(57004, "Tamil (ISCII)", "Indian"),
        new(57002, "Devanagari (ISCII)", "Indian"),
        new(57005, "Telugu (ISCII)", "Indian"),
        new(57008, "Kannada (ISCII)", "Indian"),
        new(57009, "Malayalam (ISCII)", "Indian"),
        new(57003, "Bengali (ISCII)", "Indian"),

        new(932, "Japanese (Shift-JIS)", "East Asian"),
        new(51932, "Japanese (EUC-JP)", "East Asian"),
        new(50220, "Japanese (ISO-2022-JP)", "East Asian"),
        new(54936, "Chinese Simplified (GB18030)", "East Asian"),
        new(936, "Chinese Simplified (GBK)", "East Asian"),
        new(950, "Chinese Traditional (Big5)", "East Asian"),
        new(949, "Korean (Windows-949)", "East Asian"),
        new(51949, "Korean (EUC-KR)", "East Asian"),

        new(874, "Thai (Windows-874)", "South-East Asian"),
        new(1258, "Vietnamese (Windows-1258)", "South-East Asian"),
    ];

    /// <summary>D-191: the encodings the first picker offers, after "Automatic" (which is no code page: null).
    /// All four are .NET's own or the Reader's own table, so choosing any of them never switches the code-pages
    /// provider on. <see cref="All"/> is the longer list for "More encodings", when that is decided.</summary>
    public static IReadOnlyList<TextEncodingChoice> FirstChoices { get; } =
    [
        new(Utf8, "UTF-8", "Unicode"),
        new(Windows1252, "Windows-1252", "Western"),
        new(Utf16Le, "UTF-16 LE", "Unicode"),
        new(Utf16Be, "UTF-16 BE", "Unicode"),
    ];

    /// <summary>The name to show for a code page: the short one where the first picker has it (so "Windows-1252"
    /// reads the same whether it was chosen or worked out), else the long list's, else the number.</summary>
    public static string NameOf(int codePage)
    {
        foreach (var choice in FirstChoices)
            if (choice.CodePage == codePage) return choice.Name;
        return Find(codePage)?.Name ?? "Code page " + codePage.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }

    /// <summary>The list entry for a code page number, or null when it is not one of ours.</summary>
    public static TextEncodingChoice? Find(int codePage)
    {
        foreach (var choice in All)
            if (choice.CodePage == codePage) return choice;
        return null;
    }

    /// <summary>The code page number behind a name <see cref="TextViewService.Decode(ReadOnlySpan{byte}, out string)"/>
    /// reports for an automatic read ("UTF-8", "UTF-16 LE", "Windows-1252" and so on), so a picker can mark the
    /// current one. Zero when the name is not known.</summary>
    public static int CodePageOfDetected(string encodingName) => encodingName switch
    {
        "UTF-8" => Utf8,
        "UTF-16 LE" => Utf16Le,
        "UTF-16 BE" => Utf16Be,
        "UTF-32 LE" => Utf32Le,
        "UTF-32 BE" => Utf32Be,
        "Windows-1252" => Windows1252,
        _ => 0,
    };

    /// <summary>Reads bytes as the chosen encoding. Nothing is guessed and nothing is refused: bytes that are not
    /// valid in that encoding become U+FFFD (in a one-byte code page, the stand-in character Windows gives an
    /// undefined byte) and are counted in <paramref name="bytesNotFitting"/>, so the caller can say "312 bytes do
    /// not fit this encoding" rather than show a quietly wrong page. A byte-order mark is
    /// consumed only when it is the chosen encoding's own.</summary>
    public static string Decode(ReadOnlySpan<byte> bytes, int codePage, out int bytesNotFitting)
    {
        bytesNotFitting = 0;

        // Windows-1252 keeps the table the automatic read uses, so choosing it by hand gives the same letters,
        // and the code-pages provider stays off for the commonest choice.
        if (codePage == Windows1252)
        {
            bytesNotFitting = UndefinedIn1252(bytes);
            return TextViewService.Windows1252(bytes);
        }

        var counter = new CountingFallback();
        Encoding encoding;
        try
        {
            encoding = Resolve(codePage, counter);
        }
        catch (Exception ex) when (ex is NotSupportedException or ArgumentException)
        {
            throw new DocumentViewException(ViewErrorReason.Other, "This encoding isn't available on this device.", ex);
        }

        var preamble = encoding.Preamble;
        if (preamble.Length > 0 && bytes.StartsWith(preamble)) bytes = bytes[preamble.Length..];

        // One pass through the decoder, so each byte that does not fit is counted once (GetString would run the
        // fallback twice: once to measure, once to read).
        var chars = new char[encoding.GetMaxCharCount(bytes.Length)];
        int written = encoding.GetDecoder().GetChars(bytes, chars, flush: true);
        bytesNotFitting = counter.Bytes + UndefinedSingleBytes(encoding, codePage, chars.AsSpan(0, written));
        return new string(chars, 0, written);
    }

    /// <summary>How many of these bytes Windows-1252 leaves undefined (81, 8D, 8F, 90, 9D). They are still shown,
    /// as the control codes Windows reads them as; a text file that holds them was most likely not written in
    /// Windows-1252, which is what the count is for.</summary>
    internal static int UndefinedIn1252(ReadOnlySpan<byte> bytes)
    {
        int n = 0;
        foreach (byte b in bytes)
            if (b is 0x81 or 0x8D or 0x8F or 0x90 or 0x9D) n++;
        return n;
    }

    // A one-byte code page never fails to decode: .NET, like Windows, gives a byte the page leaves undefined a
    // stand-in character (a private-use one, or for the Windows pages the matching control code). Those are bytes
    // that do not fit, so they are counted; the text is left as .NET read it.
    private static int UndefinedSingleBytes(Encoding encoding, int codePage, ReadOnlySpan<char> text)
    {
        if (!encoding.IsSingleByte || IsBuiltIn(codePage)) return 0;
        bool macRoman = codePage == 10000;                       // U+F8FF is its Apple sign, a real character
        bool windowsPage = codePage is (>= 1250 and <= 1258) or 874;
        int n = 0;
        foreach (char c in text)
        {
            if (c is >= '\uF700' and <= '\uF8FF') { if (!macRoman) n++; }
            else if (windowsPage && c is >= '\u0080' and <= '\u009F') n++;
        }
        return n;
    }

    private static Encoding Resolve(int codePage, DecoderFallback fallback)
    {
        if (!IsBuiltIn(codePage)) EnsureCodePages();
        return Encoding.GetEncoding(codePage, EncoderFallback.ReplacementFallback, fallback);
    }

    // The encodings .NET has without any provider.
    private static bool IsBuiltIn(int codePage) =>
        codePage is Utf8 or Utf16Le or Utf16Be or Utf32Le or Utf32Be or Latin1 or 20127;

    private static int _codePagesOn;

    /// <summary>True once the code-pages provider has been switched on (it never is at startup).</summary>
    public static bool CodePagesOn => Volatile.Read(ref _codePagesOn) != 0;

    private static void EnsureCodePages()
    {
        if (Interlocked.Exchange(ref _codePagesOn, 1) == 0)
            Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
    }

    /// <summary>Puts U+FFFD where bytes are not valid and counts those bytes.</summary>
    private sealed class CountingFallback : DecoderFallback
    {
        public int Bytes;
        public override int MaxCharCount => 1;
        public override DecoderFallbackBuffer CreateFallbackBuffer() => new Buffer(this);

        private sealed class Buffer(CountingFallback owner) : DecoderFallbackBuffer
        {
            private bool _pending;
            public override int Remaining => _pending ? 1 : 0;

            public override bool Fallback(byte[] bytesUnknown, int index)
            {
                owner.Bytes += bytesUnknown.Length;
                _pending = true;
                return true;
            }

            public override char GetNextChar()
            {
                if (!_pending) return '\0';
                _pending = false;
                return '�';
            }

            public override bool MovePrevious() => false;
            public override void Reset() => _pending = false;
        }
    }
}
