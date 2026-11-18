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
#if CHUVADI_ENGINE_PROBE
        Platform.EngineProbe.Probe.RuntimeAt = Platform.EngineProbe.Probe.Now;
#endif
    }

#if CHUVADI_ENGINE_PROBE
    // D-202 probe (test build only): the engine process sets up a bare MAUI app, not the Reader's.
    public override void OnCreate()
    {
        base.OnCreate();
        Platform.EngineProbe.Probe.AppCreatedAt = Platform.EngineProbe.Probe.Now;
    }
#endif

    protected override MauiApp CreateMauiApp()
    {
#if CHUVADI_ENGINE_PROBE
        if (Platform.EngineProbe.Probe.InEngineProcess)
        {
            var bare = MauiApp.CreateBuilder();
            bare.UseMauiApp<Platform.EngineProbe.EngineApp>();
            return bare.Build();
        }
#endif
        var app = MauiProgram.CreateMauiApp();
        Platform.StartupTimeline.Mark("maui");
        return app;
    }
}
