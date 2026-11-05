using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;

namespace ChuvadiReader.Linux.Platform;

/// <summary>The HTML title bar's buttons and drag, against the GTK window.</summary>
public sealed class LinuxWindowControls : IWindowControls
{
    private volatile bool _maximized = true; // the window opens maximised, as on Windows

    public LinuxWindowControls()
    {
        GtkHost.MaximizedChanged += m =>
        {
            _maximized = m;
            StateChanged?.Invoke();
        };
    }

    public event Action? StateChanged;

    public bool IsMaximized => _maximized;

    public void Minimize() => GtkHost.Post(Native.Minimize);

    public void ToggleMaximize() => GtkHost.Post(Native.ToggleMaximize);

    public void Close() => GtkHost.Post(Native.Close);

    /// <summary>Hands the move to the compositor (works on X11 and Wayland); ignored while maximised.</summary>
    public void BeginDrag() => GtkHost.Post(Native.BeginMove);
}

/// <summary>Interface size as a zoom of the whole web view (WebKit zoom level), like WebView2's
/// ZoomFactor on Windows.</summary>
public sealed class LinuxUiScale : IUiScale
{
    public bool IsSupported => true;

    public void SetScale(int percent)
    {
        double factor = percent switch
        {
            125 => 1.25,
            150 => 1.5,
            _ => 1.0,
        };
        GtkHost.Post(() => Native.SetZoom(factor));
    }
}

/// <summary>Opens http, https and mailto links with the desktop's default handler (xdg-open,
/// part of every Ubuntu desktop).</summary>
public sealed class LinuxExternalLinks : IExternalLinks
{
    public bool IsAvailable => true;

    public Task<bool> OpenAsync(string url)
    {
        if (!IExternalLinks.IsAllowed(url))
        {
            return Task.FromResult(false);
        }

        try
        {
            var psi = new ProcessStartInfo("xdg-open") { UseShellExecute = false };
            psi.ArgumentList.Add(url);
            using var p = Process.Start(psi);
            return Task.FromResult(p is not null);
        }
        catch
        {
            return Task.FromResult(false);
        }
    }
}

/// <summary>Puts a PNG on the system clipboard (GdkClipboard; the desktop converts as needed).</summary>
public sealed class LinuxImageClipboard : IImageClipboard
{
    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return Task.CompletedTask;
        }

        return GtkHost.InvokeAsync(() =>
        {
            unsafe
            {
                fixed (byte* p = pngBytes)
                {
                    return Native.ClipboardSetPng(p, (nuint)pngBytes.Length);
                }
            }
        });
    }
}
