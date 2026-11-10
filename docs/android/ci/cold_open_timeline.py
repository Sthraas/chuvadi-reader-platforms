#!/usr/bin/env python3
"""AT-14: where a cold "Open with" spends its time, stage by stage, on the booted emulator.

For each run: clear the app's data (a first open), stop it, drop the page cache, then send the PDF with
Open with (ACTION_VIEW, as the shell user so the URI grant holds) and the extra chuvadi.timing=true.
The app writes its timeline to the log, tag ChuvadiTiming, in ms since its process started:
    process · runtime · maui · activity · import-start · import-done · handed · webview · webview-ready
    · html · ui · opening · painted
(Platform/StartupTimeline.cs). Prints each run and the median and worst per stage, and writes JSON.

    cold_open_timeline.py <apk> <label> <pdf> <results-dir> [runs=10]
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time

APK, LABEL, PDF, OUT = sys.argv[1:5]
RUNS = int(sys.argv[5]) if len(sys.argv) > 5 else 10
PKG = "in.chuvadi.reader"
STAGES = ["runtime", "maui", "activity", "import-start", "import-done", "handed", "webview", "webview-ready",
          "html", "ui", "opening", "painted"]
os.makedirs(OUT, exist_ok=True)


def adb(*args, check=False):
    r = subprocess.run(["adb", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"adb {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


adb("root")
time.sleep(3)
adb("wait-for-device")
adb("uninstall", PKG)
adb("install", "-r", APK, check=True)

# The PDF in Downloads, through MediaStore, as a file manager would hand it over.
name = "chuvadi-cold-" + os.path.basename(PDF)
adb("push", PDF, f"/sdcard/Download/{name}", check=True)
uri = None
for attempt in range(15):
    for coll in ("downloads", "file"):
        row = adb("shell", "content", "query", "--uri", f"content://media/external/{coll}", "--projection", "_id",
                  "--where", f"\"_display_name='{name}'\"")
        ids = re.findall(r"_id=(\d+)", row)
        if ids:
            uri = f"content://media/external/{coll}/{ids[-1]}"
            break
    if uri:
        break
    if attempt in (0, 4):
        adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file:///sdcard/Download/{name}")
    time.sleep(2)
if not uri:
    sys.exit(f"{name} not in MediaStore")
print(f"{LABEL}: {name} as {uri}", flush=True)

runs = []
for i in range(RUNS):
    adb("shell", "pm", "clear", PKG)
    adb("shell", "am", "force-stop", PKG)
    adb("shell", "sync; echo 3 > /proc/sys/vm/drop_caches")
    time.sleep(2)
    adb("logcat", "-c")
    as_shell = ["su", "2000"] if adb("shell", "id -u").strip() == "0" else []   # a root am's URI grant doesn't reach the app
    adb("shell", *as_shell, "am", "start", "-a", "android.intent.action.VIEW", "-d", uri, "-t", "application/pdf",
        "-p", PKG, "--grant-read-uri-permission", "--ez", "chuvadi.timing", "true")
    marks = {}
    deadline = time.time() + 60
    while time.time() < deadline and "painted" not in marks:
        time.sleep(1)
        for line in adb("logcat", "-d", "-s", "ChuvadiTiming:I").splitlines():
            m = re.search(r"ChuvadiTiming: ([\w-]+) (\d+)$", line.strip())
            if m:
                marks.setdefault(m.group(1), int(m.group(2)))
    runs.append(marks)
    print(f"{LABEL} run {i + 1}: " + "  ".join(f"{s} {marks.get(s, '—')}" for s in STAGES), flush=True)

summary = {}
for s in STAGES:
    values = [r[s] for r in runs if s in r]
    if values:
        summary[s] = {"median": int(statistics.median(values)), "worst": max(values), "n": len(values)}

print(f"\n{LABEL}: ms from process start (median / worst over {RUNS} cold Open with runs)")
prev = 0
for s in STAGES:
    if s in summary:
        med = summary[s]["median"]
        print(f"  {s:<14} {med:>6} / {summary[s]['worst']:>6}   (+{med - prev})")
        prev = med
with open(os.path.join(OUT, f"cold-open-{LABEL}.json"), "w") as f:
    json.dump({"label": LABEL, "apk_bytes": os.path.getsize(APK), "runs": runs, "summary": summary}, f, indent=2)
adb("uninstall", PKG)
sys.exit(0 if summary.get("painted", {}).get("n") == RUNS else 1)
