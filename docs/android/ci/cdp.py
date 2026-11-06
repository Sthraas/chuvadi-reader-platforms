#!/usr/bin/env python3
"""Reads state from the app's page through the WebView DevTools socket (CI only; Debug builds,
where AddBlazorWebViewDeveloperTools enables WebView debugging). Used only to CHECK what a gesture
did — the gestures themselves are real touch events (touch.py).

    cdp.py <expression>      → prints the JSON value of the expression

Needs `pip install websocket-client` (test tooling, never shipped).
"""
import json
import subprocess
import sys
import urllib.request

import websocket  # websocket-client

PKG = "in.chuvadi.reader"
PORT = 9222


def connect():
    pid = subprocess.run(["adb", "shell", "pidof", PKG], capture_output=True, text=True).stdout.strip()
    if not pid:
        raise SystemExit(f"{PKG} is not running")
    subprocess.run(["adb", "forward", f"tcp:{PORT}", f"localabstract:webview_devtools_remote_{pid}"], check=True,
                   capture_output=True)
    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=10))
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        raise SystemExit(f"no page target: {targets}")
    return websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)


def evaluate(expression):
    ws = connect()
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": expression, "returnByValue": True, "awaitPromise": True}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                break
    finally:
        ws.close()
    result = msg.get("result", {})
    if "exceptionDetails" in result:
        raise SystemExit("page error: " + json.dumps(result["exceptionDetails"])[:500])
    return result.get("result", {}).get("value")


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1])))
