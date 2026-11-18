using ChuvadiReader.Mac.Platform;
using UIKit;

namespace ChuvadiReader.Mac;

public static class Program
{
    private static void Main(string[] args)
    {
        // D-198 proof (smoke only): the app's own program started again as a child; never starts UIKit.
        if (args.Length > 0 && args[0] == EngineProbe.Switch)
        {
            Environment.Exit(EngineProbe.RunChild(args));
        }

        StartupTimeline.Mark("main");
        UIApplication.Main(args, null, typeof(AppDelegate));
    }
}
