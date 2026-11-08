"""Shared helpers for the Android Test chat's emulator suites (test tooling only, never shipped).

adb wrappers, a persistent DevTools (CDP) connection to the app's WebView, screenshots, MediaStore
content URIs, results recording. Device-clock times come from logcat (-v epoch) and the page's own
performance clock, so host latency never enters a measurement.
"""
import json
import os
import re
import subprocess
import time
import urllib.request

import websocket  # websocket-client (test tooling)

PKG = os.environ.get("CHVD_PKG", "in.chuvadi.reader")
PORT = 9333


def adb(*args, check=False, timeout=120):
    r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def sh(cmd, timeout=120):
    return adb("shell", cmd, timeout=timeout)


def pid():
    return sh(f"pidof {PKG}").strip()


def component():
    return sh(f"cmd package resolve-activity --brief {PKG}").strip().splitlines()[-1].strip()


def device_epoch_ms():
    return int(sh("date +%s%3N").strip())


def screencap(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=60).stdout)
    return path


def as_shell_user(cmd):
    """Run `cmd` as uid 2000 (an ordinary sending app), even when adbd runs as root."""
    root = sh("id -u").strip() == "0"
    return sh(("su 2000 " if root else "") + cmd)


def push_media(local, name=None):
    """Push a file to Download/ and return its MediaStore content URI."""
    name = name or os.path.basename(local)
    adb("push", local, f"/sdcard/Download/{name}")
    sh(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file:///sdcard/Download/{name}'")
    for _ in range(20):
        for coll in ("downloads", "file"):
            rows = sh(f"content query --uri content://media/external/{coll} --projection _id "
                      f"--where \"_display_name='{name}'\"")
            m = re.findall(r"_id=(\d+)", rows)
            if m:
                return f"content://media/external/{coll}/{m[-1]}"
        time.sleep(1)
    return None


def open_with(uri, mime="application/pdf", wait=False):
    w = "-W " if wait else ""
    return as_shell_user(f"am start {w}-a android.intent.action.VIEW -d '{uri}' -t {mime} -p {PKG} "
                         f"--grant-read-uri-permission")


def dismiss_system_dialogs():
    """Emulator noise: 'Pixel Launcher isn't responding' / 'System UI isn't responding' → Wait."""
    xml = ui_dump()
    m = re.search(r'text="Wait"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m and "isn't responding" in xml and PKG not in re.findall(r'isn.t responding', xml)[0]:
        x1, y1, x2, y2 = map(int, m.groups())
        sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
        time.sleep(1)


def ui_dump():
    sh("uiautomator dump /sdcard/ui.xml >/dev/null 2>&1")
    return sh("cat /sdcard/ui.xml")


class Cdp:
    """One DevTools connection to the app's page; reconnects when the process changes."""

    def __init__(self):
        self.ws = None
        self.pid = None
        self.n = 0

    def connect(self, timeout=60):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            p = pid()
            if p:
                try:
                    adb("forward", f"tcp:{PORT}", f"localabstract:webview_devtools_remote_{p}")
                    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3))
                    pages = [t for t in targets if t.get("type") == "page"]
                    if pages:
                        self.close()
                        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=30,
                                                              suppress_origin=True)
                        self.pid = p
                        return True
                except Exception as e:  # socket not there yet
                    last = e
            time.sleep(0.05)
        raise RuntimeError(f"no DevTools page for {PKG}: {last}")

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.ws = None

    def call(self, method, params=None):
        if self.ws is None or pid() != self.pid:
            self.connect()
        self.n += 1
        my = self.n
        self.ws.send(json.dumps({"id": my, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == my:
                return msg

    def js(self, expr):
        msg = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        res = msg.get("result", {})
        if "exceptionDetails" in res:
            raise RuntimeError("page error: " + json.dumps(res["exceptionDetails"])[:400])
        return res.get("result", {}).get("value")

    def wait(self, expr, seconds=30, poll=0.25):
        end = time.time() + seconds
        v = None
        while time.time() < end:
            try:
                v = self.js(expr)
                if v:
                    return v
            except Exception:
                self.close()
            time.sleep(poll)
        return v


class Results:
    """Collects check results as JSON lines plus a readable summary."""

    def __init__(self, out, suite):
        self.out = out
        self.suite = suite
        os.makedirs(out, exist_ok=True)
        self.rows = []

    def check(self, case, ok, detail=None, evidence=None):
        row = {"suite": self.suite, "case": case, "result": "PASS" if ok is True else ("FAIL" if ok is False else str(ok)),
               "detail": detail, "evidence": evidence}
        self.rows.append(row)
        print(f"[{row['result']}] {case} :: {json.dumps(detail)[:300] if detail is not None else ''}", flush=True)
        with open(os.path.join(self.out, "results.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        return ok

    def failed(self):
        return [r for r in self.rows if r["result"] == "FAIL"]


def device_info():
    return {
        "api": sh("getprop ro.build.version.sdk").strip(),
        "release": sh("getprop ro.build.version.release").strip(),
        "model": sh("getprop ro.product.model").strip(),
        "build_type": sh("getprop ro.build.type").strip(),
        "size": sh("wm size").strip(),
        "density": sh("wm density").strip(),
        "webview": re.findall(r"Current WebView package \(name, version\): \(([^)]*)\)", sh("dumpsys webviewupdate")),
        "locale": sh("getprop persist.sys.locale").strip(),
    }


def set_rotation(r):
    """0 = natural, 1 = 90°. Fixed rotation, auto-rotate off."""
    sh("settings put system accelerometer_rotation 0")
    sh(f"settings put system user_rotation {r}")
    time.sleep(2.5)


def portrait_rotation():
    """Rotation value that gives portrait on this device (tablets are naturally landscape)."""
    w, h = map(int, re.findall(r"(\d+)x(\d+)", sh("wm size"))[-1])
    return 0 if h > w else 1
