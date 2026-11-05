using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;
using Foundation;
using UIKit;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>macOS locations the host owns.</summary>
internal static class MacPaths
{
    /// <summary>~/Library/Application Support/Chuvadi, asked of the OS (NSFileManager).</summary>
    public static string AppSupportDirectory
    {
        get
        {
            var urls = NSFileManager.DefaultManager.GetUrls(NSSearchPathDirectory.ApplicationSupportDirectory, NSSearchPathDomain.User);
            var root = urls.Length > 0 && !string.IsNullOrEmpty(urls[0].Path)
                ? urls[0].Path!
                : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library", "Application Support");
            var dir = Path.Combine(root, "Chuvadi");
            Directory.CreateDirectory(dir);
            return dir;
        }
    }

    /// <summary>~/Library/Logs/Chuvadi — where the startup error log and timings go.</summary>
    public static string LogDirectory
    {
        get
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library", "Logs", "Chuvadi");
            Directory.CreateDirectory(dir);
            return dir;
        }
    }
}

/// <summary>Puts a PNG on the macOS pasteboard (as image data, like the Windows clipboard).</summary>
public sealed class MacImageClipboard : IImageClipboard
{
    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return Task.CompletedTask;
        }

        UIApplication.SharedApplication.InvokeOnMainThread(() =>
        {
            try
            {
                using var data = NSData.FromArray(pngBytes);
                // Raw PNG bytes under public.png keep the image lossless and exact.
                UIPasteboard.General.SetData(data, UniformTypeIdentifiers.UTTypes.Png.Identifier);
            }
            catch
            {
                // Matches the Windows host: a failed copy is ignored, never fatal.
            }
        });

        return Task.CompletedTask;
    }
}

/// <summary>Opens http, https and mailto links in the default browser / mail app.</summary>
public sealed class MacExternalLinks : IExternalLinks
{
    public bool IsAvailable => true;

    public Task<bool> OpenAsync(string url)
    {
        if (!IExternalLinks.IsAllowed(url))
        {
            return Task.FromResult(false);
        }

        var tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            try
            {
                var nsUrl = NSUrl.FromString(url);
                if (nsUrl is null)
                {
                    tcs.TrySetResult(false);
                    return;
                }

                UIApplication.SharedApplication.OpenUrl(nsUrl, new UIApplicationOpenUrlOptions(), ok => tcs.TrySetResult(ok));
            }
            catch
            {
                tcs.TrySetResult(false);
            }
        });
        return tcs.Task;
    }
}

/// <summary>Interface size as a whole-WKWebView zoom (pageZoom), matching the Windows host's
/// WebView2 ZoomFactor. The person's own pinch zoom of the page stays off.</summary>
public sealed class MacUiScale : IUiScale
{
    private readonly MacWindowControls _window;
    private WKWebView? _view;
    private double _factor = 1.0;

    public MacUiScale(MacWindowControls window) => _window = window;

    public bool IsSupported => true;

    /// <summary>Called once the WKWebView exists; applies any scale set before then.</summary>
    public void Attach(WKWebView view)
    {
        _view = view;
        Apply();
    }

    public void SetScale(int percent)
    {
        _factor = percent switch
        {
            125 => 1.25,
            150 => 1.5,
            _ => 1.0,
        };
        _window.SetScale(_factor);
        Apply();
    }

    private void Apply()
    {
        var view = _view;
        if (view is null)
        {
            return;
        }

        var factor = (nfloat)_factor;
        void Set()
        {
            try
            {
                if (Math.Abs(view.PageZoom - factor) > 0.001)
                {
                    view.PageZoom = factor;
                }
            }
            catch
            {
                // the view may be closing; the next launch applies the stored value
            }
        }

        if (NSThread.IsMain)
        {
            Set();
        }
        else
        {
            UIApplication.SharedApplication.BeginInvokeOnMainThread(Set);
        }
    }
}

/// <summary>
/// Startup timings: process start → MAUI built → window → WebView ready → first Blazor render.
/// Written to ~/Library/Logs/Chuvadi/startup.log and to stdout (picked up by the CI smoke run).
/// </summary>
internal static class StartupTimeline
{
    private static readonly object Gate = new();
    private static readonly List<(string Stage, double Ms)> Marks = new();

    public static void Mark(string stage)
    {
        var ms = (DateTime.Now - Process.GetCurrentProcess().StartTime).TotalMilliseconds;
        lock (Gate)
        {
            Marks.Add((stage, ms));
        }

        Console.WriteLine($"CHUVADI_STARTUP {stage} {ms:F0}ms");
    }

    public static void Flush()
    {
        try
        {
            string text;
            lock (Gate)
            {
                text = DateTimeOffset.Now.ToString("u") + Environment.NewLine
                    + string.Join(Environment.NewLine, Marks.Select(m => $"{m.Stage,-14} {m.Ms,8:F0} ms"))
                    + Environment.NewLine;
            }

            File.AppendAllText(Path.Combine(MacPaths.LogDirectory, "startup.log"), text + Environment.NewLine);
        }
        catch
        {
            // timing must never affect the app
        }
    }
}
