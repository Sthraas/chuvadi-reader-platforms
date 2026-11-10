#!/usr/bin/env python3
"""Startup timing on one emulator: cold / warm / hot launch and cold "Open with" to the first PDF page.

All times are milliseconds on the DEVICE clock, from the moment ActivityTaskManager logs the launch
("START u0 …", logcat -v epoch) to:
  first_frame  Android's own first frame of the activity (am start -W TotalTime; the splash window)
  ui           the app's page has painted Blazor's UI: the first animation frame after the shell
               attributes and the app root have content (Date.now() inside the page, so no host lag)
  first_page   (Open with only) the first frame after page 1's SVG is in the DOM
Polling inside the page runs every 16 ms, so `ui` / `first_page` are late by at most one poll + one frame.

    startup.py <out-dir> <pdf> [runs=12]
"""
import json
import os
import re
import statistics
import sys
import threading
import time

from lib import Cdp, Results, adb, component, device_info, open_with, pid, push_media, sh

OUT, PDF = sys.argv[1], sys.argv[2]
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 12
os.makedirs(OUT, exist_ok=True)
R = Results(OUT, "startup")
COMP = component()
cdp = Cdp()
info = device_info()
json.dump(info, open(os.path.join(OUT, "device.json"), "w"), indent=1)
print("device", info, "component", COMP)

# In-page probe: waits (inside the page, 16 ms polls) for a condition, then one rAF, returns Date.now().
PROBE = """new Promise(res => { const t0 = Date.now(); const already = !!(%s); (function poll(){
  const ok = (%s);
  if (ok) requestAnimationFrame(() => requestAnimationFrame(() => res({t: Date.now(), already, injected: t0})));
  else if (Date.now() - t0 > 60000) res({t: -1, already, injected: t0}); else setTimeout(poll, 16); })(); })"""
UI_READY = ("document.documentElement.hasAttribute('data-shell') && document.getElementById('app') "
            "&& document.getElementById('app').children.length > 0 && document.body.innerText.trim().length > 20")
PAGE_READY = "document.querySelector('.rpage-wrap .rpage svg') !== null"


def launch_epoch():
    """Device epoch ms of the last launch of our package (ActivityTaskManager START line)."""
    log = adb("logcat", "-d", "-v", "epoch", "-s", "ActivityTaskManager:I", "ActivityManager:I")
    t = None
    for line in log.splitlines():
        if "START u0" in line and "in.chuvadi.reader" in line:
            t = float(line.split()[0]) * 1000
    return t


def drop_caches():
    sh("sync; echo 3 > /proc/sys/vm/drop_caches")


def am_start_w(extra=""):
    out = sh(f"am start -W {extra} -n {COMP}")
    m = re.search(r"TotalTime: (\d+)", out)
    return int(m.group(1)) if m else None, out


def page_time(cond):
    try:
        cdp.close()
        cdp.connect(60)
        cdp.wait("document.readyState !== 'loading' || true", 5, 0.02)
        return cdp.js(PROBE % (cond, cond))
    except Exception as e:
        print("probe error", e)
        return None


def measure(kind, runs, prep, launch, cond):
    rows = []
    fails = 0
    for i in range(runs):
        if fails >= 3:
            print(kind, "stopped: 3 launches in a row gave no measurement", flush=True)
            break
        prep()
        adb("logcat", "-c")
        time.sleep(0.5)
        # Launch in the background and attach to the page at once, so the in-page probe usually
        # arrives before the UI is ready (otherwise the run is marked late).
        box = {}
        th = threading.Thread(target=lambda: box.update(r=launch()))
        th.start()
        time.sleep(0.05)
        t_page = page_time(cond)
        th.join()
        first_frame, raw = box.get("r", (None, ""))
        t0 = launch_epoch()
        ok = bool(t_page and t_page.get("t", -1) > 0 and t0)
        # If the condition was already true when the probe arrived, the time is only an upper bound:
        # such runs are kept apart ("late") and left out of the median.
        late = bool(t_page and t_page.get("already"))
        row = {"run": i + 1, "first_frame": first_frame,
               "ready": (t_page["t"] - t0) if ok and not late else None,
               "ready_upper_bound": (t_page["t"] - t0) if ok and late else None,
               "probe_injected": (t_page["injected"] - t0) if ok else None}
        rows.append(row)
        fails = fails + 1 if row["first_frame"] is None and row["ready"] is None and row["ready_upper_bound"] is None else 0
        print(kind, row, flush=True)
    json.dump(rows, open(os.path.join(OUT, f"{kind}.json"), "w"), indent=1)
    return rows


def summary(kind, rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    if not v:
        return {"kind": kind, "metric": key, "n": 0}
    return {"kind": kind, "metric": key, "n": len(v), "median": statistics.median(v), "worst": max(v), "best": min(v)}


def cold_prep():
    sh(f"am force-stop {PKG}")
    drop_caches()
    time.sleep(1)


PKG = "in.chuvadi.reader"
sh("settings put global always_finish_activities 0")
# Warm-up install effects (first launch after install compiles/extracts): one discarded launch.
cold_prep()
am_start_w()
page_time(UI_READY)

results = {}
ONLY_OPEN = bool(os.environ.get("ONLY_OPEN"))
cold = [] if ONLY_OPEN else measure("cold", RUNS, cold_prep, lambda: am_start_w(), UI_READY)


def warm_prep():
    # Process alive, activity destroyed: "Don't keep activities" + Home.
    if not pid():
        am_start_w()
        page_time(UI_READY)
    sh("settings put global always_finish_activities 1")
    sh("input keyevent KEYCODE_HOME")
    time.sleep(2)


warm = [] if ONLY_OPEN else measure("warm", RUNS, warm_prep, lambda: am_start_w(), UI_READY)
sh("settings put global always_finish_activities 0")


def hot_prep():
    if not pid():
        am_start_w()
        page_time(UI_READY)
    sh("input keyevent KEYCODE_HOME")
    time.sleep(1.5)


hot = [] if ONLY_OPEN else measure("hot", RUNS, hot_prep, lambda: am_start_w(), "true")

uri = push_media(PDF, "startup-doc.pdf")


def open_cold():
    out = open_with(uri, wait=True)
    m = re.search(r"TotalTime: (\d+)", out)
    return (int(m.group(1)) if m else None), out


pdf_cold = measure("open-with-cold", RUNS, cold_prep, open_cold, PAGE_READY)

table = [summary("cold", cold, "first_frame"), summary("cold", cold, "ready"),
         summary("warm", warm, "first_frame"), summary("warm", warm, "ready"),
         summary("hot", hot, "first_frame"),
         summary("open-with-cold", pdf_cold, "first_frame"), summary("open-with-cold", pdf_cold, "ready")]
json.dump({"device": info, "summary": table}, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
for t in table:
    print(json.dumps(t))
mem = sh(f"dumpsys meminfo {PKG}")
open(os.path.join(OUT, "meminfo.txt"), "w").write(mem)
for t in table:
    if t["n"] or not ONLY_OPEN:
        R.check(f"{t['kind']} {t['metric']} measured over {RUNS} runs", t["n"] >= min(10, RUNS), t)
