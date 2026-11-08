using ChuvadiReader.Core.Window;
using Foundation;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// The real macOS window behind the Ui's own title bar. The Ui draws the traffic lights on the left
/// (design handout; Foundation Group A) and calls these to minimise, zoom, close and move the window.
/// The native title bar is hidden so only the Ui's chrome shows. Mac's "maximise" is Zoom.
/// </summary>
public sealed class MacWindowControls : IWindowControls, IDisposable
{
    private readonly List<NSObject> _observers = new();
    private bool _lastZoomed;

    public event Action? StateChanged;

    public bool IsMaximized => OnMain(() => AppKitBridge.IsZoomed(AppKitBridge.AppWindow()));

    public MacWindowControls()
    {
        // Zoom state changes arrive as resizes; AppKit may also restore its title bar on these.
        foreach (var name in new[]
                 {
                     "NSWindowDidResizeNotification", "NSWindowDidEndLiveResizeNotification",
                     "NSWindowDidDeminiaturizeNotification", "NSWindowDidBecomeKeyNotification",
                     "NSWindowDidExitFullScreenNotification",
                 })
        {
            _observers.Add(NSNotificationCenter.DefaultCenter.AddObserver(new NSString(name), _ =>
            {
                ApplyChrome(); // idempotent; also catches a window that wasn't up yet at WebView ready
                RaiseIfChanged();
            }));
        }
    }

    public void Minimize() => OnMain(() => AppKitBridge.Miniaturize(AppKitBridge.AppWindow()));

    public void ToggleMaximize() => OnMain(() => AppKitBridge.Zoom(AppKitBridge.AppWindow()));

    public void Close() => OnMain(() => AppKitBridge.PerformClose(AppKitBridge.AppWindow()));

    public void BeginDrag() => OnMain(() => AppKitBridge.BeginDrag(AppKitBridge.AppWindow()));

    /// <summary>Opening size (Mac Test M-07): the Windows host's opening size, centred on the screen.</summary>
    public const double OpeningWidth = 1100;
    public const double OpeningHeight = 720;

    private bool _sized;

    /// <summary>
    /// No title text, no toolbar, no native title bar, and the page running to the window's top edge
    /// (Mac Test M-04); not restorable (M-03); 1100×720 centred on first show (M-07); 720×480 minimum.
    /// </summary>
    public void ApplyChrome() => OnMain(() =>
    {
        foreach (var scene in UIApplication.SharedApplication.ConnectedScenes)
        {
            if (scene is UIWindowScene windowScene)
            {
                if (windowScene.Titlebar is { } titlebar)
                {
                    titlebar.TitleVisibility = UITitlebarTitleVisibility.Hidden;
                    titlebar.Toolbar = null;
                }

                if (windowScene.SizeRestrictions is { } limits)
                {
                    limits.MinimumSize = new CoreGraphics.CGSize(720, 480);
                }
            }
        }

        var window = AppKitBridge.AppWindow();
        AppKitBridge.MakeContentFullHeight(window);
        AppKitBridge.HideTitlebar(window);
        AppKitBridge.SetRestorable(window, false);
        if (!_sized && window != IntPtr.Zero)
        {
            _sized = true;
            AppKitBridge.SizeAndCenter(window, OpeningWidth, OpeningHeight);
        }
    });

    private void RaiseIfChanged()
    {
        var zoomed = AppKitBridge.IsZoomed(AppKitBridge.AppWindow());
        if (zoomed != _lastZoomed)
        {
            _lastZoomed = zoomed;
            StateChanged?.Invoke();
        }
    }

    private static void OnMain(Action action)
    {
        if (NSThread.IsMain)
        {
            action();
        }
        else
        {
            UIApplication.SharedApplication.InvokeOnMainThread(action);
        }
    }

    private static T OnMain<T>(Func<T> func)
    {
        if (NSThread.IsMain)
        {
            return func();
        }

        T result = default!;
        UIApplication.SharedApplication.InvokeOnMainThread(() => result = func());
        return result;
    }

    public void Dispose()
    {
        foreach (var o in _observers)
        {
            NSNotificationCenter.DefaultCenter.RemoveObserver(o);
        }

        _observers.Clear();
    }
}
