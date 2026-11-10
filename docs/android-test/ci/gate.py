#!/usr/bin/env python3
"""D-105 WebView gate (test tooling only). On an image whose WebView is < 128 the app must show its
update screen (no Reader), name the WebView update, and not crash. On >= 128 it must not show it.

    gate.py <out-dir>
"""
import os
import re
import sys
import time

from lib import PKG, Results, adb, component, screencap, sh, ui_dump

OUT = sys.argv[1]
R = Results(OUT, "gate")
ver = re.findall(r"Current WebView package \(name, version\): \(([^,]+), ([0-9.]+)\)", sh("dumpsys webviewupdate"))
major = int(ver[0][1].split(".")[0]) if ver else 0
sh(f"am force-stop {PKG}")
adb("logcat", "-c")
sh(f"am start -W -n {component()}")
time.sleep(8)
xml = ui_dump()
screencap(os.path.join(OUT, f"gate-webview-{major}.png"))
open(os.path.join(OUT, "gate-ui.xml"), "w").write(xml)
texts = re.findall(r'text="([^"]+)"', xml)
alive = bool(sh(f"pidof {PKG}").strip())
mentions = any(re.search(r"update|WebView", t, re.I) for t in texts)
fatal = "FATAL EXCEPTION" in adb("logcat", "-d")
if major and major < 128:
    R.check(f"D-105 WebView {major}: update screen shown, app alive, no crash", alive and mentions and not fatal,
            {"webview": ver, "texts": texts[:20], "alive": alive, "fatal": fatal})
else:
    R.check(f"D-105 WebView {major}: no update screen", alive and not mentions, {"webview": ver, "texts": texts[:12]})
