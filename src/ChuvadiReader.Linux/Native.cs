using System.Runtime.InteropServices;

namespace ChuvadiReader.Linux;

/// <summary>Calls into libchvdhost.so (native/chvdhost.c). Every call except <see cref="Wake"/> and
/// <see cref="PostMessage"/> must be made on the GTK main thread.</summary>
internal static unsafe partial class Native
{
    private const string Lib = "libchvdhost.so";

    public enum WindowEvent
    {
        MaximizedChanged = 1,
        CloseRequested = 2,
        FilesDropped = 3,
        ExternalLink = 4,
        FirstPaint = 5,
        DialogResult = 6,
        PrintResult = 7,
        JsResult = 8,
        ButtonLayout = 9,
        SessionEnd = 10,
    }

    [LibraryImport(Lib, EntryPoint = "chvd_init")]
    public static partial int Init(
        delegate* unmanaged<nint, byte*, void> scheme,
        delegate* unmanaged<byte*, void> message,
        delegate* unmanaged<void> wake,
        delegate* unmanaged<int, byte*, void> windowEvent);

    [LibraryImport(Lib, EntryPoint = "chvd_run")]
    public static partial void Run();

    [LibraryImport(Lib, EntryPoint = "chvd_quit")]
    public static partial void Quit();

    [LibraryImport(Lib, EntryPoint = "chvd_wake")]
    public static partial void Wake();

    [LibraryImport(Lib, EntryPoint = "chvd_post_message", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void PostMessage(string jsStringLiteral);

    [LibraryImport(Lib, EntryPoint = "chvd_scheme_respond", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void SchemeRespond(nint request, int status, string contentType, byte* bytes, nuint length, string? cacheControl);

    [LibraryImport(Lib, EntryPoint = "chvd_create_window", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int CreateWindow(string title, string appId, int width, int height, string background, int devTools);

    [LibraryImport(Lib, EntryPoint = "chvd_show")]
    public static partial void Show(int maximized);

    /// <summary>The start-up mark's colours for the saved theme (accent "#RRGGBB", the bar's outline). Before <see cref="Show"/>.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_start_mark", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void StartMark(string accent, string rule);

    /// <summary>From inside <see cref="GtkHost.CloseRequested"/> only: this close request leaves the window open.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_hold_close")]
    public static partial void HoldClose();

    /// <summary>Starts listening for the desktop's "about to sign out or shut down" (D-194). Once, after <see cref="Init"/>.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_session_watch")]
    public static partial void SessionWatch();

    /// <summary>Holds a sign-out or shutdown with this reason (the desktop shows it), or lets it go with null.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_session_hold", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void SessionHold(string? reason);

    /// <summary>0 nothing held, 1 being asked for, 2 held through the portal, 3 through the GNOME session manager (UI tests).</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_session_hold_state")]
    public static partial int SessionHoldState();

    /// <summary>The app has drawn itself: the start-up mark over the page goes.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_ready")]
    public static partial void Ready();

    /// <summary>1 while the start-up mark is still over the page (UI tests).</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_start_mark_shown")]
    public static partial int StartMarkShown();

    /// <summary>One step of a pinch at a place in the view, as the pinch gesture sends it (UI tests).
    /// phase: 0 begin, 1 change, 2 end; scale: since the begin.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_pinch")]
    public static partial void Pinch(int phase, double scale, double x, double y);

    [LibraryImport(Lib, EntryPoint = "chvd_navigate", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void Navigate(string uri);

    [LibraryImport(Lib, EntryPoint = "chvd_set_zoom")]
    public static partial void SetZoom(double factor);

    [LibraryImport(Lib, EntryPoint = "chvd_set_background", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void SetBackground(string hex);

    [LibraryImport(Lib, EntryPoint = "chvd_minimize")]
    public static partial void Minimize();

    [LibraryImport(Lib, EntryPoint = "chvd_toggle_maximize")]
    public static partial void ToggleMaximize();

    [LibraryImport(Lib, EntryPoint = "chvd_is_maximized")]
    public static partial int IsMaximized();

    [LibraryImport(Lib, EntryPoint = "chvd_close")]
    public static partial void Close();

    [LibraryImport(Lib, EntryPoint = "chvd_begin_move")]
    public static partial void BeginMove();

    [LibraryImport(Lib, EntryPoint = "chvd_clipboard_set_png")]
    public static partial int ClipboardSetPng(byte* bytes, nuint length);

    [LibraryImport(Lib, EntryPoint = "chvd_file_dialog", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void FileDialog(int kind, int token, string title, string? initialFolder, string? initialName, string? filters);

    [LibraryImport(Lib, EntryPoint = "chvd_clipboard_set_text", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void ClipboardSetText(string text);

    /// <summary>Brings the window to the front; <paramref name="token"/> = the launcher's activation token, if any.</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_present", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void Present(string? token);

    [LibraryImport(Lib, EntryPoint = "chvd_sandbox_check")]
    private static partial int SandboxCheck(byte* buf, int size);

    /// <summary>Whether WebKit's sandbox (bubblewrap) can start here; <paramref name="detail"/> = bwrap's message if not.</summary>
    public static bool SandboxCheck(out string detail)
    {
        Span<byte> buf = stackalloc byte[512];
        int ok;
        fixed (byte* p = buf)
        {
            ok = SandboxCheck(p, buf.Length);
        }

        var len = buf.IndexOf((byte)0);
        detail = System.Text.Encoding.UTF8.GetString(len < 0 ? buf : buf[..len]);
        return ok != 0;
    }

    [LibraryImport(Lib, EntryPoint = "chvd_show_error", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void ShowError(string title, string detail);

    /// <summary>Bit 0: no GPU; bit 1: WebKit compositing off (hardware acceleration policy "never").</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_render_info")]
    public static partial int RenderInfo();

    /// <summary>Sets GTK's window-button layout (UI tests: what the desktop's settings bridge does).</summary>
    [LibraryImport(Lib, EntryPoint = "chvd_set_button_layout", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void SetButtonLayout(string layout);

    [LibraryImport(Lib, EntryPoint = "chvd_button_layout")]
    private static partial int ButtonLayout(byte* buf, int size);

    /// <summary>GTK's gtk-decoration-layout (the desktop's window-button layout), or null when unset.</summary>
    public static string? ButtonLayout()
    {
        Span<byte> buf = stackalloc byte[256];
        int len;
        fixed (byte* p = buf)
        {
            len = ButtonLayout(p, buf.Length);
        }

        if (len < 0)
        {
            return null;
        }

        if (len >= buf.Length)
        {
            var big = new byte[len + 1];
            fixed (byte* p = big)
            {
                ButtonLayout(p, big.Length);
            }

            return System.Text.Encoding.UTF8.GetString(big, 0, len);
        }

        return System.Text.Encoding.UTF8.GetString(buf[..len]);
    }

    [LibraryImport(Lib, EntryPoint = "chvd_reveal", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int Reveal(string path);

    [LibraryImport(Lib, EntryPoint = "chvd_print_dialog", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void PrintDialog(int token, string title, int pageCount, int currentPage, string pages, int copies);

    [LibraryImport(Lib, EntryPoint = "chvd_eval_js", StringMarshalling = StringMarshalling.Utf8)]
    public static partial void EvalJs(int token, string script);

    public static string? Utf8(byte* p) => p == null ? null : Marshal.PtrToStringUTF8((nint)p);
}
