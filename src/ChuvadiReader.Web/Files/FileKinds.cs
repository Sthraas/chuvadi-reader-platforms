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
            // Text formats: no NUL bytes in the first kilobyte (UTF-8/ANSI text; the viewers decide the rest).
            ".txt" or ".log" or ".md" or ".markdown" or ".html" or ".htm" or ".json" => head.IndexOf((byte)0) < 0,
            _ => false,
        };
    }
}
