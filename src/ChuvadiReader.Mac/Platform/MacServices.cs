using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Platform;
using Foundation;
using UIKit;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>macOS folders (IAppPaths), asked of the OS. The kit's desktop default uses
/// OperatingSystem.IsMacOS(), which is false under Mac Catalyst, so the Mac host provides its own.</summary>
public sealed class MacAppPaths : IAppPaths
{
    public MacAppPaths()
    {
        AppDataFolder = Path.Combine(SystemFolder(NSSearchPathDirectory.ApplicationSupportDirectory, "Library/Application Support"), "Chuvadi");
        Directory.CreateDirectory(AppDataFolder);
        WorkingFolder = Path.GetTempPath();
        DefaultSaveFolder = SystemFolder(NSSearchPathDirectory.DocumentDirectory, "Documents");
    }

    /// <summary>~/Library/Application Support/Chuvadi.</summary>
    public string AppDataFolder { get; }

    public string WorkingFolder { get; }

    /// <summary>~/Documents.</summary>
    public string? DefaultSaveFolder { get; }

    /// <summary>~/Library/Logs/Chuvadi — the startup timings.</summary>
    public static string LogDirectory
    {
        get
        {
            var dir = Path.Combine(SystemFolder(NSSearchPathDirectory.LibraryDirectory, "Library"), "Logs", "Chuvadi");
            Directory.CreateDirectory(dir);
            return dir;
        }
    }

    private static string SystemFolder(NSSearchPathDirectory kind, string fallbackUnderHome)
    {
        var urls = NSFileManager.DefaultManager.GetUrls(kind, NSSearchPathDomain.User);
        return urls.Length > 0 && !string.IsNullOrEmpty(urls[0].Path)
            ? urls[0].Path!
            : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), fallbackUnderHome);
    }
}

/// <summary>The macOS pasteboard: text, and PNG images as image data (as the Windows clipboard does).</summary>
public sealed class MacClipboard : IClipboard, IImageClipboard
{
    public bool CanCopyText => true;

    public bool CanCopyImage => true;

    public Task SetTextAsync(string text, CancellationToken ct = default)
        => OnMain(() => UIPasteboard.General.String = text ?? string.Empty);

    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return Task.CompletedTask;
        }

        // Raw PNG bytes under public.png keep the image lossless and exact.
        return OnMain(() =>
        {
            using var data = NSData.FromArray(pngBytes);
            UIPasteboard.General.SetData(data, UniformTypeIdentifiers.UTTypes.Png.Identifier);
        });
    }

    private static Task OnMain(Action action)
    {
        var tcs = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            try
            {
                action();
                tcs.SetResult();
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        });
        return tcs.Task;
    }
}

/// <summary>"Show in folder": reveals and selects the file in Finder.</summary>
public sealed class MacFileManager : IFileManager
{
    public bool IsAvailable => true;

    public Task<bool> RevealAsync(string localPath, CancellationToken ct = default)
    {
        if (string.IsNullOrEmpty(localPath) || !(File.Exists(localPath) || Directory.Exists(localPath)))
        {
            return Task.FromResult(false);
        }

        var tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        UIApplication.SharedApplication.BeginInvokeOnMainThread(() => tcs.TrySetResult(AppKitBridge.RevealInFinder(localPath)));
        return tcs.Task;
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
    private WKWebView? _view;
    private double _factor = 1.0;

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

            File.AppendAllText(Path.Combine(MacAppPaths.LogDirectory, "startup.log"), text + Environment.NewLine);
        }
        catch
        {
            // timing must never affect the app
        }
    }
}
