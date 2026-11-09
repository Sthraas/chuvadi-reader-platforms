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

    private static readonly Queue<string> Picks = new(
        (Environment.GetEnvironmentVariable("CHUVADI_SMOKE_PICK") ?? string.Empty)
            .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries));

    /// <summary>Smoke only: the next fixture file the Open panel "chooses" (CHUVADI_SMOKE_PICK, ';'-separated).</summary>
    public static string? NextPick() => Enabled && Picks.Count > 0 ? Picks.Dequeue() : null;

    private static readonly string[] Steps = (Environment.GetEnvironmentVariable("CHUVADI_SMOKE_STEPS") ?? string.Empty)
        .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

    /// <summary>
    /// Smoke only: walks CHUVADI_SMOKE_STEPS (';'-separated), 3 s apart, reporting the page after each as
    /// "step n name: route=… reader=… errorbar=…". Steps: "pick" (Open button → panel → next CHUVADI_SMOKE_PICK),
    /// "pw:text" (type into the unlock field and press Return — M-17), "click:Title" (the button whose title
    /// starts with Title — M-18), "mode:n" (the n-th mode button), "key:Name" (a synthetic page key) and
    /// "native:name" (a real key posted by the smoke script — M-21).
    /// </summary>
    private static void RunSteps(WKWebView view, int index = 0)
    {
        if (index >= Steps.Length)
        {
            Log("steps done");
            return;
        }

        var step = Steps[index];
        Later(3.0, async () =>
        {
            var colon = step.IndexOf(':');
            var kind = colon < 0 ? step : step[..colon];
            var arg = colon < 0 ? string.Empty : step[(colon + 1)..];
            if (kind == "native")
            {
                // The smoke script watches for this line and posts the real key (keys.swift), so the key travels
                // macOS → UIKit → WKWebView as a person's does (M-21). Recorded page keys show what arrived.
                Log("native-key " + arg);
                Later(4.0, async () =>
                {
                    Log($"step {index + 1} native: " + await UiTextAsync(view) + " sent=" + arg);
                    RunSteps(view, index + 1);
                });
                return;
            }

            var js = kind switch
            {
                "pick" => null,
                "jserror" => """
                    (function () {
                      console.error("smoke-page-error opening '/Users/someone/Documents/smoke-secret-name.pdf'\n   at Smoke.Page.Frame()");
                      return 'logged';
                    })()
                    """,
                "mode" => $$"""
                    (function () {
                      var b = document.querySelectorAll('button.lb-mode')[{{int.Parse(arg, System.Globalization.CultureInfo.InvariantCulture) - 1}}];
                      if (!b) { return 'no-mode-button'; } b.click(); return 'clicked ' + (b.getAttribute('title') || '');
                    })()
                    """,
                "pw" => $$"""
                    (function () {
                      var i = document.querySelector('input.uc-pw'); if (!i) { return 'no-password-field'; }
                      i.focus();
                      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, {{System.Text.Json.JsonSerializer.Serialize(arg)}});
                      i.dispatchEvent(new Event('input', { bubbles: true }));
                      setTimeout(function () {
                        i.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
                        i.form.requestSubmit();
                      }, 200);
                      return 'typed';
                    })()
                    """,
                "click" => $$"""
                    (function () {
                      var t = {{System.Text.Json.JsonSerializer.Serialize(arg)}};
                      var b = Array.prototype.find.call(document.querySelectorAll('button'), function (x) {
                        return (x.getAttribute('title') || x.getAttribute('aria-label') || '').indexOf(t) === 0; });
                      if (!b) { return 'no-button'; } b.click(); return 'clicked';
                    })()
                    """,
                "key" => $$"""
                    (function () {
                      var k = {{System.Text.Json.JsonSerializer.Serialize(arg)}};
                      var t = document.activeElement || document.body;
                      t.dispatchEvent(new KeyboardEvent('keydown', { key: k, code: k, bubbles: true, cancelable: true }));
                      t.dispatchEvent(new KeyboardEvent('keyup', { key: k, code: k, bubbles: true }));
                      return 'pressed';
                    })()
                    """,
                _ => "'unknown-step'",
            };
            if (js is null)
            {
                await PressOpenAsync(view);
            }
            else
            {
                try
                {
                    Log($"step {index + 1} {kind}: " + (await view.EvaluateJavaScriptAsync(js))?.ToString());
                }
                catch (Exception ex)
                {
                    Log($"step {index + 1} {kind} failed: " + ex.Message);
                }
            }

            Later(2.5, async () =>
            {
                Log($"step {index + 1} {step.Split(':')[0]}: " + await UiTextAsync(view));
                RunSteps(view, index + 1);
            });
        });
    }

    /// <summary>Smoke only: presses the left bar's Open button, as a person does (M-16).</summary>
    private static async Task PressOpenAsync(WKWebView view)
    {
        const string script = """
            (function () {
              var b = Array.prototype.find.call(document.querySelectorAll('button.lb-btn'),
                function (x) { return (x.getAttribute('title') || '').indexOf('Open') === 0; });
              if (!b) { return 'no-open-button'; }
              b.click(); return 'pressed';
            })()
            """;
        try
        {
            Log("open-button " + (await view.EvaluateJavaScriptAsync(script))?.ToString());
        }
        catch (Exception ex)
        {
            Log("open-button failed: " + ex.Message);
        }
    }

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
                    if (Picks.Count > 0 && Steps.Length == 0)
                    {
                        Later(1.0, () => _ = PressOpenAsync(view)); // next format through the Open panel
                    }
                }
            });
        }

        // D-132 check: a warning that carries a path, a file name and a quoted secret, and (CHUVADI_SMOKE_LOGFILL=1)
        // 1.3 MB of warnings so the log must roll over. The script reads ~/Library/Logs/Chuvadi afterwards.
        var logger = services.GetRequiredService<ILoggerFactory>().CreateLogger("ChuvadiReader.Mac.Smoke");
        if (Environment.GetEnvironmentVariable("CHUVADI_SMOKE_LOGFILL") == "1")
        {
            var filler = new string('x', 300);
            for (var i = 0; i < 4000; i++)
            {
                logger.LogWarning("smoke-fill {Index} {Filler}", i, filler);
            }
        }
        logger.LogWarning("smoke-check could not open '/Users/someone/Documents/smoke-secret-name.pdf' with password 'smoke-hunter2'");

        Log("dotnet-text " + new ObjectDisposedException("IServiceProvider").Message.Replace('\n', ' ')); // M-14
        tabs.Changed += () => UIApplication.SharedApplication.BeginInvokeOnMainThread(ReportTabs);
        ReportTabs();
        if (Steps.Length > 0 && view is not null)
        {
            RunSteps(view); // a scripted sequence (M-17, M-18, M-21)
        }
        else if (Picks.Count > 0 && view is not null)
        {
            Later(2.0, () => _ = PressOpenAsync(view)); // first file through the Open panel, from Home
        }

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
        Log("ui " + await UiTextAsync(view));
    }

    private const string UiScript = """
            (function () {
              if (!window.__chvdKeys) {
                window.__chvdKeys = [];
                window.addEventListener('keydown', function (k) {
                  window.__chvdKeys.push((k.ctrlKey ? '⌃' : '') + (k.metaKey ? '⌘' : '') + k.key);
                }, true);
              }
              var keys = window.__chvdKeys.splice(0).join(',');
              var e = document.getElementById('blazor-error-ui');
              return 'route=' + location.pathname + ' reader=' + (document.querySelector('.reader') ? 1 : 0)
                + ' errorbar=' + (e ? getComputedStyle(e).display : 'none')
                + ' unlock=' + (document.querySelector('.uc') ? 1 : 0)
                + ' immersive=' + (document.body.classList.contains('chvd-immersive') ? 1 : 0)
                + ' keys=[' + keys + ']' + (function () {
                  var f = document.querySelector('iframe.htv-frame');
                  if (!f) { return ''; }
                  var b = f.contentDocument && f.contentDocument.body;
                  return ' frame=' + (b && b.innerText.trim() ? JSON.stringify(b.innerText.trim().slice(0, 40)) : 'empty');
                })();
            })()
            """;

    private static async Task<string> UiTextAsync(WKWebView view)
    {
        try
        {
            return (await view.EvaluateJavaScriptAsync(UiScript))?.ToString() ?? string.Empty;
        }
        catch (Exception ex)
        {
            return "failed: " + ex.Message;
        }
    }

    private static void Later(double seconds, Action action)
        => NSTimer.CreateScheduledTimer(seconds, false, _ => action());

    private static void Later(double seconds, Func<Task> action)
        => NSTimer.CreateScheduledTimer(seconds, false, timer => _ = action());

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
