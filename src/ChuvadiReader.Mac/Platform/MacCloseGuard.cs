using System.Runtime.InteropServices;
using ChuvadiReader.Platform;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// D-190: the question before closing, for the two closes the Mac host owns — Quit (⌘Q, the Chuvadi menu, the Dock,
/// another app asking, log-out) and closing the window (the red button, which is the Ui's own, and anything else that
/// closes it). Closing a tab, the other tabs or all tabs asks inside the kit (TabsService), so the host adds nothing
/// there. The contract is <see cref="IUnsavedWork"/>: with nothing unsaved the close goes on at once, as before; with
/// unsaved marks the close is held, the window comes forward, the Ui asks, and the close goes on only on "true".
///
/// A Mac Catalyst app has no UIKit callback that can hold a quit or a window close. AppKit has both
/// (applicationShouldTerminate:, windowShouldClose:), on delegates UIKit owns. This puts a method in front of each
/// and passes every call it does not hold on to UIKit's own, so nothing else changes. If either hook cannot be placed
/// (a later macOS names things differently), it says so in the log and that close goes on unasked, as before D-190.
/// </summary>
internal static unsafe class MacCloseGuard
{
    private const string LibObjC = "/usr/lib/libobjc.dylib";
    private const nuint TerminateCancel = 0, TerminateNow = 1;

    private static IntPtr _uikitShouldTerminate, _uikitShouldClose;
    private static bool _quitHooked, _windowHooked, _asking, _closeNow;

    [DllImport(LibObjC)] private static extern IntPtr object_getClass(IntPtr obj);
    [DllImport(LibObjC)] private static extern IntPtr class_getMethodImplementation(IntPtr cls, IntPtr sel);
    [DllImport(LibObjC)] [return: MarshalAs(UnmanagedType.I1)] private static extern bool class_respondsToSelector(IntPtr cls, IntPtr sel);
    [DllImport(LibObjC)] private static extern IntPtr class_replaceMethod(IntPtr cls, IntPtr sel, IntPtr imp, string types);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern IntPtr Send(IntPtr receiver, IntPtr sel);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern void SendPtr(IntPtr receiver, IntPtr sel, IntPtr arg);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern void SendFlag(IntPtr receiver, IntPtr sel, [MarshalAs(UnmanagedType.I1)] bool arg);

    private static IntPtr Sel(string name) => Selector.GetHandle(name);

    private static IntPtr App()
    {
        var cls = Class.GetHandle("NSApplication");
        return cls == IntPtr.Zero ? IntPtr.Zero : Send(cls, Sel("sharedApplication"));
    }

    /// <summary>Places the hooks; safe to call again (the window may not be up the first time).</summary>
    public static void Install()
    {
        try
        {
            var app = App();
            if (!_quitHooked && app != IntPtr.Zero && Send(app, Sel("delegate")) is var appDelegate && appDelegate != IntPtr.Zero)
            {
                _uikitShouldTerminate = Hook(object_getClass(appDelegate), "applicationShouldTerminate:",
                    (IntPtr)(delegate* unmanaged<IntPtr, IntPtr, IntPtr, nuint>)&ShouldTerminate, "Q@:@");
                _quitHooked = true;
                MacSmoke.Log("close-guard quit hooked uikit=" + (_uikitShouldTerminate != IntPtr.Zero ? 1 : 0));
            }

            var window = AppKitBridge.AppWindow();
            if (!_windowHooked && window != IntPtr.Zero)
            {
                // AppKit asks the window's delegate, or the window itself when it has none.
                var windowDelegate = Send(window, Sel("delegate"));
                _uikitShouldClose = Hook(object_getClass(windowDelegate != IntPtr.Zero ? windowDelegate : window), "windowShouldClose:",
                    (IntPtr)(delegate* unmanaged<IntPtr, IntPtr, IntPtr, byte>)&ShouldClose, "c@:@");
                _windowHooked = true;
                MacSmoke.Log("close-guard window hooked uikit=" + (_uikitShouldClose != IntPtr.Zero ? 1 : 0));
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Chuvadi: the question before closing could not be set up: " + ex.Message);
            MacSmoke.Log("close-guard failed " + ex.GetType().Name);
        }
    }

    /// <summary>Puts <paramref name="mine"/> on the class and returns what answered before (zero: nothing did).</summary>
    private static IntPtr Hook(IntPtr cls, string selector, IntPtr mine, string types)
    {
        var sel = Sel(selector);
        var before = class_respondsToSelector(cls, sel) ? class_getMethodImplementation(cls, sel) : IntPtr.Zero;
        class_replaceMethod(cls, sel, mine, types);
        return before;
    }

    private static IUnsavedWork? Unsaved()
        => IPlatformApplication.Current?.Services.GetService(typeof(IUnsavedWork)) as IUnsavedWork;

    [UnmanagedCallersOnly]
    private static nuint ShouldTerminate(IntPtr self, IntPtr sel, IntPtr sender)
    {
        try
        {
            if (!_closeNow && Unsaved() is { HasUnsavedWork: true } work)
            {
                Ask(work, "quit", () => SendPtr(App(), Sel("terminate:"), IntPtr.Zero));
                return TerminateCancel;
            }
        }
        catch
        {
            // Never the reason the app cannot quit.
        }

        return _uikitShouldTerminate != IntPtr.Zero
            ? ((delegate* unmanaged<IntPtr, IntPtr, IntPtr, nuint>)_uikitShouldTerminate)(self, sel, sender)
            : TerminateNow;
    }

    [UnmanagedCallersOnly]
    private static byte ShouldClose(IntPtr self, IntPtr sel, IntPtr window)
    {
        try
        {
            if (!_closeNow && Unsaved() is { HasUnsavedWork: true } work)
            {
                Ask(work, "window", () => Send(window, Sel("close")));
                return 0;
            }
        }
        catch
        {
            // Never the reason the window cannot close.
        }

        return _uikitShouldClose != IntPtr.Zero
            ? ((delegate* unmanaged<IntPtr, IntPtr, IntPtr, byte>)_uikitShouldClose)(self, sel, window)
            : (byte)1;
    }

    /// <summary>Holds the close: window forward, the Ui asks, and <paramref name="close"/> runs only on "close now".</summary>
    private static void Ask(IUnsavedWork work, string what, Action close)
    {
        MacSmoke.Log("close-guard held " + what + (_asking ? " (already asking)" : string.Empty));
        if (_asking)
        {
            return;
        }

        _asking = true;
        var app = App();
        if (app != IntPtr.Zero)
        {
            SendFlag(app, Sel("activateIgnoringOtherApps:"), true);
        }

        var window = AppKitBridge.AppWindow();
        if (window != IntPtr.Zero)
        {
            SendPtr(window, Sel("makeKeyAndOrderFront:"), IntPtr.Zero); // also brings it out of the Dock
        }

        _ = AskAsync(work, what, close);
    }

    private static async Task AskAsync(IUnsavedWork work, string what, Action close)
    {
        var closeNow = false;
        try
        {
            closeNow = await work.ConfirmCloseAsync().ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Chuvadi: the question before closing failed: " + ex.Message);
        }

        UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            _asking = false;
            MacSmoke.Log("close-guard answer " + what + " close=" + (closeNow ? 1 : 0));
            if (!closeNow)
            {
                return;
            }

            _closeNow = true;
            try
            {
                close();
            }
            finally
            {
                _closeNow = what == "quit"; // a quit stays decided; a closed window leaves the app running
            }
        });
    }
}
