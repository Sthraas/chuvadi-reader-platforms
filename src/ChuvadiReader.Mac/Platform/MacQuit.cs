using System.Runtime.InteropServices;
using Foundation;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-03 — a clean quit on macOS 26. During termination MAUI tears the page down, then AppKit's
/// saved-window-state flush (NSPersistentUIManager) commits one more frame, which sends a trait change to
/// MAUI's PageViewController; its handler reaches services that are gone and throws, and a managed
/// exception crossing into native code aborts the process ("quit unexpectedly").
/// Three layers: windows are not restorable (MacWindowControls), the page's view controllers are detached
/// as termination starts so no late callback reaches them, and — only once quitting has begun — any
/// managed exception that still reaches native code ends the process with exit code 0 instead of an abort.
/// Nothing is pending by then: settings are written atomically on every change and tabs persist as they change.
/// </summary>
internal static class MacQuit
{
    private static bool _quitting;

    [DllImport("/usr/lib/libSystem.dylib", EntryPoint = "_exit")]
    private static extern void ExitImmediately(int status);

    public static void Install()
    {
        Runtime.MarshalManagedException += (_, e) =>
        {
            if (!_quitting)
            {
                return;
            }

            Console.Error.WriteLine("Chuvadi: exception during quit, exiting cleanly: " + e.Exception.GetType().Name + ": " + e.Exception.Message);
            MacSmoke.Log("quit-exception " + e.Exception.GetType().Name);
            Console.Out.Flush();
            Console.Error.Flush();
            ExitImmediately(0);
        };

        // A scene that goes away (its window closed, or quitting) has its page detached first, so no late
        // trait change reaches it. This does not mark the app as quitting: it may keep running and reopen.
        NSNotificationCenter.DefaultCenter.AddObserver(UIScene.DidDisconnectNotification, n =>
        {
            if (n.Object is UIWindowScene scene)
            {
                Detach(scene);
            }
        });
    }

    /// <summary>Termination has started: detach every window's page so nothing reaches it any more.</summary>
    public static void Begin(string reason)
    {
        if (_quitting)
        {
            return;
        }

        _quitting = true;
        MacSmoke.Log("quit " + reason);
        foreach (var scene in UIApplication.SharedApplication.ConnectedScenes.OfType<UIWindowScene>())
        {
            Detach(scene);
        }
    }

    private static void Detach(UIWindowScene scene)
    {
        try
        {
            foreach (var window in scene.Windows)
            {
                window.RootViewController = new UIViewController();
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Chuvadi: detaching the page failed: " + ex.Message);
        }
    }
}
