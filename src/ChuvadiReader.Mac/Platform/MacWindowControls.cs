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

    public bool IsMaximized => OnMain(() => AppKitBridge.IsZoomed(AppKitBridge.KeyWindow()));

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
                AppKitBridge.HideTitlebar(AppKitBridge.KeyWindow());
                RaiseIfChanged();
            }));
        }
    }

    public void Minimize() => OnMain(() => AppKitBridge.Miniaturize(AppKitBridge.KeyWindow()));

    public void ToggleMaximize() => OnMain(() => AppKitBridge.Zoom(AppKitBridge.KeyWindow()));

    public void Close() => OnMain(() => AppKitBridge.PerformClose(AppKitBridge.KeyWindow()));

    public void BeginDrag() => OnMain(() => AppKitBridge.BeginDrag(AppKitBridge.KeyWindow()));

    /// <summary>No title text, no toolbar, no native title bar: the page runs to the window's top edge.</summary>
    public void ApplyChrome() => OnMain(() =>
    {
        foreach (var scene in UIApplication.SharedApplication.ConnectedScenes)
        {
            if (scene is UIWindowScene { Titlebar: { } titlebar })
            {
                titlebar.TitleVisibility = UITitlebarTitleVisibility.Hidden;
                titlebar.Toolbar = null;
            }
        }

        AppKitBridge.HideTitlebar(AppKitBridge.KeyWindow());
    });

    private void RaiseIfChanged()
    {
        var zoomed = AppKitBridge.IsZoomed(AppKitBridge.KeyWindow());
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
