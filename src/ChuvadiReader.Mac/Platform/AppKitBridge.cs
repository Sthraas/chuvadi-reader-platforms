using Foundation;
using System.Runtime.InteropServices;
using ObjCRuntime;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// The few AppKit window calls Mac Catalyst doesn't expose through UIKit (minimise, zoom,
/// window drag, the standard window buttons). Reached through the Objective-C runtime that
/// ships with macOS (libobjc) — no third-party code, no AppKit plug-in bundle.
/// Every call is best-effort: if AppKit doesn't answer, nothing happens and nothing throws.
/// </summary>
internal static class AppKitBridge
{
    private const string LibObjC = "/usr/lib/libobjc.dylib";

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern IntPtr SendIntPtr(IntPtr receiver, IntPtr selector);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern IntPtr SendIntPtrLong(IntPtr receiver, IntPtr selector, long arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern void SendVoidIntPtr(IntPtr receiver, IntPtr selector, IntPtr arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern void SendVoidBool(IntPtr receiver, IntPtr selector, [MarshalAs(UnmanagedType.I1)] bool arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    [return: MarshalAs(UnmanagedType.I1)]
    private static extern bool SendBool(IntPtr receiver, IntPtr selector);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern long SendLong(IntPtr receiver, IntPtr selector);

    /// <summary>NSModalResponseOK.</summary>
    private const long ModalOk = 1;

    /// <summary>Settings for a native NSOpenPanel / NSSavePanel.</summary>
    public sealed record PanelOptions
    {
        public string Title { get; init; } = string.Empty;
        public IReadOnlyList<string> Extensions { get; init; } = Array.Empty<string>();
        public bool Multiple { get; init; }
        public bool Folders { get; init; }
        public string? SuggestedName { get; init; }
    }

    /// <summary>Runs a native open panel (application-modal, like the Windows dialogs).
    /// Returns the chosen paths, or an empty list when cancelled or unavailable.</summary>
    public static IReadOnlyList<string> RunOpenPanel(PanelOptions o)
    {
        var cls = Class.GetHandle("NSOpenPanel");
        if (cls == IntPtr.Zero)
        {
            return Array.Empty<string>();
        }

        var panel = SendIntPtr(cls, Sel("openPanel"));
        if (panel == IntPtr.Zero)
        {
            return Array.Empty<string>();
        }

        SetTitle(panel, o.Title);
        SendVoidBool(panel, Sel("setCanChooseFiles:"), !o.Folders);
        SendVoidBool(panel, Sel("setCanChooseDirectories:"), o.Folders);
        SendVoidBool(panel, Sel("setCanCreateDirectories:"), o.Folders);
        SendVoidBool(panel, Sel("setAllowsMultipleSelection:"), o.Multiple);
        SetAllowedTypes(panel, o.Extensions);

        // CI smoke (M-16): the real panel runs modally, is closed by a timer in the modal run loop, and a
        // fixture file stands in for the person's choice — the Ui's whole Open path runs as it does for a person.
        var smokePick = MacSmoke.NextPick();
        if (smokePick is not null)
        {
            var timer = NSTimer.CreateTimer(1.0, false, _ => SendVoidIntPtr(panel, Sel("cancel:"), IntPtr.Zero));
            NSRunLoop.Main.AddTimer(timer, NSRunLoopMode.Common);
            SendLong(panel, Sel("runModal"));
            MacSmoke.Log("picked " + System.IO.Path.GetFileName(smokePick));
            return new[] { smokePick };
        }

        if (SendLong(panel, Sel("runModal")) != ModalOk)
        {
            return Array.Empty<string>();
        }

        using var urls = Runtime.GetNSObject<Foundation.NSArray>(SendIntPtr(panel, Sel("URLs")));
        if (urls is null)
        {
            return Array.Empty<string>();
        }

        var paths = new List<string>((int)urls.Count);
        for (nuint i = 0; i < urls.Count; i++)
        {
            var path = urls.GetItem<Foundation.NSUrl>(i)?.Path;
            if (!string.IsNullOrEmpty(path))
            {
                paths.Add(path);
            }
        }

        return paths;
    }

    /// <summary>Runs a native save panel. The panel itself asks before replacing a file.
    /// Returns the chosen path, or null when cancelled or unavailable.</summary>
    public static string? RunSavePanel(PanelOptions o)
    {
        var cls = Class.GetHandle("NSSavePanel");
        if (cls == IntPtr.Zero)
        {
            return null;
        }

        var panel = SendIntPtr(cls, Sel("savePanel"));
        if (panel == IntPtr.Zero)
        {
            return null;
        }

        SetTitle(panel, o.Title);
        SendVoidBool(panel, Sel("setCanCreateDirectories:"), true);
        SetAllowedTypes(panel, o.Extensions);
        if (!string.IsNullOrEmpty(o.SuggestedName))
        {
            using var name = new Foundation.NSString(o.SuggestedName);
            SendVoidIntPtr(panel, Sel("setNameFieldStringValue:"), name.Handle);
        }

        if (SendLong(panel, Sel("runModal")) != ModalOk)
        {
            return null;
        }

        var url = Runtime.GetNSObject<Foundation.NSUrl>(SendIntPtr(panel, Sel("URL")));
        return string.IsNullOrEmpty(url?.Path) ? null : url.Path;
    }

    private static void SetTitle(IntPtr panel, string title)
    {
        if (string.IsNullOrEmpty(title))
        {
            return;
        }

        // Modern macOS panels show the message line, not the title; set both.
        using var s = new Foundation.NSString(title);
        SendVoidIntPtr(panel, Sel("setTitle:"), s.Handle);
        SendVoidIntPtr(panel, Sel("setMessage:"), s.Handle);
    }

    private static void SetAllowedTypes(IntPtr panel, IReadOnlyList<string> extensions)
    {
        var types = new List<UniformTypeIdentifiers.UTType>();
        foreach (var ext in extensions)
        {
            var t = UniformTypeIdentifiers.UTType.CreateFromExtension(ext.TrimStart('.'));
            if (t is not null)
            {
                types.Add(t);
            }
        }

        if (types.Count == 0)
        {
            return; // no filter: every file can be chosen
        }

        using var array = Foundation.NSArray.FromNSObjects(types.ToArray());
        SendVoidIntPtr(panel, Sel("setAllowedContentTypes:"), array.Handle);
    }

    // NSWindowButton values (AppKit).
    private const long CloseButton = 0;
    private const long MiniaturizeButton = 1;
    private const long ZoomButton = 2;

    private static IntPtr Sel(string name) => Selector.GetHandle(name);

    /// <summary>[NSApplication sharedApplication], or zero when AppKit isn't loaded.</summary>
    private static IntPtr SharedApplication()
    {
        var cls = Class.GetHandle("NSApplication");
        return cls == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(cls, Sel("sharedApplication"));
    }

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern ulong SendULong(IntPtr receiver, IntPtr selector);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern IntPtr SendIntPtrULong(IntPtr receiver, IntPtr selector, ulong arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern void SendVoidULong(IntPtr receiver, IntPtr selector, ulong arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern void SendVoidLong(IntPtr receiver, IntPtr selector, long arg);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern CoreGraphics.CGRect SendRect(IntPtr receiver, IntPtr selector);

    // x64 returns structs larger than 16 bytes through objc_msgSend_stret.
    [DllImport(LibObjC, EntryPoint = "objc_msgSend_stret")]
    private static extern void SendRectStret(out CoreGraphics.CGRect result, IntPtr receiver, IntPtr selector);

    [DllImport(LibObjC, EntryPoint = "objc_msgSend")]
    private static extern void SendVoidRectBool(IntPtr receiver, IntPtr selector, CoreGraphics.CGRect rect, [MarshalAs(UnmanagedType.I1)] bool display);

    private static CoreGraphics.CGRect Rect(IntPtr receiver, string selector)
    {
        if (receiver == IntPtr.Zero)
        {
            return default;
        }

        if (RuntimeInformation.ProcessArchitecture == Architecture.X64)
        {
            SendRectStret(out var r, receiver, Sel(selector));
            return r;
        }

        return SendRect(receiver, Sel(selector));
    }

    private static string? Text(IntPtr nsString)
        => nsString == IntPtr.Zero ? null : Runtime.GetNSObject<Foundation.NSString>(nsString)?.ToString();

    /// <summary>The app's main NSWindow: key, else main, else the first UIKit-hosted window (at launch the
    /// window exists before it becomes key — Mac Test M-04 / M-07).</summary>
    public static IntPtr AppWindow()
    {
        var key = KeyWindow();
        if (key != IntPtr.Zero)
        {
            return key;
        }

        var app = SharedApplication();
        if (app == IntPtr.Zero)
        {
            return IntPtr.Zero;
        }

        var windows = SendIntPtr(app, Sel("windows"));
        var count = windows == IntPtr.Zero ? 0UL : SendULong(windows, Sel("count"));
        for (ulong i = 0; i < count; i++)
        {
            var w = SendIntPtrULong(windows, Sel("objectAtIndex:"), i);
            var cls = Text(SendIntPtr(SendIntPtr(w, Sel("className")), Sel("description"))) ?? string.Empty;
            if (cls.Contains("UINSWindow", StringComparison.Ordinal))
            {
                return w;
            }
        }

        return IntPtr.Zero;
    }

    // NSWindowStyleMaskFullSizeContentView; NSWindowTitleHidden.
    private const ulong FullSizeContentView = 1UL << 15;
    private const long TitleHidden = 1;

    /// <summary>
    /// Mac Test M-04: the page reaches the window's top edge. Hiding the title text and buttons is not
    /// enough — AppKit still reserves the title bar's height — so the content view is made full-size
    /// under a transparent, title-less title bar. Idempotent; re-applied when AppKit relays the window out.
    /// </summary>
    public static void MakeContentFullHeight(IntPtr window)
    {
        if (window == IntPtr.Zero)
        {
            return;
        }

        var mask = SendULong(window, Sel("styleMask"));
        if ((mask & FullSizeContentView) == 0)
        {
            SendVoidULong(window, Sel("setStyleMask:"), mask | FullSizeContentView);
        }

        SendVoidBool(window, Sel("setTitlebarAppearsTransparent:"), true);
        SendVoidLong(window, Sel("setTitleVisibility:"), TitleHidden);
    }

    /// <summary>
    /// Mac Test M-03: AppKit's saved window state (NSPersistentUIManager) commits a last frame during
    /// termination, after MAUI has torn the page down; Chuvadi restores its own tabs, so windows are not restorable.
    /// </summary>
    public static void SetRestorable(IntPtr window, bool restorable)
    {
        if (window != IntPtr.Zero)
        {
            SendVoidBool(window, Sel("setRestorable:"), restorable);
        }
    }

    /// <summary>Mac Test M-07: sizes the window's frame and centres it on its screen.</summary>
    public static void SizeAndCenter(IntPtr window, double width, double height)
    {
        if (window == IntPtr.Zero)
        {
            return;
        }

        // Never larger than the screen's visible area (a 1024×768 display gets the whole visible area).
        var frame = Rect(window, "frame");
        var screen = Rect(SendIntPtr(window, Sel("screen")), "visibleFrame");
        if (screen.Width > 0 && screen.Height > 0)
        {
            width = Math.Min(width, (double)screen.Width);
            height = Math.Min(height, (double)screen.Height);
        }

        SendVoidRectBool(window, Sel("setFrame:display:"), new CoreGraphics.CGRect(frame.X, frame.Y, width, height), true);
        SendVoidIntPtr(window, Sel("center"), IntPtr.Zero);
    }

    /// <summary>Window frame, its screen's visible frame and the content view's frame (smoke diagnostics).</summary>
    public static (CoreGraphics.CGRect Window, CoreGraphics.CGRect Screen, CoreGraphics.CGRect Content) Geometry(IntPtr window)
    {
        var screen = window == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(window, Sel("screen"));
        var content = window == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(window, Sel("contentView"));
        return (Rect(window, "frame"), Rect(screen, "visibleFrame"), Rect(content, "frame"));
    }

    /// <summary>The real macOS menu bar, as AppKit holds it: "Menu: item ⌘key; …" one line per menu
    /// (smoke diagnostics for Mac Test M-01 / M-11).</summary>
    public static IReadOnlyList<string> DumpMainMenu()
    {
        var lines = new List<string>();
        var app = SharedApplication();
        var main = app == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(app, Sel("mainMenu"));
        if (main == IntPtr.Zero)
        {
            return lines;
        }

        var items = SendIntPtr(main, Sel("itemArray"));
        var count = SendULong(items, Sel("count"));
        for (ulong i = 0; i < count; i++)
        {
            var item = SendIntPtrULong(items, Sel("objectAtIndex:"), i);
            var sub = SendIntPtr(item, Sel("submenu"));
            var title = Text(SendIntPtr(sub == IntPtr.Zero ? item : sub, Sel("title"))) ?? "?";
            var parts = new List<string>();
            if (sub != IntPtr.Zero)
            {
                Collect(sub, parts, string.Empty);
            }

            lines.Add($"{title}: {string.Join(" | ", parts)}");
        }

        return lines;
    }

    private static void Collect(IntPtr menu, List<string> parts, string prefix)
    {
        var items = SendIntPtr(menu, Sel("itemArray"));
        var count = SendULong(items, Sel("count"));
        for (ulong i = 0; i < count; i++)
        {
            var item = SendIntPtrULong(items, Sel("objectAtIndex:"), i);
            if (SendBool(item, Sel("isSeparatorItem")))
            {
                continue;
            }

            var title = Text(SendIntPtr(item, Sel("title"))) ?? string.Empty;
            var key = Text(SendIntPtr(item, Sel("keyEquivalent"))) ?? string.Empty;
            var mods = SendULong(item, Sel("keyEquivalentModifierMask"));
            var shortcut = key.Length == 0 ? string.Empty
                : " " + ((mods & (1UL << 18)) != 0 ? "⌃" : string.Empty) + ((mods & (1UL << 19)) != 0 ? "⌥" : string.Empty)
                  + ((mods & (1UL << 17)) != 0 ? "⇧" : string.Empty) + ((mods & (1UL << 20)) != 0 ? "⌘" : string.Empty) + key.ToUpperInvariant();
            parts.Add(prefix + title + shortcut);
            var sub = SendIntPtr(item, Sel("submenu"));
            if (sub != IntPtr.Zero)
            {
                Collect(sub, parts, prefix + title + " › ");
            }
        }
    }

    /// <summary>The app's key NSWindow — the one the person is interacting with.</summary>
    public static IntPtr KeyWindow()
    {
        var app = SharedApplication();
        if (app == IntPtr.Zero)
        {
            return IntPtr.Zero;
        }

        var w = SendIntPtr(app, Sel("keyWindow"));
        return w != IntPtr.Zero ? w : SendIntPtr(app, Sel("mainWindow"));
    }

    public static void Miniaturize(IntPtr window)
    {
        if (window != IntPtr.Zero)
        {
            SendVoidIntPtr(window, Sel("miniaturize:"), IntPtr.Zero);
        }
    }

    public static void Zoom(IntPtr window)
    {
        if (window != IntPtr.Zero)
        {
            SendVoidIntPtr(window, Sel("zoom:"), IntPtr.Zero);
        }
    }

    public static bool IsZoomed(IntPtr window)
        => window != IntPtr.Zero && SendBool(window, Sel("isZoomed"));

    public static void PerformClose(IntPtr window)
    {
        if (window != IntPtr.Zero)
        {
            SendVoidIntPtr(window, Sel("performClose:"), IntPtr.Zero);
        }
    }

    /// <summary>Starts a native window move from the mouse-down that is being handled now.</summary>
    public static void BeginDrag(IntPtr window)
    {
        var app = SharedApplication();
        if (window == IntPtr.Zero || app == IntPtr.Zero)
        {
            return;
        }

        var ev = SendIntPtr(app, Sel("currentEvent"));
        if (ev != IntPtr.Zero)
        {
            SendVoidIntPtr(window, Sel("performWindowDragWithEvent:"), ev);
        }
    }

    /// <summary>Opens a Finder window with the item selected ([NSWorkspace activateFileViewerSelectingURLs:]).</summary>
    public static bool RevealInFinder(string path)
    {
        var cls = Class.GetHandle("NSWorkspace");
        if (cls == IntPtr.Zero)
        {
            return false;
        }

        var workspace = SendIntPtr(cls, Sel("sharedWorkspace"));
        if (workspace == IntPtr.Zero)
        {
            return false;
        }

        using var url = Foundation.NSUrl.CreateFileUrl(path, Directory.Exists(path), null);
        using var urls = Foundation.NSArray.FromNSObjects(url);
        SendVoidIntPtr(workspace, Sel("activateFileViewerSelectingURLs:"), urls.Handle);
        return true;
    }

    /// <summary>
    /// Hides the native title bar completely — its buttons and the (otherwise invisible) strip that
    /// would sit over the top of the page and take its clicks. The Ui draws the traffic lights and
    /// moves the window itself (IWindowControls.BeginDrag).
    /// </summary>
    public static void HideTitlebar(IntPtr window)
    {
        if (window == IntPtr.Zero)
        {
            return;
        }

        var close = SendIntPtrLong(window, Sel("standardWindowButton:"), CloseButton);
        var titlebarView = close == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(close, Sel("superview"));
        var container = titlebarView == IntPtr.Zero ? IntPtr.Zero : SendIntPtr(titlebarView, Sel("superview"));
        if (container != IntPtr.Zero)
        {
            SendVoidBool(container, Sel("setHidden:"), true);
        }

        foreach (var kind in new[] { CloseButton, MiniaturizeButton, ZoomButton })
        {
            var button = SendIntPtrLong(window, Sel("standardWindowButton:"), kind);
            if (button != IntPtr.Zero)
            {
                SendVoidBool(button, Sel("setHidden:"), true);
            }
        }
    }
}
