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
    /// "pw:text" (put text in the unlock field, then a real Return — M-17), "click:Title" (the button whose title
    /// starts with Title — M-18), "mode:n" (the n-th mode button), "key:Name" (a synthetic page key) and
    /// "native:name" (a real key posted by the smoke script — M-21).
    /// </summary>
    /// <summary>The page's WebView now — a new one after WebKit's content process ended and the page reopened.</summary>
    private static WKWebView Current(WKWebView fallback) => ChuvadiReader.Mac.MainPage.WebKitView ?? fallback;

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
            if (kind == "pinch")
            {
                // The page half of a trackpad pinch: one 1.5× step at the middle of the page area (the gesture itself
                // needs a real trackpad — REAL-MAC-CHECKS).
                var v = Current(view);
                var mid = new CoreGraphics.CGPoint(v.Bounds.Width / 2, v.Bounds.Height / 2);
                MacPinch.Send(v, "begin", 1, mid);
                MacPinch.Send(v, "change", double.Parse(arg, System.Globalization.CultureInfo.InvariantCulture), mid);
                MacPinch.Send(v, "end", 1, mid);
                Later(2.0, async () =>
                {
                    Log($"step {index + 1} pinch: " + await UiTextAsync(Current(view)));
                    RunSteps(view, index + 1);
                });
                return;
            }

            if (kind == "cmd")
            {
                // A command by its label, as the menu bar invokes it (e.g. "Mark: Rectangle").
                var commands = _services!.GetRequiredService<ChuvadiReader.Platform.IAppCommands>();
                var info = commands.Commands.FirstOrDefault(c => c.Label == arg);
                Log($"step {index + 1} cmd: {arg} → {(info is null ? "no such command" : info.Id + (info.IsEnabled ? "" : " (disabled)"))}");
                if (info is not null)
                {
                    ChuvadiReader.Mac.MainPage.Dispatch(() => commands.InvokeAsync(info.Id));
                }

                Later(2.5, async () =>
                {
                    Log($"step {index + 1} cmd: " + await UiTextAsync(Current(view)));
                    RunSteps(view, index + 1);
                });
                return;
            }

            if (kind == "closewindow")
            {
                // D-190: the Ui's own red button — IWindowControls.Close, AppKit's performClose:.
                _services!.GetRequiredService<ChuvadiReader.Core.Window.IWindowControls>().Close();
                Later(2.5, async () =>
                {
                    Log($"step {index + 1} closewindow: " + await UiTextAsync(Current(view)));
                    RunSteps(view, index + 1);
                });
                return;
            }

            if (kind == "unfocus")
            {
                // M-08 / M-23: the state Mac Test saw — the window has no first responder (focus on its content group).
                var resigned = Current(view).ResignFirstResponder();
                Log($"step {index + 1} unfocus: resigned={resigned} first={Current(view).IsFirstResponder}");
                Later(2.0, async () =>
                {
                    Log($"step {index + 1} unfocus: " + await UiTextAsync(Current(view)));
                    RunSteps(view, index + 1);
                });
                return;
            }

            if (kind == "native")
            {
                // The smoke script watches for this line and posts the real key (keys.swift), so the key travels
                // macOS → UIKit → WKWebView as a person's does (M-21). Recorded page keys show what arrived.
                Log("responders " + Responders());
                Log("native-key " + arg);
                // Report 2 s after the key's effect was logged (a slow runner posts the key seconds late, and the Ui
                // needs a moment to show the result), or after 10 s if nothing came of it.
                var asked = DateTime.UtcNow;
                void Check()
                {
                    var now = DateTime.UtcNow;
                    var seen = _lastKeyAt > asked;
                    if ((seen && now - _lastKeyAt >= TimeSpan.FromSeconds(2)) || now - asked >= TimeSpan.FromSeconds(seen ? 14 : 10))
                    {
                        _ = Report();
                        return;
                    }

                    Later(0.5, Check);
                }

                async Task Report()
                {
                    Log($"step {index + 1} native: " + await UiTextAsync(Current(view)) + " sent=" + arg);
                    RunSteps(view, index + 1);
                }

                Later(4.0, Check);
                return;
            }

            var js = kind switch
            {
                "pick" => null,
                "wait" => "'waited'",
                // M-27: drag a mark with the pointer inside the page and say where the shape landed. The drag is
                // 120×80 px from 60 px inside the visible page's top-left; the shape's place comes from its own
                // left/top/width/height (fractions of the page layer), against where the pointer was in the layer.
                // The layer's true box on screen: WebKit reports a box inside a CSS-zoomed page in the page's own
                // (unzoomed) pixels, Chromium as shown — a 100 px probe says which ("rects=").
                "markdrag" => """
                    (function () {
                      var layer = document.querySelector('.mk-layer.drawmode') || document.querySelector('.mk-layer');
                      var desk = document.querySelector('.rdesk');
                      if (!layer || !desk) { return 'no-layer'; }
                      var z = 1; for (var n = layer; n && n.nodeType === 1; n = n.parentElement) { z *= parseFloat(getComputedStyle(n).zoom) || 1; }
                      var probe = document.createElement('div');
                      probe.style.cssText = 'position:absolute;left:0;top:0;width:100px;height:100px;visibility:hidden;pointer-events:none';
                      layer.appendChild(probe);
                      var pr = probe.getBoundingClientRect(), w = Math.max(pr.width, pr.height); probe.remove();
                      var shown = Math.abs(w - 100 * z) <= Math.abs(w - 100), k = shown ? 1 : z;
                      var r = layer.getBoundingClientRect();
                      var L = r.left * k, T = r.top * k, W = r.width * k, H = r.height * k;   // the layer as shown
                      var d = desk.getBoundingClientRect();
                      var ax = Math.max(L, d.left) + 60, ay = Math.max(T, d.top) + 60, bx = ax + 120, by = ay + 80;
                      var fire = function (type, x, y, buttons) {
                        var el = document.elementFromPoint(x, y) || layer;
                        el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, button: 0, buttons: buttons, pointerId: 7,
                          pointerType: 'mouse', isPrimary: true, bubbles: true, cancelable: true }));
                      };
                      fire('pointerdown', ax, ay, 1);
                      setTimeout(function () { fire('pointermove', (ax + bx) / 2, (ay + by) / 2, 1); }, 250);
                      setTimeout(function () { fire('pointermove', bx, by, 1); }, 500);
                      setTimeout(function () { fire('pointerup', bx, by, 0); }, 750);
                      window.__chvdMark = { ax: ax, ay: ay, bx: bx, by: by, L: L, T: T, W: W, H: H, z: z, rects: shown ? 'shown' : 'unzoomed' };
                      return 'dragging z=' + z.toFixed(3) + ' rects=' + window.__chvdMark.rects;
                    })()
                    """,
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
                      return 'typed';
                    })()
                    """,
                "click" => $$"""
                    (function () {
                      var t = {{System.Text.Json.JsonSerializer.Serialize(arg)}};
                      var b = Array.prototype.find.call(document.querySelectorAll('button'), function (x) {
                        return (x.getAttribute('title') || x.getAttribute('aria-label') || x.textContent.trim()).indexOf(t) === 0; });
                      if (!b) { return 'no-button'; } b.click(); return 'clicked';
                    })()
                    """,
                "closeq" => $$"""
                    (function () {   // D-190: a button of the question before closing, by its words
                      var t = {{System.Text.Json.JsonSerializer.Serialize(arg)}};
                      var b = Array.prototype.find.call(document.querySelectorAll('.closeq button'), function (x) {
                        return x.textContent.trim().indexOf(t) === 0; });
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
                await PressOpenAsync(Current(view));
            }
            else
            {
                try
                {
                    Log($"step {index + 1} {kind}: " + (await Current(view).EvaluateJavaScriptAsync(js))?.ToString());
                }
                catch (Exception ex)
                {
                    Log($"step {index + 1} {kind} failed: " + ex.Message);
                }

                if (kind == "pw")
                {
                    Log("native-key return"); // the password is submitted with a real Return, as a person does
                }
            }

            Later(kind == "pw" ? 4.0 : 2.5, async () =>
            {
                Log($"step {index + 1} {step.Split(':')[0]}: " + await UiTextAsync(Current(view)));
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

    private static DateTime _lastKeyAt; // when a real key last had an effect the host saw (page key or menu command)

    public static void Log(string line)
    {
        if (Enabled)
        {
            if (line.StartsWith("page-key ", StringComparison.Ordinal) || line.StartsWith("menu-command ", StringComparison.Ordinal))
            {
                _lastKeyAt = DateTime.UtcNow;
            }

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
        _tabs = tabs;
        _services = services;
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
            if (view is not null)
            {
                // A raster page (D-158, large-format) takes seconds to draw: report the page again later.
                Later(9.0, async () => Log("ui-late " + await UiTextAsync(Current(view))));
                Later(30.0, async () => Log("ui-later " + await UiTextAsync(Current(view))));
            }

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

        // M-26 check (CHUVADI_SMOKE_PRINTFIT=<pdf>): the print PDF's first page drawn as the print renderer draws it.
        if (Environment.GetEnvironmentVariable("CHUVADI_SMOKE_PRINTFIT") is { Length: > 0 } printFile)
        {
            _ = Task.Run(async () =>
            {
                try
                {
                    var doc = await PrintDocumentBuilder.BuildAsync(printFile, new PrintRequest()).ConfigureAwait(false);
                    UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
                    {
                        try
                        {
                            Log($"printfit landscape={(doc.Landscape ? 1 : 0)} " + MacPdfPageRenderer.Probe(doc.Pdf, doc.Landscape, true));
                        }
                        catch (Exception ex)
                        {
                            Log("printfit failed: " + ex.Message);
                        }
                    });
                }
                catch (Exception ex)
                {
                    Log("printfit failed: " + ex.Message);
                }
            });
        }

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
              return 'route=' + location.pathname + ' closeq=' + (document.querySelector('.closeq') ? 1 : 0) + ' reader=' + (document.querySelector('.reader') ? 1 : 0)
                + ' errorbar=' + (e ? getComputedStyle(e).display : 'none')
                + ' unlock=' + (document.querySelector('.uc') ? 1 : 0)
                + ' immersive=' + (document.body.classList.contains('chvd-immersive') ? 1 : 0)
                + ' keys=[' + keys + ']'
                + ' notice=' + (document.body && document.body.innerText.indexOf('stopped unexpectedly') >= 0 ? 1 : 0)
                + (function () {   // D-158: a raster page's image is served by address from memory (page-image hook)
                  var html = document.body ? document.body.innerHTML : '';
                  var m = html.match(/_chvd\/pages\/[0-9a-f]{32}\.png/);
                  if (!m) {
                    // diagnosis: where the page went — inline base64, an <img> source, or not drawn yet
                    var imgs = Array.prototype.map.call(document.querySelectorAll('.reader img, .reader image, .reader object'),
                      function (e) { return (e.tagName + ':' + (e.getAttribute('src') || e.getAttribute('href') || e.getAttribute('data') || '')).slice(0, 48); });
                    return document.querySelector('.reader') ? ' pageimg=none inline=' + (html.indexOf('data:image/png') >= 0 ? 1 : 0)
                      + ' svgs=' + document.querySelectorAll('.reader svg').length + ' imgs=' + JSON.stringify(imgs.slice(0, 3)) : '';
                  }
                  var href = m[0];
                  try {
                    var x = new XMLHttpRequest(); x.open('GET', href, false); x.send();
                    return ' pageimg=' + x.status + '/' + (x.getResponseHeader('content-type') || '?') + '/' + (x.responseText || '').length;
                  } catch (err) { return ' pageimg=error:' + err.message; }
                })()
                + (function () {   // M-27: where the last dragged mark landed, against the pointer (px on screen)
                  var m = window.__chvdMark; if (!m) { return ''; }
                  var shapes = document.querySelectorAll('.mk-shape.rect:not(.draft)');
                  var s = shapes[shapes.length - 1]; if (!s) { return ' mark=none rects=' + m.rects; }
                  var pct = function (v) { return parseFloat(v) / 100; };
                  var sx = m.L + pct(s.style.left) * m.W, sy = m.T + pct(s.style.top) * m.H;
                  var sw = pct(s.style.width) * m.W, sh = pct(s.style.height) * m.H;
                  var err = Math.max(Math.abs(sx - m.ax), Math.abs(sy - m.ay), Math.abs(sx + sw - m.bx), Math.abs(sy + sh - m.by));
                  return ' mark=' + Math.round(sx) + ',' + Math.round(sy) + '+' + Math.round(sw) + 'x' + Math.round(sh)
                    + ' pointer=' + Math.round(m.ax) + ',' + Math.round(m.ay) + '+120x80 markerr=' + Math.round(err) + ' rects=' + m.rects;
                })()
                + (function () {   // M-28: the Find bar
                  return ' find=' + (document.querySelector('.rfind, .rfind-box, input[placeholder^="Find"]') ? 1 : 0);
                })()
                + (function () {   // the page zoom as the page holds it
                  var d = document.querySelector('.rdesk');
                  return d ? ' zoom=' + (parseFloat(getComputedStyle(d).getPropertyValue('--rpage-zoom')) || 1).toFixed(3) : '';
                })()
                + (function () {   // M-08 / M-23: the tab strip as shown — the active tab and the first tab
                  var a = document.querySelector('.rtab.active'), f = document.querySelector('.rtab');
                  var t = function (e) { return e ? JSON.stringify(e.textContent.replace(/\s+/g, ' ').trim().slice(0, 40)) : '-'; };
                  var order = Array.prototype.map.call(document.querySelectorAll('.rtab'), function (e) {
                    return e.textContent.replace(/\s+/g, ' ').trim().slice(0, 40); }).join('|');
                  return ' strip=' + t(a) + ' strip1=' + t(f) + ' order=' + JSON.stringify(order);
                })()
                + (function () {   // M-09: the View rail's Immersive label as the page shows it
                  var b = document.querySelector('button[aria-label="Immersive"]');
                  return b ? ' immersiveTip=' + JSON.stringify(b.getAttribute('title') || '') : '';
                })()
                + (function () {   // M-14: a .NET message shown by the Ui, as text or as a resource key
                  var t = document.body ? document.body.textContent : '';   // the message sits under a closed "Details"
                  return /Access to the path/.test(t) ? ' dotnet=text' : /UnauthorizedAccess_|IO_|_Generic\b/.test(t) ? ' dotnet=key' : '';
                })() + (function () {
                  var f = document.querySelector('iframe.htv-frame');
                  if (!f) { return ''; }
                  var b = f.contentDocument && f.contentDocument.body;
                  return ' frame=' + (b && b.innerText.trim() ? JSON.stringify(b.innerText.trim().slice(0, 40)) : 'empty');
                })() + (function () {
                  // Where the keyboard is, and the last keydowns the page itself received (^ Control, @ Command,
                  // $ Shift; a trailing ! marks one the host sent, not the keyboard): tells a key the page got from
                  // one that never arrived.
                  if (!window.__chvdRaw) {
                    window.__chvdRaw = [];
                    window.addEventListener('keydown', function (e) {
                      window.__chvdRaw.push((e.ctrlKey ? '^' : '') + (e.metaKey ? '@' : '') + (e.shiftKey ? '$' : '') + e.key
                        + '>' + (e.target && e.target.tagName || '?') + (e.isTrusted ? '' : '!'));
                      if (window.__chvdRaw.length > 6) { window.__chvdRaw.shift(); }
                    }, true);
                  }
                  var a = document.activeElement;
                  return ' focus=' + (a ? a.tagName + (a.type ? ':' + a.type : '') : '-') + ' docfocus=' + (document.hasFocus() ? 1 : 0)
                    + ' raw=[' + window.__chvdRaw.join(',') + ']';
                })();
            })()
            """;

    private static TabsService? _tabs;
    private static IServiceProvider? _services;

    private static async Task<string> UiTextAsync(WKWebView view)
    {
        try
        {
            var page = (await view.EvaluateJavaScriptAsync(UiScript))?.ToString() ?? string.Empty;
            return page + " active=" + (_tabs?.Active?.FileName ?? "-"); // M-08 / M-23: which tab is active
        }
        catch (Exception ex)
        {
            return "failed: " + ex.Message;
        }
    }

    /// <summary>Which window is key and which view holds the keyboard, in every window of the app.</summary>
    internal static string Responders()
    {
        try
        {
            var parts = new List<string>();
            foreach (var scene in UIApplication.SharedApplication.ConnectedScenes.OfType<UIWindowScene>())
            {
                foreach (var window in scene.Windows)
                {
                    var first = FirstIn(window);
                    parts.Add(window.GetType().Name + (window.IsKeyWindow ? "*" : string.Empty) + (window.Hidden ? "(hidden)" : string.Empty)
                        + ":" + (first is null ? "-" : first.Class.Name));
                }
            }

            return string.Join(" ", parts);
        }
        catch (Exception ex)
        {
            return "failed " + ex.GetType().Name;
        }

        static UIView? FirstIn(UIView view)
        {
            if (view.IsFirstResponder)
            {
                return view;
            }

            foreach (var child in view.Subviews)
            {
                if (FirstIn(child) is { } found)
                {
                    return found;
                }
            }

            return null;
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
