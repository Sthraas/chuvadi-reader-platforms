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
