using System.IO.Compression;

namespace ChuvadiReader.Core.Documents;

/// <summary>
/// B-08: refuses a Word / Excel package whose parts unpack to an unreasonable size (a "zip bomb") before the
/// document library inflates anything. Reads only the zip directory (declared sizes): cheap, and it stops
/// honest-header bombs; a package that lies about its sizes needs the library's own input limits (library
/// ask). Not a zip (an encrypted Office file is a different container): left to the library.
/// </summary>
public static class OfficePackageGuard
{
    /// <summary>Largest single part, unpacked.</summary>
    public const long MaxPartBytes = 256L * 1024 * 1024;

    /// <summary>All parts together, unpacked.</summary>
    public const long MaxTotalBytes = 1024L * 1024 * 1024;

    /// <summary>Compression ratio beyond which a large part (over <see cref="RatioFloorBytes"/>) is refused.</summary>
    public const long MaxRatio = 200;

    public const long RatioFloorBytes = 16L * 1024 * 1024;

    /// <param name="kind">"Word document" or "Excel workbook", for the message.</param>
    public static void Check(string path, string kind)
    {
        ZipArchive zip;
        try
        {
            zip = ZipFile.OpenRead(path);
        }
        catch (InvalidDataException)
        {
            return;
        }

        using (zip)
        {
            long total = 0;
            foreach (var e in zip.Entries)
            {
                total += e.Length;
                var bomb = e.Length > MaxPartBytes
                           || total > MaxTotalBytes
                           || (e.Length > RatioFloorBytes && e.CompressedLength > 0 && e.Length / e.CompressedLength > MaxRatio);
                if (bomb)
                {
                    throw new DocumentViewException(ViewErrorReason.TooLarge,
                        $"This {kind} is too large to open: its contents unpack to more than {Math.Max(total, e.Length) / (1024 * 1024):N0} MB. It may be damaged.");
                }
            }
        }
    }
}
