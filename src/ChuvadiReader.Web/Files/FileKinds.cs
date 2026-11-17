namespace ChuvadiReader.Web.Files;

/// <summary>What a pick accepts. Each kind has the extensions the browser's chooser offers and a
/// check of the file's first bytes, so a renamed file of another type is refused on the server.</summary>
public enum PickKind
{
    /// <summary>The Reader's open dialog: the same formats as the desktop open dialog.</summary>
    Document,

    /// <summary>PDFs only (Merge, Bench).</summary>
    Pdf,

    /// <summary>Images to place on a page.</summary>
    Image,

    /// <summary>A saved Bench session (JSON).</summary>
    Session,

    /// <summary>A signing certificate with its private key.</summary>
    Certificate,
}

public static class FileKinds
{
    private static readonly string[] DocumentExt = [".pdf", ".docx", ".xlsx", ".md", ".markdown", ".txt", ".log", ".html", ".htm"];
    private static readonly string[] PdfExt = [".pdf"];
    private static readonly string[] ImageExt = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"];
    private static readonly string[] SessionExt = [".json"];
    private static readonly string[] CertificateExt = [".pfx", ".p12"];

    public static IReadOnlyList<string> Extensions(PickKind kind) => kind switch
    {
        PickKind.Document => DocumentExt,
        PickKind.Pdf => PdfExt,
        PickKind.Image => ImageExt,
        PickKind.Session => SessionExt,
        PickKind.Certificate => CertificateExt,
        _ => throw new ArgumentOutOfRangeException(nameof(kind)),
    };

    /// <summary>The <c>accept</c> attribute for the browser's file chooser.</summary>
    public static string Accept(PickKind kind) => string.Join(',', Extensions(kind));

    public static bool HasAllowedExtension(PickKind kind, string fileName)
        => Extensions(kind).Contains(Path.GetExtension(fileName).ToLowerInvariant(), StringComparer.Ordinal);

    /// <summary>Checks the file's first bytes against its extension. <paramref name="head"/> is the
    /// start of the file (up to 1024 bytes; fewer for a smaller file).</summary>
    public static bool ContentMatches(string fileName, ReadOnlySpan<byte> head)
    {
        var ext = Path.GetExtension(fileName).ToLowerInvariant();
        return ext switch
        {
            // PDF readers accept the header anywhere in the first 1024 bytes.
            ".pdf" => head.IndexOf("%PDF-"u8) >= 0,
            // OOXML packages are ZIP files.
            ".docx" or ".xlsx" => head.StartsWith("PK\u0003\u0004"u8),
            ".png" => head.StartsWith(new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A }),
            ".jpg" or ".jpeg" => head.StartsWith(new byte[] { 0xFF, 0xD8, 0xFF }),
            ".gif" => head.StartsWith("GIF87a"u8) || head.StartsWith("GIF89a"u8),
            ".bmp" => head.StartsWith("BM"u8),
            ".tif" or ".tiff" => head.StartsWith("II*\0"u8) || head.StartsWith("MM\0*"u8),
            ".webp" => head.Length >= 12 && head.StartsWith("RIFF"u8) && head[8..12].SequenceEqual("WEBP"u8),
            // DER SEQUENCE.
            ".pfx" or ".p12" => head.Length > 0 && head[0] == 0x30,
            // A saved session is UTF-8 JSON: no NUL bytes in the first kilobyte.
            ".json" => head.IndexOf((byte)0) < 0,
            // Text the viewers read (D-191 lets the person choose the encoding): UTF-8 or a one-byte encoding
            // has no NUL bytes in the first kilobyte; UTF-16 is full of them, so it is taken only when it
            // says what it is with a byte-order mark and its first kilobyte is text (WT-26, D-197).
            _ when IsViewedAsText(ext) => head.IndexOf((byte)0) < 0 || IsUtf16TextWithMark(head),
            _ => false,
        };
    }

    /// <summary>The text types the viewers open, where the person can choose the encoding (D-191).</summary>
    public static bool IsViewedAsText(string extension)
        => extension is ".txt" or ".log" or ".md" or ".markdown" or ".html" or ".htm";

    /// <summary>
    /// UTF-16 text that starts with its byte-order mark (FF FE little-endian, FE FF big-endian), judged on the
    /// start of the file: after the mark, whole 16-bit units, none of them U+0000, and surrogates only in
    /// proper pairs. That keeps the rule's purpose (a binary file must not come in under a text name): a
    /// binary that happens to start with those two bytes fails on its zero units or broken pairs, and
    /// FF FE 00 00 (the UTF-32 mark, which the viewers don't offer) fails on its first unit. UTF-16 without
    /// a mark stays refused: without the mark it cannot be told from a binary by rule, only by guessing.
    /// </summary>
    public static bool IsUtf16TextWithMark(ReadOnlySpan<byte> head)
    {
        bool little;
        if (head.StartsWith(new byte[] { 0xFF, 0xFE }))
        {
            little = true;
        }
        else if (head.StartsWith(new byte[] { 0xFE, 0xFF }))
        {
            little = false;
        }
        else
        {
            return false;
        }

        var units = head[2..];
        units = units[..(units.Length & ~1)]; // the kilobyte may end in the middle of a unit
        var expectLow = false;
        for (var i = 0; i < units.Length; i += 2)
        {
            var u = little ? units[i] | (units[i + 1] << 8) : (units[i] << 8) | units[i + 1];
            if (u == 0)
            {
                return false;
            }

            var isHigh = u is >= 0xD800 and <= 0xDBFF;
            var isLow = u is >= 0xDC00 and <= 0xDFFF;
            if (expectLow != isLow)
            {
                return false; // a low surrogate without its high one, or a high one not followed by a low one
            }

            expectLow = isHigh;
        }

        return true; // (a pair cut by the end of the kilobyte is fine: the rest of the file is the viewer's to read)
    }

    /// <summary>What the person is told when the content check refuses a file.</summary>
    public static string Refusal(string fileName, ReadOnlySpan<byte> head)
    {
        var ext = Path.GetExtension(fileName).ToLowerInvariant();
        if (IsViewedAsText(ext) && head.IndexOf((byte)0) >= 0)
        {
            // Not "isn't a valid TXT file": it may well be text (UTF-16 as some programs save it, without the mark).
            return $"{fileName} can't be opened here. It is either not text, or UTF-16 text saved without a byte-order mark. "
                + "Save it as UTF-8, or as UTF-16 with a byte-order mark, and upload it again.";
        }

        return $"{fileName} isn't a valid {ext.TrimStart('.').ToUpperInvariant()} file.";
    }
}
