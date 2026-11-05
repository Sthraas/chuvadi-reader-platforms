using ChuvadiReader.Core.Window;
using Foundation;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Drives the real macOS window from the HTML title bar (move, minimise, zoom, close) and
/// reports zoomed state so the title bar shows the right icon. Mac's "maximise" is Zoom.
/// </summary>
public sealed class MacWindowControls : IWindowControls, IDisposable
{
    private readonly List<NSObject> _observers = new();
    private bool _lastZoomed;

    public event Action? StateChanged;

    public bool IsMaximized => OnMain(() => AppKitBridge.IsZoomed(AppKitBridge.KeyWindow()));

    public MacWindowControls()
    {
        // AppKit posts these through the shared notification centre that Catalyst also uses.
        foreach (var name in new[] { "NSWindowDidResizeNotification", "NSWindowDidEndLiveResizeNotification", "NSWindowDidDeminiaturizeNotification" })
        {
            _observers.Add(NSNotificationCenter.DefaultCenter.AddObserver(new NSString(name), _ => RaiseIfChanged()));
        }
    }

    public void Minimize() => OnMain(() => AppKitBridge.Miniaturize(AppKitBridge.KeyWindow()));

    public void ToggleMaximize() => OnMain(() => AppKitBridge.Zoom(AppKitBridge.KeyWindow()));

    public void Close() => OnMain(() => AppKitBridge.PerformClose(AppKitBridge.KeyWindow()));

    public void BeginDrag() => OnMain(() => AppKitBridge.BeginDrag(AppKitBridge.KeyWindow()));

    /// <summary>Hides the native traffic lights while the HTML title bar carries the window
    /// buttons (MacChrome.UseHtmlWindowButtons).</summary>
    public void ApplyChrome() => OnMain(() =>
        AppKitBridge.SetStandardButtonsHidden(AppKitBridge.KeyWindow(), MacChrome.UseHtmlWindowButtons));

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

/// <summary>Mac window-chrome choice, pending Arun's decision (docs/mac/README.md).
/// true  = design untouched: HTML window dots (top right) drive the window; native buttons hidden.
/// false = native traffic lights top-left; needs a host stylesheet that hides the HTML dots and
///         insets the top bar (not built until Arun approves).</summary>
internal static class MacChrome
{
    public const bool UseHtmlWindowButtons = true;
}
