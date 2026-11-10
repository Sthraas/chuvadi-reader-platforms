using global::Android.App;
using global::Android.Runtime;

namespace ChuvadiReader.Android;

[Application]
public sealed class MainApplication : MauiApplication
{
    public MainApplication(IntPtr handle, JniHandleOwnership ownership)
        : base(handle, ownership)
    {
        Platform.StartupTimeline.Mark("runtime");   // the first managed code (AT-14)
    }

    protected override MauiApp CreateMauiApp()
    {
        var app = MauiProgram.CreateMauiApp();
        Platform.StartupTimeline.Mark("maui");
        return app;
    }
}
