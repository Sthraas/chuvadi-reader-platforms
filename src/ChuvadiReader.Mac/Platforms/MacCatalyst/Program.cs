using ChuvadiReader.Mac.Platform;
using UIKit;

namespace ChuvadiReader.Mac;

public static class Program
{
    private static void Main(string[] args)
    {
        StartupTimeline.Mark("main");
        UIApplication.Main(args, null, typeof(AppDelegate));
    }
}
