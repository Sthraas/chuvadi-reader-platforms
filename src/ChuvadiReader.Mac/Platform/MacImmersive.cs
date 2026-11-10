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
        MacPageKeys.Send("Escape", "Escape", ctrl: false, shift: false, meta: false);
    }
}

/// <summary>
/// Mac Test M-08 / M-23: keys that only the page handles — next/previous tab (⌃Tab, ⌃⇧Tab) and go to tab n (⌘1…⌘9).
/// On Mac they did not arrive: the WebView often lacks the keyboard (after a panel, after files arrive) and UIKit
/// uses ⌃Tab for its own focus moves. They are Window menu items (MacMenuBar) — a menu key equivalent works whatever
/// has the keyboard — that hand the key to the page's focused element, where reader.js decides exactly as on Windows
/// (it ignores them while typing in a field). The WebView also gets the keyboard back after panels, when files
/// arrive, at first render and whenever the window becomes key (<see cref="Refocus"/>).
/// </summary>
internal static class MacPageKeys
{
    public const string Selector = "chvdPageKey:";

    /// <summary>⌃Tab and ⌃⇧Tab as key commands with priority over UIKit's own focus moves.</summary>
    public static IEnumerable<UIKeyCommand> TabCommands()
    {
        foreach (var flags in new[] { UIKeyModifierFlags.Control, UIKeyModifierFlags.Control | UIKeyModifierFlags.Shift })
        {
            var c = UIKeyCommand.Create(new NSString("\t"), flags, new ObjCRuntime.Selector(Selector));
            c.WantsPriorityOverSystemBehavior = true;
            yield return c;
        }
    }

    public static bool Available => ChuvadiReader.Mac.MainPage.WebKitView is not null;

    public static void Handle(UIKeyCommand command)
    {
        var input = command.Input ?? string.Empty;
        var flags = command.ModifierFlags;
        if (input == "\t")
        {
            Send("Tab", "Tab", ctrl: true, shift: flags.HasFlag(UIKeyModifierFlags.Shift), meta: false);
        }
        else if (input.Length == 1 && char.IsDigit(input[0]))
        {
            Send(input, "Digit" + input, ctrl: false, shift: false, meta: true);
        }
    }

    /// <summary>A keydown on the page's focused element (bubbling to the document, where reader.js listens).</summary>
    public static void Send(string key, string code, bool ctrl, bool shift, bool meta)
    {
        MacSmoke.Log($"page-key {(ctrl ? "⌃" : "")}{(shift ? "⇧" : "")}{(meta ? "⌘" : "")}{key}");
        var b = (bool v) => v ? "true" : "false";
        _ = ChuvadiReader.Mac.MainPage.WebKitView?.EvaluateJavaScriptAsync(
            $"(document.activeElement || document.body || document).dispatchEvent(new KeyboardEvent('keydown', {{ key: '{key}', code: '{code}', ctrlKey: {b(ctrl)}, shiftKey: {b(shift)}, metaKey: {b(meta)}, bubbles: true, cancelable: true }}))");
    }

    /// <summary>Gives the WebView the keyboard (after a panel closes, when the window becomes key).</summary>
    public static void Refocus()
    {
        if (ChuvadiReader.Mac.MainPage.WebKitView is { } view && !view.IsFirstResponder)
        {
            var ok = view.BecomeFirstResponder();
            MacSmoke.Log("webview-focus " + ok);
        }
    }

    private static NSObject? _keyWatch;

    public static void WatchWindow()
    {
        _keyWatch ??= NSNotificationCenter.DefaultCenter.AddObserver(UIWindow.DidBecomeKeyNotification,
            _ => UIApplication.SharedApplication.BeginInvokeOnMainThread(Refocus));
    }
}
