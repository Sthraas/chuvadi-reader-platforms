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

        // AppKit lays the window buttons out again on these; put them back in the top bar.
        foreach (var name in new[]
                 {
                     "NSWindowDidResizeNotification", "NSWindowDidBecomeKeyNotification",
                     "NSWindowDidExitFullScreenNotification", "NSWindowDidChangeBackingPropertiesNotification",
                 })
        {
            _observers.Add(NSNotificationCenter.DefaultCenter.AddObserver(new NSString(name), _ => PlaceButtons()));
        }
    }

    public void Minimize() => OnMain(() => AppKitBridge.Miniaturize(AppKitBridge.KeyWindow()));

    public void ToggleMaximize() => OnMain(() => AppKitBridge.Zoom(AppKitBridge.KeyWindow()));

    public void Close() => OnMain(() => AppKitBridge.PerformClose(AppKitBridge.KeyWindow()));

    public void BeginDrag() => OnMain(() => AppKitBridge.BeginDrag(AppKitBridge.KeyWindow()));

    /// <summary>Mac chrome per the handout: no native title text or toolbar, the page runs to the
    /// top edge, and the native traffic lights sit at the left of the Ui's own top bar. The Ui's
    /// right-hand window dots are hidden by the host stylesheet (wwwroot/css/mac.css).</summary>
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

        PlaceButtons();
    });

    /// <summary>Re-centres the traffic lights when the interface size changes.</summary>
    public void SetScale(double factor)
    {
        _scale = factor;
        OnMain(PlaceButtons);
    }

    private double _scale = 1.0;

    private void PlaceButtons()
        => AppKitBridge.PositionStandardButtons(AppKitBridge.KeyWindow(),
            MacChrome.ButtonsLeft, MacChrome.ButtonPitch, MacChrome.TopBarHeight * _scale);

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

/// <summary>Geometry of the native traffic lights inside the Ui's top bar. Must agree with
/// wwwroot/css/mac.css (padding-left of the top bar = ButtonsLeft + 2 × ButtonPitch + button
/// width 14 + the bar's 12 px gap = 80 px).</summary>
internal static class MacChrome
{
    /// <summary>The Ui's top bar height (shell.css --sh-top) at 100 %.</summary>
    public const double TopBarHeight = 40;

    /// <summary>Left edge of the close button (handout: title bar padding 14 px).</summary>
    public const double ButtonsLeft = 14;

    /// <summary>Distance from one button to the next (12 px dot + ~8 px gap, macOS standard).</summary>
    public const double ButtonPitch = 20;
}
