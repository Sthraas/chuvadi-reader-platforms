using CoreGraphics;
using Foundation;
using UIKit;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Trackpad pinch zooms the page (coordinator, 11 Nov: it did nothing on Linux; Mac checked). The Ui zooms on
/// wheel + Ctrl, which is how Chromium (WebView2) reports a trackpad pinch. WebKit does not: on Mac a pinch is a UIKit
/// pinch gesture, and the WebView's own zoom is locked at 1 (the app chrome must never scale). So the host watches the
/// pinch and hands each step to the page as the wheel + Ctrl event it expects, at the pointer — the page then zooms
/// around the pointer exactly as on Windows. Only the page canvas zooms; nothing else changes.
/// </summary>
internal sealed class MacPinch : UIGestureRecognizerDelegate
{
    private static MacPinch? _delegate;      // the recognizer holds its delegate weakly
    private static nfloat _last = 1;

    public static void Attach(WKWebView view)
    {
        _delegate ??= new MacPinch();
        var pinch = new UIPinchGestureRecognizer(g =>
        {
            if (g.State == UIGestureRecognizerState.Began)
            {
                _last = 1;
            }
            else if (g.State == UIGestureRecognizerState.Changed && g.Scale > 0 && _last > 0)
            {
                var ratio = g.Scale / _last;
                _last = g.Scale;
                Forward(view, (double)ratio, g.LocationInView(view));
            }
        })
        {
            Delegate = _delegate,
            CancelsTouchesInView = false,
        };
        view.AddGestureRecognizer(pinch);
    }

    public override bool ShouldRecognizeSimultaneously(UIGestureRecognizer gestureRecognizer, UIGestureRecognizer otherGestureRecognizer) => true;

    /// <summary>One pinch step as the page's wheel + Ctrl zoom: the page multiplies its zoom by exp(-deltaY × 0.0015).</summary>
    public static void Forward(WKWebView view, double ratio, CGPoint at)
    {
        if (ratio <= 0 || Math.Abs(ratio - 1) < 0.0005)
        {
            return;
        }

        var deltaY = -Math.Log(ratio) / 0.0015;
        var js = FormattableString.Invariant(
            $"(function(){{var x={at.X:0.#},y={at.Y:0.#};var el=document.elementFromPoint(x,y)||document.body;el.dispatchEvent(new WheelEvent('wheel',{{deltaY:{deltaY:0.###},ctrlKey:true,clientX:x,clientY:y,bubbles:true,cancelable:true}}));}})()");
        _ = view.EvaluateJavaScriptAsync(js);
    }
}
