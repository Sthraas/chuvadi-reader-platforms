using System;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using Microsoft.AspNetCore.Components.WebView;
using Microsoft.AspNetCore.Components.WebView.Wpf;
using Microsoft.Web.WebView2.Core;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Windows.Platform;

namespace ChuvadiReader.Windows;

public partial class MainWindow : Window
{
    private readonly IServiceProvider _services;

    public MainWindow(IServiceProvider services)
    {
        InitializeComponent();
        _services = services;

        Web.Services = services;
        Web.RootComponents.Add(new RootComponent
        {
            Selector = "#app",
            ComponentType = typeof(ChuvadiReader.Ui.App),
        });

        Web.BlazorWebViewInitializing += OnBlazorWebViewInitializing;
        Web.BlazorWebViewInitialized += OnBlazorWebViewInitialized;
        StateChanged += OnStateChanged;

        // Drop a PDF (or doc) anywhere on the window to open it in the reader.
        AllowDrop = true;
        DragOver += OnFileDragOver;
        Drop += OnFileDrop;
    }

    // Same list as the Open dialog (Core: DocumentFormatExtensions.OpenableExtensions).
    private static bool IsSupportedFile(string path)
        => ChuvadiReader.Core.Documents.DocumentFormatExtensions.IsOpenable(path);

    private static bool HasSupportedFile(DragEventArgs e)
        => e.Data.GetDataPresent(DataFormats.FileDrop)
           && e.Data.GetData(DataFormats.FileDrop) is string[] files
           && files.Any(IsSupportedFile);

    private void OnFileDragOver(object sender, DragEventArgs e)
    {
        e.Effects = HasSupportedFile(e) ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private void OnFileDrop(object sender, DragEventArgs e)
    {
        if (e.Data.GetData(DataFormats.FileDrop) is string[] files)
        {
            OpenDropped(files);
        }
    }

    // W-02: a drop on the page (almost the whole window) arrives from the page itself: host-drop.js hands the
    // dropped File objects over with postMessageWithAdditionalObjects, and WebView2 gives the host their paths.
    // (WebView2's native window covers the WPF window, so the window's own Drop only fires on its edges; the
    // earlier fix, turning WebView2's drop off, left drops on the page doing nothing.)
    private void OnWebMessageReceived(object? sender, Microsoft.Web.WebView2.Core.CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (e.WebMessageAsJson != "\"chvd:files-dropped\"" || e.AdditionalObjects is not { Count: > 0 } objects)
        {
            return;
        }

        var paths = objects.OfType<Microsoft.Web.WebView2.Core.CoreWebView2File>()
            .Select(f => f.Path)
            .Where(p => !string.IsNullOrEmpty(p))
            .ToArray();
        OpenDropped(paths);
    }

    private void OpenDropped(IReadOnlyList<string> files)
    {
        var supported = files.Where(IsSupportedFile).ToArray();
        if (supported.Length == 0)
        {
            return;
        }

        // The shared router (ChuvadiReader.Hosting.IncomingFiles) sends the files to the Bench shelf
        // when the Bench is open, otherwise each to its own Reader tab (approved 7 Nov: every
        // dropped file opens, not just the first).
        if (_services.GetService(typeof(ChuvadiReader.Hosting.IncomingFiles)) is ChuvadiReader.Hosting.IncomingFiles incoming)
        {
            incoming.Receive(supported);
            Activate();
        }
    }

    private void OnBlazorWebViewInitializing(object? sender, BlazorWebViewInitializingEventArgs e)
    {
        // Stable per-build user-data folder: WebView2 reuses one profile across
        // launches of the same build (no first-run setup, so no white flash), and a
        // rebuild lands on a fresh folder so edited CSS/JS can't be served stale.
        e.UserDataFolder = WebViewCache.ResolveAndPrune();

        // HTTP cache stays ON for fast startup. The build-keyed folder above means a
        // new build always starts from an empty cache, so there's nothing stale to
        // serve — we no longer need --disable-http-cache (which forced a full asset
        // reload, and the latency of that was the start-up delay).
    }

    private void OnBlazorWebViewInitialized(object? sender, BlazorWebViewInitializedEventArgs e)
    {
        try
        {
            var settings = e.WebView.CoreWebView2.Settings;
            settings.IsZoomControlEnabled = false; // no Ctrl+scroll / Ctrl +/- zoom
            settings.IsPinchZoomEnabled = false;   // no trackpad / touch pinch zoom
        }
        catch
        {
            // older WebView2 runtime without these settings — non-fatal
        }

        // W-02: dropped files come from the page (host-drop.js); WebView2 keeps its own drop handling on.
        e.WebView.CoreWebView2.WebMessageReceived += OnWebMessageReceived;

        // Interface size (Settings) zooms the whole WebView; attach now that it exists.
        if (_services.GetService(typeof(ChuvadiReader.Core.Window.IUiScale)) is ChuvadiReader.Windows.Platform.WpfUiScale scale)
        {
            scale.Attach(e.WebView, e.WebView.Dispatcher);
        }
    }

    private void OnStateChanged(object? sender, EventArgs e)
    {
        // A custom-chrome window clips its content by the resize-border thickness
        // when maximized, which hides the top of the title bar. Compensate with a
        // matching margin so the whole title bar stays visible.
        Web.Margin = WindowState == WindowState.Maximized
            ? new Thickness(
                SystemParameters.WindowResizeBorderThickness.Left,
                SystemParameters.WindowResizeBorderThickness.Top,
                SystemParameters.WindowResizeBorderThickness.Right,
                SystemParameters.WindowResizeBorderThickness.Bottom)
            : new Thickness(0);
    }

    // A borderless / custom-chrome window maximizes to the full monitor, covering
    // the taskbar, unless we clamp the maximized bounds to the monitor work area.
    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        var handle = new WindowInteropHelper(this).Handle;
        HwndSource.FromHwnd(handle)?.AddHook(WindowProc);

        // Maximize only after the hook is installed, so the first maximize is
        // clamped to the work area instead of spilling under the taskbar.
        WindowState = WindowState.Maximized;
    }

