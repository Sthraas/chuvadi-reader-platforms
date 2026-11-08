using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using Foundation;
using UIKit;
using Microsoft.Extensions.Logging;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// CI diagnostics, on only when the environment variable CHUVADI_SMOKE=1 (the Mac workflow's smoke run).
/// Prints "CHUVADI …" lines to stdout so the workflow can assert the Mac Test fixes on a real macOS runner:
/// open tabs (M-02), window and content geometry (M-04, M-07), the real AppKit menu bar (M-01, M-11) and
/// a breakdown of the time from WebView ready to Blazor's first render (M-06). Never on for a person.
/// </summary>
internal static class MacSmoke
{
    public static readonly bool Enabled = Environment.GetEnvironmentVariable("CHUVADI_SMOKE") == "1";

    public static void Log(string line)
    {
        if (Enabled)
        {
            Console.WriteLine("CHUVADI " + line);
        }
    }

    /// <summary>Called once the Ui has rendered.</summary>
    public static void Start(IServiceProvider services, WKWebView? view)
    {
        if (!Enabled)
        {
            return;
        }

        var tabs = services.GetRequiredService<TabsService>();
        var last = string.Empty;
        void ReportTabs()
        {
            var now = string.Join(", ", tabs.Tabs.Select(t => t.FileName));
            if (now == last)
            {
                return;
            }

            last = now;
            Log($"tabs {tabs.Tabs.Count}: {now}");
            Later(1.5, () =>
            {
                ReportMenu();
                if (view is not null)
                {
                    _ = UiStateAsync(view);
                }
            });
        }

        Log("dotnet-text " + new ObjectDisposedException("IServiceProvider").Message.Replace('\n', ' ')); // M-14
        tabs.Changed += () => UIApplication.SharedApplication.BeginInvokeOnMainThread(ReportTabs);
        ReportTabs();

        Later(1.0, () =>
        {
            var (window, screen, content) = AppKitBridge.Geometry(AppKitBridge.AppWindow());
            Log(FormattableString.Invariant(
                $"geometry window={window.Width:0}x{window.Height:0}@{window.X:0},{window.Y:0} screen={screen.Width:0}x{screen.Height:0}@{screen.X:0},{screen.Y:0} content={content.Width:0}x{content.Height:0}"));
            if (view is not null)
            {
                var inWindow = view.ConvertRectToView(view.Bounds, null);
                Log(FormattableString.Invariant($"webview top={inWindow.Y:0} height={inWindow.Height:0} uiwindow={view.Window?.Bounds.Height ?? 0:0}"));
                _ = TimingsAsync(view);
            }

            ReportMenu();
        });
    }

    private static void ReportMenu()
    {
        foreach (var line in AppKitBridge.DumpMainMenu())
        {
            Log("menu " + line);
        }
    }

    /// <summary>What the page shows (M-16): the route, whether the Reader rendered, and whether Blazor's
    /// "An error occurred" bar is showing.</summary>
    private static async Task UiStateAsync(WKWebView view)
    {
        const string script = """
            (function () {
              var e = document.getElementById('blazor-error-ui');
              return 'route=' + location.pathname + ' reader=' + (document.querySelector('.reader') ? 1 : 0)
                + ' errorbar=' + (e ? getComputedStyle(e).display : 'none');
            })()
            """;
        try
        {
            Log("ui " + (await view.EvaluateJavaScriptAsync(script))?.ToString());
        }
        catch (Exception ex)
        {
            Log("ui failed: " + ex.Message);
        }
    }

    private static void Later(double seconds, Action action)
        => NSTimer.CreateScheduledTimer(seconds, false, _ => action());

    /// <summary>
    /// Where the time between WebView ready and the Ui's ready signal goes (M-06), from the WebView's own
    /// performance timeline: page and resource loads, first paint and first content of #app (host page mark).
    /// All times are ms since process start, like the CHUVADI_STARTUP marks.
    /// </summary>
    private static async Task TimingsAsync(WKWebView view)
    {
        const string script = """
            (function () {
              var r = function (v) { return Math.round(v); };
              var nav = performance.getEntriesByType('navigation')[0] || {};
              var res = performance.getEntriesByType('resource').map(function (e) {
                return [e.name.split('?')[0].split('/').slice(-1)[0], r(e.startTime), r(e.responseEnd), e.initiatorType];
              });
              var marks = performance.getEntriesByType('mark').map(function (e) { return [e.name, r(e.startTime)]; });
              var paint = performance.getEntriesByType('paint').map(function (e) { return [e.name, r(e.startTime)]; });
              return JSON.stringify({ origin: performance.timeOrigin, responseEnd: r(nav.responseEnd || 0),
                dcl: r(nav.domContentLoadedEventEnd || 0), load: r(nav.loadEventEnd || 0), marks: marks, paint: paint, res: res });
            })()
            """;
        try
        {
            var result = await view.EvaluateJavaScriptAsync(script);
            var json = result?.ToString() ?? string.Empty;
            var processStart = new DateTimeOffset(Process.GetCurrentProcess().StartTime).ToUnixTimeMilliseconds();
            Log($"webtimings processStartEpochMs={processStart} {json}");
        }
        catch (Exception ex)
        {
            Log("webtimings failed: " + ex.Message);
        }
    }
}

/// <summary>Smoke runs only: warnings and errors from every logger (Blazor's unhandled exceptions among them) go to
/// stdout as "CHUVADI log …", so a Ui failure on the runner shows its exception (Mac Test M-16).</summary>
internal sealed class SmokeLoggerProvider : ILoggerProvider
{
    public ILogger CreateLogger(string categoryName) => new SmokeLogger(categoryName);

    public void Dispose()
    {
    }

    private sealed class SmokeLogger(string category) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => logLevel >= LogLevel.Warning;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            if (IsEnabled(logLevel))
            {
                MacSmoke.Log($"log {logLevel} {category}: {formatter(state, exception)} {exception}".Replace('\n', '⏎'));
            }
        }
    }
}
