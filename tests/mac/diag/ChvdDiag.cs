// Mac Test — TESTING ONLY. Copied into a throw-away diagnostic build on the runner (never committed to the app,
// never shipped): prints every thrown .NET exception with its stack to stderr, because the Release app has no
// logging provider and Blazor's "An error occurred" bar shows no detail.
#pragma warning disable CA2255
using System.Runtime.CompilerServices;

namespace ChuvadiReader.Mac;

internal static class ChvdDiag
{
    [ModuleInitializer]
    internal static void Init()
    {
        AppDomain.CurrentDomain.FirstChanceException += (_, e) =>
        {
            try
            {
                Console.Error.WriteLine($"CHVD_FIRST_CHANCE {e.Exception.GetType().FullName}: {e.Exception.Message}{Environment.NewLine}{e.Exception.StackTrace}{Environment.NewLine}CHVD_END");
            }
            catch
            {
            }
        };
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
        {
            try { Console.Error.WriteLine($"CHVD_UNHANDLED {e.ExceptionObject}"); } catch { }
        };
    }
}
