namespace ChuvadiReader.Android.Platform;

/// <summary>MIME types the Android host accepts, and their file extensions.</summary>
public static class DocumentTypes
{
    public const string Pdf = "application/pdf";
    public const string Docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    public const string Xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    public const string Text = "text/plain";
    public const string Markdown = "text/markdown";
    public const string MarkdownX = "text/x-markdown";
    public const string Html = "text/html";

    /// <summary>Everything the Windows "All supported" filter accepts.</summary>
    public static readonly string[] AllSupported =
    {
        Pdf, Docx, Xlsx, Markdown, MarkdownX, Text, Html,
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
        Markdown or MarkdownX => ".md",
        Html => ".html",
        Text => ".txt",
        _ => null,
    };
}
