#!/usr/bin/env python3
"""On an emulator whose Android System WebView is older than 128 (D-105): the app must show the update
screen instead of the Reader, its button must lead out of the app (Google Play, or the Play web page),
and coming back must land on the same screen, with no crash. CI only.

    webview_gate.py <results-dir>
"""
import json
import os
import re
import subprocess
import sys
import time

OUT = sys.argv[1]
PKG = "in.chuvadi.reader"
os.makedirs(OUT, exist_ok=True)
results = []


def adb(*args):
    return subprocess.run(["adb", *args], capture_output=True, text=True).stdout


def shot(name):
    with open(os.path.join(OUT, name + ".png"), "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True).stdout)


def dump():
    """UI tree, after tapping "Wait" on the emulator's own "<app> isn't responding" dialog if it shows
    (round 7: Pixel Launcher's covered the update screen on phone API 35; emulator noise, not our app)."""
    xml = ""
    for _ in range(4):
        xml = subprocess.run(["adb", "exec-out", "uiautomator", "dump", "/dev/tty"], capture_output=True, text=True).stdout
        if not re.search(r"isn.t responding", xml):
            return xml
        m = re.search(r'text="Wait"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if not m:
            return xml
        x1, y1, x2, y2 = map(int, m.groups())
        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(2)
    return xml


def texts(xml):
    return [t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()]


def resumed():
    out = adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"(?:topResumedActivity|mResumedActivity|ResumedActivity)[:=].*? ([\w.]+)/", out)
    return m.group(1) if m else None


def check(name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " — " + json.dumps(detail)[:600])


webview = re.search(r"Current WebView package \(name, version\): \(([^,]+), ([^)]+)\)", adb("shell", "dumpsys", "webviewupdate"))
version = webview.group(2) if webview else None
print(f"WebView: {webview.group(1) if webview else '?'} {version}")

adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
xml = ""
for _ in range(30):
    time.sleep(2)
    xml = dump()
    if "One small update first" in xml:
        break
shot("w1-update-screen")
t = texts(xml)
check("old WebView: the update screen shows instead of the Reader",
      "One small update first" in t and "Update Android System WebView" in t
      and any(version and version in x for x in t) and not any(x in ("Read", "Mark", "Arrange", "Protect") for x in t),
      {"webview": version, "texts": t[:12]})

pid0 = adb("shell", "pidof", PKG).strip()
m = re.search(r'text="Update Android System WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if m:
    x1, y1, x2, y2 = map(int, m.groups())
    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
time.sleep(5)
went = resumed()
shot("w2-after-update-button")
check("the update button leads out of the app (Google Play or its web page)",
      bool(m) and went not in (None, PKG), {"resumed": went})

adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
time.sleep(4)
xml = dump()
shot("w3-back-in-app")
check("back in the app: same process, still the update screen (WebView not updated)",
      resumed() == PKG and adb("shell", "pidof", PKG).strip() == pid0 and "One small update first" in xml,
      {"resumed": resumed(), "pid": [pid0, adb("shell", "pidof", PKG).strip()]})

log = adb("logcat", "-d")
crash = [ln for ln in log.splitlines() if re.search(rf"AndroidRuntime: Process: {re.escape(PKG)}|Fatal signal .*\({re.escape(PKG)}\)|ANR in {re.escape(PKG)}", ln)]
check("no crash or ANR in the app", not crash, {"lines": crash[:5]})

with open(os.path.join(OUT, "webview-gate.json"), "w") as f:
    json.dump({"webview": version, "results": results}, f, indent=2)
failed = [r["check"] for r in results if not r["pass"]]
print(f"{len(results) - len(failed)}/{len(results)} WebView-gate checks passed")
sys.exit(1 if failed else 0)
