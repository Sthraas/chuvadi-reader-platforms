using System.Globalization;
using global::Android.OS;
using AWebView = global::Android.Webkit.WebView;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// AT-14: where a cold "Open with" spends its time, from the process starting to page 1 painted.
/// The host stamps its own stages as they happen (a few numbers in memory, always — too cheap to
/// matter); only when the launch asks for it (intent extra <c>chuvadi.timing</c> = true, set by the
/// test scripts) does it watch the page and write the timeline to the log, tag <c>ChuvadiTiming</c>,
/// in milliseconds since the process started:
/// <code>
///   process 0 · runtime · maui · activity · import-start · import-done · handed · webview · webview-ready
///   · html (DOMContentLoaded) · ui (Blazor's first UI) · reader (the Reader's route) · loading (its
///   "Opening &lt;name&gt;…" line: the tab exists, the document is being read) · opening (the Reader shows the
///   document's pages) · painted (page 1's drawing is on the page)
/// </code>
/// Page stages are read from the page every 25 ms (EvaluateJavascript, so it works on the Release
/// build, which has no DevTools), so they are good to ±25 ms. Nothing is ever sent anywhere.
/// </summary>
public static class StartupTimeline
{
    public const string Extra = "chuvadi.timing";
    private const string Tag = "ChuvadiTiming";

    // epoch ms of the process start: now minus how long the process has been running.
    private static readonly long ProcessStart = Java.Lang.JavaSystem.CurrentTimeMillis()
        - (SystemClock.ElapsedRealtime() - global::Android.OS.Process.StartElapsedRealtime);

    private static readonly List<(string Stage, long Epoch)> Marks = [];
    private static bool _enabled;
    private static bool _watching;

    /// <summary>Stamp a host stage (first time only).</summary>
    public static void Mark(string stage)
    {
        var now = Java.Lang.JavaSystem.CurrentTimeMillis();
        lock (Marks)
        {
            if (Marks.Exists(m => m.Stage == stage))
            {
                return;
            }

            Marks.Add((stage, now));
        }

        if (_enabled)
        {
            Write(stage, now);
        }
    }

    /// <summary>The launch intent asked for the timeline: write what's stamped so far, and from now on.</summary>
    public static void EnableIf(global::Android.Content.Intent? intent)
    {
        if (_enabled || intent?.GetBooleanExtra(Extra, false) != true)
        {
            return;
        }

        _enabled = true;
        global::Android.Util.Log.Info(Tag, "process 0");
        lock (Marks)
        {
            foreach (var (stage, epoch) in Marks)
            {
                Write(stage, epoch);
            }
        }
    }

    /// <summary>Watch the page for its stages (after the WebView is ready; only when enabled).</summary>
    public static void Watch(AWebView web)
    {
        if (!_enabled || _watching)
        {
            return;
        }

        _watching = true;
        var handler = new Handler(Looper.MainLooper!);
        var deadline = SystemClock.ElapsedRealtime() + 60_000;
        var seen = new HashSet<string>();

        void Poll()
        {
            web.EvaluateJavascript(PageProbe, new Callback(value =>
            {
                var now = Java.Lang.JavaSystem.CurrentTimeMillis();
                var parts = (value ?? string.Empty).Trim('"', '[', ']').Split(',');
                if (parts.Length == 6)
                {
                    if (long.TryParse(parts[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out var html) && html > 0 && seen.Add("html"))
                    {
                        Write("html", html);
                    }

                    if (parts[1] == "1" && seen.Add("ui")) Write("ui", now);
                    if (parts[2] == "1" && seen.Add("reader")) Write("reader", now);
                    if (parts[3] == "1" && seen.Add("loading")) Write("loading", now);
                    if (parts[4] == "1" && seen.Add("opening")) Write("opening", now);
                    if (parts[5] == "1" && seen.Add("painted")) Write("painted", now);
                }

                if (!seen.Contains("painted") && SystemClock.ElapsedRealtime() < deadline)
                {
                    handler.PostDelayed(Poll, 25);
                }
                else
                {
                    global::Android.Util.Log.Info(Tag, seen.Contains("painted") ? "done" : "gave up after 60 s");
                }
            }));
        }

        handler.Post(Poll);
    }

    // [DOMContentLoaded epoch, Blazor UI present, on the Reader's route, "Opening …" shown, Reader pages present, page 1 drawn]
    private const string PageProbe = """
        (function(){var t=performance.timing,a=document.getElementById('app');
        return [t.domContentLoadedEventEnd||0,
          a&&a.children.length&&!document.getElementById('blazor-error-ui')?.offsetParent?1:0,
          location.pathname==='/reader'?1:0,
          [...document.querySelectorAll('.rempty-t')].some(e=>/^Opening /.test(e.textContent))?1:0,
          document.querySelector('.rpage-wrap')?1:0,
          document.querySelector('.rpage-wrap .rpage svg')?1:0].join(',');})()
        """;

    private static void Write(string stage, long epoch)
        => global::Android.Util.Log.Info(Tag, $"{stage} {epoch - ProcessStart}");

    private sealed class Callback(Action<string?> done) : Java.Lang.Object, global::Android.Webkit.IValueCallback
    {
        public void OnReceiveValue(Java.Lang.Object? value) => done(value?.ToString());
    }
}
