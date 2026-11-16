using System.Runtime.InteropServices;
using ObjCRuntime;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-08 on macOS 15: with the keyboard in a text box of the page (the password prompt, Find), a real ⌃Tab or
/// ⌃⇧Tab reached neither the app's key commands, nor its Window menu items, nor the page — macOS 15 takes it on the
/// way in (macOS 26 and 27 deliver it). So the two keys are taken where AppKit hands the app its events, before
/// anything else can: an NSEvent local monitor, for key-downs in the app's own window only. The page gets the same
/// ⌃Tab keydown as from the key command (<see cref="MacPageKeys.Send"/>), and the event ends there, so one press
/// still moves exactly one tab. The key commands and the Window menu items stay (the menu shows the shortcut and
/// works by mouse). If the monitor cannot be placed, they carry the keys as before.
/// </summary>
internal static class MacTabKeyMonitor
{
    private const string LibObjC = "/usr/lib/libobjc.dylib";
    private const ulong KeyDownMask = 1UL << 10;
    private const ushort TabKeyCode = 48;
    private const nuint Shift = 1 << 17, Control = 1 << 18, Option = 1 << 19, Command = 1 << 20;

    private static IntPtr _monitor;

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern unsafe IntPtr AddMonitor(IntPtr cls, IntPtr sel, ulong mask, BlockLiteral* handler);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern IntPtr Send(IntPtr receiver, IntPtr sel);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern ushort SendUShort(IntPtr receiver, IntPtr sel);
    [DllImport(LibObjC, EntryPoint = "objc_msgSend")] private static extern nuint SendNUInt(IntPtr receiver, IntPtr sel);

    public static unsafe void Install()
    {
        if (_monitor != IntPtr.Zero)
        {
            return;
        }

        try
        {
            var events = Class.GetHandle("NSEvent");
            if (events == IntPtr.Zero)
            {
                return;
            }

            delegate* unmanaged<IntPtr, IntPtr, IntPtr> handler = &OnKeyDown;
            using var block = new BlockLiteral(handler, null, typeof(MacTabKeyMonitor), nameof(OnKeyDown));
            _monitor = AddMonitor(events, Selector.GetHandle("addLocalMonitorForEventsMatchingMask:handler:"), KeyDownMask, &block);
            MacSmoke.Log("tab-key-monitor " + (_monitor != IntPtr.Zero ? 1 : 0));
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Chuvadi: the ⌃Tab monitor could not be set up: " + ex.Message);
            MacSmoke.Log("tab-key-monitor failed " + ex.GetType().Name);
        }
    }

    /// <summary>AppKit's block: returns the event to let it go on, or nil when it was handled here.</summary>
    [UnmanagedCallersOnly]
    private static IntPtr OnKeyDown(IntPtr block, IntPtr nsEvent)
    {
        try
        {
            if (nsEvent == IntPtr.Zero || SendUShort(nsEvent, Selector.GetHandle("keyCode")) != TabKeyCode)
            {
                return nsEvent;
            }

            var flags = SendNUInt(nsEvent, Selector.GetHandle("modifierFlags"));
            if ((flags & Control) == 0 || (flags & (Option | Command)) != 0)
            {
                return nsEvent;
            }

            // Only in the app's own window: a native panel (Open, Print) keeps its own ⌃Tab.
            var window = AppKitBridge.AppWindow();
            if (window == IntPtr.Zero || Send(nsEvent, Selector.GetHandle("window")) != window || !MacPageKeys.Available)
            {
                return nsEvent;
            }

            MacPageKeys.Send("Tab", "Tab", ctrl: true, shift: (flags & Shift) != 0, meta: false);
            return IntPtr.Zero;
        }
        catch
        {
            return nsEvent;
        }
    }
}
