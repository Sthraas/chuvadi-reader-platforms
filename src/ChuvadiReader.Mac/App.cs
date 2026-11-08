using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Mac.Platform;

namespace ChuvadiReader.Mac;

/// <summary>The MAUI application: one window hosting the Blazor UI.</summary>
public sealed class App : Application
{
    private readonly IServiceProvider _services;

    public App(IServiceProvider services, IAppReadySignal ready)
    {
        _services = services;
        ready.Ready += () =>
        {
            StartupTimeline.Mark("first-render");
            StartupTimeline.Flush();

            // The Ui has now registered its commands: make sure the menu bar is built from them (M-01).
            UIKit.UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
            {
                MacMenuBar.RequestRebuild("ui-ready");
                MacSmoke.Start(_services, MainPage.WebKitView);
            });

            // CI smoke run: launch, reach the first Blazor render, report, quit.
            if (Environment.GetEnvironmentVariable("CHUVADI_SMOKE_EXIT") == "1")
            {
                Console.WriteLine("CHUVADI_SMOKE_OK");
                Environment.Exit(0);
            }
        };
    }

    protected override Window CreateWindow(IActivationState? activationState)
    {
        StartupTimeline.Mark("window");
        var window = new Window(new MainPage(_services))
        {
            Title = "Chuvadi",
            // Same opening size as the Windows host before it maximises.
            Width = 1100,
            Height = 720,
            MinimumWidth = 720,
            MinimumHeight = 480,
        };
        return window;
    }
}
