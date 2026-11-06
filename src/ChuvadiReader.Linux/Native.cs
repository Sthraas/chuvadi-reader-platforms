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

    [LibraryImport(Lib, EntryPoint = "chvd_buttons_on_left")]
    public static partial int ButtonsOnLeft();

    [LibraryImport(Lib, EntryPoint = "chvd_reveal", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int Reveal(string path);

    public static string? Utf8(byte* p) => p == null ? null : Marshal.PtrToStringUTF8((nint)p);
}
