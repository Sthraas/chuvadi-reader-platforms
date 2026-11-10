#!/usr/bin/env python3
"""Cold Open-with timeline (test tooling only), on the trace build (trace-patch.py markers).
All times: device-clock ms after ActivityTaskManager's "START u0" for the VIEW intent.
Sources: logcat -v epoch (system lines + "ATT" markers from the app), the page's own clock
(Navigation/Resource/Paint timing, read afterwards) and an in-page probe (DOM milestones, then rAF).

    trace.py <out-dir> <pdf> [runs=10]
"""
import json
import os
import re
import statistics
import sys
import threading
import time

from lib import Cdp, PKG, adb, open_with, push_media, sh

OUT, PDF = sys.argv[1], sys.argv[2]
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 10
os.makedirs(OUT, exist_ok=True)
cdp = Cdp()
uri = push_media(PDF, "trace-doc.pdf")

PROBE = r"""new Promise(res => { const t0 = Date.now(); const got = {};
  const conds = { app_root_rendered: () => { const a = document.getElementById('app'); return a && a.children.length > 0 && document.body.innerText.trim().length > 20; },
                  reader_page_boxes: () => document.querySelector('.rpage-wrap') !== null,
                  page1_svg_in_dom: () => document.querySelector('.rpage-wrap .rpage svg') !== null };
  const already = Object.fromEntries(Object.entries(conds).map(([k, f]) => [k, !!f()]));
  (function poll() { const now = Date.now();
    for (const [k, f] of Object.entries(conds)) if (!(k in got) && f()) got[k] = now;
    if ('page1_svg_in_dom' in got) requestAnimationFrame(() => requestAnimationFrame(() => { got.page1_painted = Date.now(); res({got, already, injected: t0}); }));
    else if (now - t0 > 60000) res({got, already, injected: t0}); else setTimeout(poll, 8); })(); })"""

PERF = r"""(() => { const o = performance.timeOrigin; const n = performance.getEntriesByType('navigation')[0] || {};
  const r = performance.getEntriesByType('resource').map(e => ({name: e.name.split('/').slice(-1)[0], start: o + e.startTime, end: o + e.responseEnd}));
  const p = performance.getEntriesByType('paint').map(e => ({name: e.name, t: o + e.startTime}));
  return { timeOrigin: o, fetchStart: o + (n.fetchStart || 0), responseEnd: o + (n.responseEnd || 0),
           domContentLoaded: o + (n.domContentLoadedEventEnd || 0), load: o + (n.loadEventEnd || 0), resources: r, paint: p }; })()"""


def log_lines():
    return adb("logcat", "-d", "-v", "epoch").splitlines()


def epoch(line):
    try:
        return float(line.split()[0]) * 1000
    except (ValueError, IndexError):
        return None


rows = []
for i in range(RUNS + 1):  # first run discarded (post-install effects)
    sh(f"am force-stop {PKG}")
    sh("sync; echo 3 > /proc/sys/vm/drop_caches")
    time.sleep(1)
    adb("logcat", "-c")
    time.sleep(0.3)
    box = {}
    th = threading.Thread(target=lambda: box.update(out=open_with(uri, wait=True)))
    th.start()
    time.sleep(0.05)
    probe = None
    try:
        cdp.close()
        cdp.connect(60)
        probe = cdp.js(PROBE)
        perf = cdp.js(PERF)
    except Exception as e:
        perf = {"error": str(e)}
    th.join()
    time.sleep(1.5)
    lines = log_lines()
    t0 = next((epoch(l) for l in lines if "START u0" in l and PKG in l), None)
    m = {}
    for l in lines:
        t = epoch(l)
        if t is None:
            continue
        if "Start proc" in l and PKG in l:
            m.setdefault("process_start", t)
        elif "Opened from another app" in l:
            m.setdefault("host_import_copied", t)
        elif "WebViewFactory" in l and "Loading" in l:
            m.setdefault("webview_provider_load", t)
        elif "Displayed " + PKG in l or ("Displayed" in l and PKG in l):
            m.setdefault("android_first_frame_logged", t)
        mm = re.search(r"ATT (\S+)", l)
        if mm:
            m.setdefault(mm.group(1), t)
    if isinstance(perf, dict) and "timeOrigin" in perf:
        m["webview_navigation_start"] = perf["timeOrigin"]
        m["host_page_loaded (responseEnd)"] = perf["responseEnd"]
        m["dom_content_loaded"] = perf["domContentLoaded"]
        for r in perf["resources"]:
            if r["name"].startswith("blazor.webview"):
                m["blazor_js_loaded"] = r["end"]
        for p in perf["paint"]:
            m[p["name"]] = p["t"]
    if probe:
        for k, v in probe["got"].items():
            m[k] = v
        m["_probe_injected"] = probe["injected"]
        m["_already_true"] = [k for k, v in probe["already"].items() if v]
    rel = {k: (round(v - t0) if isinstance(v, (int, float)) and t0 else v) for k, v in m.items()}
    rel["run"] = i
    rows.append(rel)
    print(json.dumps(rel), flush=True)
    open(os.path.join(OUT, f"logcat-run{i}.txt"), "w").write("\n".join(l for l in lines if "ATT" in l or "START u0" in l or "Start proc" in l
                                                                        or "WebViewFactory" in l or "Displayed" in l or "monodroid" in l or "Chuvadi" in l))
rows = rows[1:]
json.dump(rows, open(os.path.join(OUT, "timeline-runs.json"), "w"), indent=1)
keys = []
for r in rows:
    for k, v in r.items():
        if isinstance(v, (int, float)) and k not in ("run",) and not k.startswith("_") and k not in keys:
            keys.append(k)
summary = []
for k in keys:
    v = [r[k] for r in rows if isinstance(r.get(k), (int, float))]
    if v:
        summary.append({"milestone": k, "n": len(v), "median": statistics.median(v), "min": min(v), "max": max(v)})
summary.sort(key=lambda x: x["median"])
json.dump(summary, open(os.path.join(OUT, "timeline-summary.json"), "w"), indent=1)
for s_ in summary:
    print(f"{s_['milestone']:<36} median {s_['median']:>7}  min {s_['min']:>7}  max {s_['max']:>7}  (n={s_['n']})")

# One extra run with the .NET runtime's own timing log on, for the runtime start breakdown (not in the medians).
sh("setprop debug.mono.log timing,default")
sh(f"am force-stop {PKG}")
adb("logcat", "-c")
open_with(uri, wait=True)
time.sleep(8)
open(os.path.join(OUT, "mono-timing.txt"), "w").write("\n".join(l for l in log_lines() if "monodroid" in l.lower() or "timing" in l.lower()))
sh("setprop debug.mono.log ''")
