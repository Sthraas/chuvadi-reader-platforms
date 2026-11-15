using CoreGraphics;
using Foundation;
using UIKit;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Trackpad pinch zooms the page. On Mac a pinch is a UIKit gesture, and the WebView's own zoom is locked at 1 (the app
/// chrome must never scale), so the host watches the pinch and passes it to the kit's entry for hosts that keep the
/// gesture, <c>window.chuvadiPinch(phase, scale, x, y)</c> (patch 27). The scale is the gesture's own, since it began,
/// so if WebKit also sends the page its gesture events the two ask for the same zoom — nothing doubles.
/// </summary>
internal sealed class MacPinch : UIGestureRecognizerDelegate
{
    private static MacPinch? _delegate;      // the recognizer holds its delegate weakly

    public static void Attach(WKWebView view)
    {
        _delegate ??= new MacPinch();
        var pinch = new UIPinchGestureRecognizer(g =>
        {
            var at = g.LocationInView(view);
            switch (g.State)
            {
                case UIGestureRecognizerState.Began:
                    Send(view, "begin", 1, at);
                    break;
                case UIGestureRecognizerState.Changed when g.Scale > 0:
                    Send(view, "change", (double)g.Scale, at);
                    break;
                case UIGestureRecognizerState.Ended:
                case UIGestureRecognizerState.Cancelled:
                case UIGestureRecognizerState.Failed:
                    Send(view, "end", 1, at);
                    break;
            }
        })
        {
            Delegate = _delegate,
            CancelsTouchesInView = false,
        };
        view.AddGestureRecognizer(pinch);
    }

    public override bool ShouldRecognizeSimultaneously(UIGestureRecognizer gestureRecognizer, UIGestureRecognizer otherGestureRecognizer) => true;

    /// <summary>One step of the gesture to the kit's entry: phase 'begin' | 'change' | 'end', the scale since 'begin',
    /// and the pointer in the page's CSS pixels. The page zooms the view under the pointer, keeping that point still.</summary>
    public static void Send(WKWebView view, string phase, double scale, CGPoint at)
    {
        var js = FormattableString.Invariant(
            $"window.chuvadiPinch && window.chuvadiPinch('{phase}', {scale:0.####}, {at.X:0.#}, {at.Y:0.#})");
        _ = view.EvaluateJavaScriptAsync(js);
    }
}
