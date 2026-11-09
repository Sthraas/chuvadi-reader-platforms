using Foundation;
using UIKit;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-21: Esc leaves Immersive. The Ui leaves Immersive on Esc (reader.js → Reader.OnEscape), but on Mac the
/// key only reaches the page while the WebView has the keyboard — after the Open panel closes, it often does not, so
/// ⌃⌘F (a menu shortcut) entered Immersive and Esc went nowhere. The host page reports Immersive (the
/// body's chvd-immersive class) here; while it is on, an Esc key command at the app level hands Esc to the page.
/// While it is off the command is not available and Esc goes wherever it always went.
/// </summary>
internal sealed class MacImmersive : NSObject, IWKScriptMessageHandler
{
    public const string Name = "chvdState";
    public const string EscapeSelector = "chvdEscape:";

    public static bool IsOn { get; private set; }

    public static void Attach(WKWebView view)
    {
        IsOn = false;
        view.Configuration.UserContentController.AddScriptMessageHandler(new MacImmersive(), Name);
    }

    [Export("userContentController:didReceiveScriptMessage:")]
    public void DidReceiveScriptMessage(WKUserContentController userContentController, WKScriptMessage message)
    {
        var on = message.Body?.ToString() == "immersive:1";
        if (on != IsOn)
        {
            IsOn = on;
            MacSmoke.Log("immersive " + (on ? "on" : "off"));
        }
    }

    /// <summary>The Esc key command (AppDelegate.KeyCommands); performed only while Immersive is on.</summary>
    public static UIKeyCommand EscapeCommand()
    {
        var command = UIKeyCommand.Create(UIKeyCommand.Escape, 0, new ObjCRuntime.Selector(EscapeSelector));
        command.WantsPriorityOverSystemBehavior = true;
        return command;
    }

    /// <summary>Hands Esc to the page as the key it would have had (reader.js listens on the document).</summary>
    public static void SendEscapeToPage()
    {
        MacSmoke.Log("immersive escape → page");
        _ = ChuvadiReader.Mac.MainPage.WebKitView?.EvaluateJavaScriptAsync(
            "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true, cancelable: true }))");
    }
}
