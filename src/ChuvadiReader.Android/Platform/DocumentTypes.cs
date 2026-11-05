namespace ChuvadiReader.Android.Platform;

/// <summary>MIME types the Android host accepts, and their file extensions.</summary>
public static class DocumentTypes
{
    public const string Pdf = "application/pdf";
    public const string Docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    public const string Xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    /// <summary>Everything the Windows "All supported" filter accepts.</summary>
    public static readonly string[] AllSupported =
    {
        Pdf, Docx, Xlsx, "text/markdown", "text/x-markdown", "text/plain", "text/html",
    };

    public static readonly string[] PdfOnly = { Pdf };

    public static readonly string[] Images = { "image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp", "image/tiff" };

    public static readonly string[] Certificates = { "application/x-pkcs12", "application/x-pkcs12-certificate" };

    /// <summary>Extensions the open path accepts (same list as the Windows picker).</summary>
    public static readonly string[] Extensions =
    {
        ".pdf", ".docx", ".xlsx", ".md", ".markdown", ".txt", ".log", ".html", ".htm",
    };

    /// <summary>Best extension for a MIME type, used when a provider gives a name without one.</summary>
    public static string? ExtensionFor(string? mime) => mime switch
    {
        Pdf => ".pdf",
        Docx => ".docx",
        Xlsx => ".xlsx",
        "text/markdown" or "text/x-markdown" => ".md",
        "text/html" => ".html",
        "text/plain" => ".txt",
        _ => null,
    };
}
