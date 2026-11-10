using System.Runtime.InteropServices;
using ChuvadiReader.Linux.Platform;
using Xunit;

namespace ChuvadiReader.Linux.Tests;

/// <summary>After a memory relief, freed native memory goes back to the system (nineteenth patch; glibc only).</summary>
public sealed class GlibcTrimTests
{
    private static long ResidentKb() =>
        long.Parse(File.ReadLines("/proc/self/status").First(l => l.StartsWith("VmRSS:", StringComparison.Ordinal))
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)[1]);

    [Fact]
    public void Freed_native_memory_goes_back_to_the_system()
    {
        // Many small blocks (below glibc's mmap threshold) stay with the C library when freed, as WebKitGTK's do.
        var blocks = new IntPtr[64 * 1024];
        for (var i = 0; i < blocks.Length; i++)
        {
            blocks[i] = Marshal.AllocHGlobal(1000);
            unsafe { new Span<byte>((void*)blocks[i], 1000).Fill(1); } // touched, so it is resident
        }

        // One block still in use above them, as in a long-running app: glibc can't give the freed ones back by
        // shrinking the top of its heap on its own, so only malloc_trim returns them.
        var pin = Marshal.AllocHGlobal(1000);
        try
        {
            foreach (var b in blocks)
            {
                Marshal.FreeHGlobal(b);
            }

            var before = ResidentKb();
            Assert.True(GlibcTrim.Trim(), "glibc had freed memory to give back");
            var after = ResidentKb();
            Assert.True(before - after > 32 * 1024, $"resident {before / 1024} MB → {after / 1024} MB: under 32 MB given back");
        }
        finally
        {
            Marshal.FreeHGlobal(pin);
        }
    }

    [Fact]
    public void Hooking_twice_is_harmless_and_trimming_again_does_not_throw()
    {
        GlibcTrim.Hook();
        GlibcTrim.Trim();
        GlibcTrim.Trim();
    }
}
