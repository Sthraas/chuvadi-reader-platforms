using System.Runtime.InteropServices;

namespace ParseProcessPrototype;

/// <summary>The stack size of the calling thread, from the operating system (the advisory's question: on what stack
/// do Word files load). Linux: pthread_getattr_np; macOS: pthread_get_stacksize_np; Windows: GetCurrentThreadStackLimits.</summary>
public static unsafe class Stacks
{
    public static string Describe()
    {
        string main = "main " + Kb(Current());
        long pool = Task.Run(Current).GetAwaiter().GetResult();
        long created = 0;
        var t = new Thread(() => created = Current());
        t.Start(); t.Join();
        return $"{main}, thread pool {Kb(pool)}, new Thread() {Kb(created)}";
    }

    private static string Kb(long b) => b <= 0 ? "unknown" : $"{b / 1024} KB";

    public static long Current()
    {
        try
        {
            if (OperatingSystem.IsWindows())
            {
                GetCurrentThreadStackLimits(out var low, out var high);
                return (long)(high - low);
            }
            if (OperatingSystem.IsMacOS() || OperatingSystem.IsMacCatalyst())
                return (long)pthread_get_stacksize_np(pthread_self());
            if (OperatingSystem.IsLinux() || OperatingSystem.IsAndroid())
            {
                var attr = stackalloc byte[128];
                if (pthread_getattr_np(pthread_self(), attr) != 0) return -1;
                nint addr; nuint size;
                pthread_attr_getstack(attr, &addr, &size);
                pthread_attr_destroy(attr);
                return (long)size;
            }
        }
        catch (Exception) { }
        return -1;
    }

    [DllImport("kernel32")] private static extern void GetCurrentThreadStackLimits(out nuint low, out nuint high);
    [DllImport("libc")] private static extern nint pthread_self();
    [DllImport("libc")] private static extern nuint pthread_get_stacksize_np(nint thread);
    [DllImport("libc")] private static extern int pthread_getattr_np(nint thread, byte* attr);
    [DllImport("libc")] private static extern int pthread_attr_getstack(byte* attr, nint* addr, nuint* size);
    [DllImport("libc")] private static extern int pthread_attr_destroy(byte* attr);
}