    private static IntPtr WindowProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        const int WM_GETMINMAXINFO = 0x0024;
        if (msg == WM_GETMINMAXINFO)
        {
            var mmi = Marshal.PtrToStructure<MINMAXINFO>(lParam);
            const int MONITOR_DEFAULTTONEAREST = 0x00000002;
            var monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
            if (monitor != IntPtr.Zero)
            {
                var info = new MONITORINFO { cbSize = Marshal.SizeOf<MONITORINFO>() };
                if (GetMonitorInfo(monitor, ref info))
                {
                    var work = info.rcWork;
                    var mon = info.rcMonitor;
                    mmi.ptMaxPosition.X = Math.Abs(work.Left - mon.Left);
                    mmi.ptMaxPosition.Y = Math.Abs(work.Top - mon.Top);
                    mmi.ptMaxSize.X = Math.Abs(work.Right - work.Left);
                    mmi.ptMaxSize.Y = Math.Abs(work.Bottom - work.Top);
                }
            }
            Marshal.StructureToPtr(mmi, lParam, true);
            handled = true;
        }
        return IntPtr.Zero;
    }

    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr hwnd, int flags);

    [DllImport("user32.dll")]
    private static extern bool GetMonitorInfo(IntPtr hMonitor, ref MONITORINFO lpmi);

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT { public int Left; public int Top; public int Right; public int Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    private struct MINMAXINFO
    {
        public POINT ptReserved;
        public POINT ptMaxSize;
        public POINT ptMaxPosition;
        public POINT ptMinTrackSize;
        public POINT ptMaxTrackSize;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MONITORINFO
    {
        public int cbSize;
        public RECT rcMonitor;
        public RECT rcWork;
        public int dwFlags;
    }
}
