using System.IO.Compression;
using ChuvadiReader.Core.Documents;
using Xunit;

namespace ChuvadiReader.Tests;

/// <summary>B-08: a Word / Excel package whose parts unpack to an unreasonable size is refused before the
/// document library inflates it.</summary>
public class OfficePackageGuardTests
{
    private static string Package(long partBytes)
    {
        var path = Path.Combine(Path.GetTempPath(), $"guard-{Guid.NewGuid():N}.docx");
        using (var zip = ZipFile.Open(path, ZipArchiveMode.Create))
        {
            zip.CreateEntry("[Content_Types].xml").Open().Dispose();
            using var part = zip.CreateEntry("word/document.xml", CompressionLevel.SmallestSize).Open();
            var zeros = new byte[1 << 20];
            for (long written = 0; written < partBytes; written += zeros.Length)
            {
                part.Write(zeros, 0, (int)Math.Min(zeros.Length, partBytes - written));
            }
        }

        return path;
    }

    [Fact]
    public void A_zip_bomb_is_refused_before_it_is_unpacked()
    {
        var path = Package(300L * 1024 * 1024);
        Assert.True(new FileInfo(path).Length < 2 * 1024 * 1024, "the bomb itself is small");

        var ex = Assert.Throws<DocumentViewException>(() => OfficePackageGuard.Check(path, "Word document"));
        Assert.Equal(ViewErrorReason.TooLarge, ex.Reason);
        Assert.Contains("too large to open", ex.Message);
    }

    [Fact]
    public void A_normal_package_passes()
    {
        var path = Package(64 * 1024);
        OfficePackageGuard.Check(path, "Word document");
    }

    [Fact]
    public void A_file_that_is_not_a_zip_is_left_to_the_library()
    {
        var path = Path.Combine(Path.GetTempPath(), $"guard-{Guid.NewGuid():N}.docx");
        File.WriteAllBytes(path, [0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]); // an encrypted Office file's header
        OfficePackageGuard.Check(path, "Word document");
    }
}
