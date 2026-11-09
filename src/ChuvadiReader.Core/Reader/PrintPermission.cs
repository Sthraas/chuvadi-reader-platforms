using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Primitives;

namespace ChuvadiReader.Core.Reader;

/// <summary>
/// A PDF's own "no printing" permission (PDF 32000-1 §7.6.3.2, /P bit 3). Every platform respects
/// it: the Print card is locked with <see cref="Refused"/> as the reason, and host print services
/// refuse the job as well. The permissions restrict whoever opens the file with the user password (or
/// none); the owner password lifts them (D-139, chuvadi-pdf 3.32.0 <c>EncryptionInfo.EffectiveFlags</c>,
/// which ends the D-102 refusal for owner-password opens).
/// </summary>
public static class PrintPermission
{
    public const string Refused = "This file's permissions don't allow printing.";

    /// <summary>False when the file is encrypted, its permissions forbid printing, and it wasn't opened with the
    /// owner password. The library decides what the opener may do (<c>EffectiveFlags</c>: everything for the
    /// owner password, otherwise the file's own flags).</summary>
    public static bool Allows(PdfDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);
        return document.Encryption is not { } encryption || encryption.EffectiveFlags.HasFlag(PdfPermissions.Print);
    }
}
