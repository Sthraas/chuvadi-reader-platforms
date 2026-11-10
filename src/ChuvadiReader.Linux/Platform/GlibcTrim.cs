using System.Runtime.InteropServices;
using ChuvadiReader.Core.Reader;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Gives freed native memory back to the system after a memory relief pass (nineteenth patch, 36c). WebKitGTK and
/// GLib run inside the app's process, and the C library keeps the memory they freed (about 150 MB after a big
/// drawing) until <c>malloc_trim(0)</c>. glibc only: it is the C library itself, nothing external; on another C
/// library the call isn't there, and this turns itself off.
/// </summary>
public static class GlibcTrim
{
    private static int _unavailable;
    private static int _relieved;

    /// <summary>How many relief passes have notified the host so far (for the UI tests).</summary>
    public static int Relieved => Volatile.Read(ref _relieved);

    /// <summary>Hooks the trim to <see cref="MemoryReliefNotice.Relieved"/> (once, at start).</summary>
    public static void Hook() => MemoryReliefNotice.Relieved += () =>
    {
        Interlocked.Increment(ref _relieved);
        Trim();
    };

    /// <summary>Returns true when glibc gave memory back to the system, false when it had none or isn't glibc.</summary>
    public static bool Trim()
    {
        if (Volatile.Read(ref _unavailable) != 0)
        {
            return false;
        }

        try
        {
            return malloc_trim(0) != 0;
        }
        catch (Exception ex) when (ex is DllNotFoundException or EntryPointNotFoundException)
        {
            Volatile.Write(ref _unavailable, 1); // not glibc (musl, for one): nothing to trim this way
            return false;
        }
    }

    [DllImport("libc.so.6", EntryPoint = "malloc_trim", ExactSpelling = true)]
    private static extern int malloc_trim(nuint pad);
}
