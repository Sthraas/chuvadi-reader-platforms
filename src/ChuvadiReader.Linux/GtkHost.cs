using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace ChuvadiReader.Linux;

/// <summary>
/// Owns the native callbacks and the GTK main thread. Blazor itself runs on its own
/// synchronization context (<c>Dispatcher.CreateDefault()</c>), so heavy rendering never
/// blocks the window; anything that touches GTK is posted here with <see cref="Post"/>
/// or <see cref="InvokeAsync{T}"/>.
/// </summary>
internal static unsafe class GtkHost
{
    private static readonly ConcurrentQueue<Action> Queue = new();
    private static int _mainThreadId;
    private static LinuxWebViewManager? _manager;

    public static event Action<bool>? MaximizedChanged;

    public static event Action<string[]>? FilesDropped;

    /// <summary>Files a later launch handed to this running copy (single instance, B-05).</summary>
    public static event Action<string[]>? InstanceOpen;

#if CHUVADI_UITEST
    /// <summary>UI test build only: the same event the window's GTK drop target raises.</summary>
    internal static void SimulateDrop(string[] paths) => FilesDropped?.Invoke(paths);
#endif

    public static event Action<string>? ExternalLinkRequested;

    public static event Action? FirstPaint;

    public static event Action? CloseRequested;

    /// <summary>Token, then the chosen paths (empty when cancelled).</summary>
    public static event Action<int, string[]>? DialogResult;

    /// <summary>Print dialog answer: token, then key=value lines (empty when cancelled).</summary>
    public static event Action<int, string[]>? PrintResult;

    /// <summary>UI test builds only: token, then the script result (JSON, or "!error").</summary>
    public static event Action<int, string>? JsResult;

    public static bool IsMainThread => Environment.CurrentManagedThreadId == _mainThreadId;

    /// <summary>Initialises GTK on the calling thread, which becomes the GTK main thread.
    /// Returns false when there is no display.</summary>
    public static bool Init()
    {
        _mainThreadId = Environment.CurrentManagedThreadId;
        return Native.Init(&OnScheme, &OnMessage, &OnWake, &OnWindowEvent) != 0;
    }

    public static void Attach(LinuxWebViewManager manager) => _manager = manager;

    /// <summary>Runs <paramref name="action"/> on the GTK main thread (inline if already there).</summary>
    public static void Post(Action action)
    {
        if (IsMainThread)
        {
            action();
            return;
        }

        Queue.Enqueue(action);
        Native.Wake();
    }

    public static Task<T> InvokeAsync<T>(Func<T> func)
    {
        if (IsMainThread)
        {
            return Task.FromResult(func());
        }

        var tcs = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        Queue.Enqueue(() =>
        {
            try
            {
                tcs.SetResult(func());
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        });
        Native.Wake();
        return tcs.Task;
    }

    /// <summary>Thread-safe: hands a message to blazor.webview.js.</summary>
    public static void SendToPage(string message) => Native.PostMessage(JsonSerializer.Serialize(message));

    [UnmanagedCallersOnly]
    private static void OnWake()
    {
        while (Queue.TryDequeue(out var action))
        {
            try
            {
                action();
            }
            catch (Exception ex)
            {
                Program.Report(ex);
            }
        }
    }

    [UnmanagedCallersOnly]
    private static void OnMessage(byte* message)
    {
        try
        {
            var text = Native.Utf8(message);
            if (text is not null)
            {
                _manager?.Receive(text);
            }
        }
        catch (Exception ex)
        {
            Program.Report(ex);
        }
    }

    [UnmanagedCallersOnly]
    private static void OnScheme(nint request, byte* uri)
    {
        int status = 404;
        string contentType = "text/plain";
        string? cacheControl = null;
        byte[] body = Encoding.UTF8.GetBytes("Not found");
        try
        {
            var u = Native.Utf8(uri);
            if (u is not null && _manager is not null && _manager.TryGetAsset(u, out var s, out var type, out var bytes, out var cache))
            {
                status = s;
                contentType = type;
                body = bytes;
                cacheControl = cache;
            }
        }
        catch (Exception ex)
        {
            Program.Report(ex);
            status = 500;
            body = Encoding.UTF8.GetBytes("Internal error");
        }

        fixed (byte* p = body)
        {
            Native.SchemeRespond(request, status, contentType, p, (nuint)body.Length, cacheControl);
        }
    }

    [UnmanagedCallersOnly]
    private static void OnWindowEvent(int kind, byte* payload)
    {
        try
        {
            var text = Native.Utf8(payload);
            switch ((Native.WindowEvent)kind)
            {
                case Native.WindowEvent.MaximizedChanged:
                    MaximizedChanged?.Invoke(text == "1");
                    break;
                case Native.WindowEvent.CloseRequested:
                    CloseRequested?.Invoke();
                    break;
                case Native.WindowEvent.FilesDropped when text is not null:
                    FilesDropped?.Invoke(text.Split('\n', StringSplitOptions.RemoveEmptyEntries));
                    break;
                case Native.WindowEvent.ExternalLink when text is not null:
                    ExternalLinkRequested?.Invoke(text);
                    break;
                case Native.WindowEvent.DialogResult when text is not null:
                    var lines = text.Split('\n');
                    DialogResult?.Invoke(int.Parse(lines[0], System.Globalization.CultureInfo.InvariantCulture), lines[1..]);
                    break;
                case Native.WindowEvent.PrintResult when text is not null:
                    var answer = text.Split('\n');
                    PrintResult?.Invoke(int.Parse(answer[0], System.Globalization.CultureInfo.InvariantCulture), answer[1..]);
                    break;
                case Native.WindowEvent.JsResult when text is not null:
                    var nl = text.IndexOf('\n');
                    JsResult?.Invoke(int.Parse(text.AsSpan(0, nl), System.Globalization.CultureInfo.InvariantCulture), text[(nl + 1)..]);
                    break;
                case Native.WindowEvent.InstanceOpen:
                    InstanceOpen?.Invoke((text ?? string.Empty).Split('\n', StringSplitOptions.RemoveEmptyEntries));
                    break;
                case Native.WindowEvent.FirstPaint:
                    FirstPaint?.Invoke();
                    break;
            }
        }
        catch (Exception ex)
        {
            Program.Report(ex);
        }
    }
}
