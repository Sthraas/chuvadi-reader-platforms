#!/usr/bin/env python3
"""B-21 test (test-only, never shipped): "Show in folder" opens exactly one file-manager window.

  tools/linux/reveal-test.py <ui-test publish dir> <pdf> <out dir>

1. A file manager that takes 8 s to answer (a cold Nautilus): one ShowItems call, no xdg-open fallback.
2. No file manager on the bus: the folder opens with xdg-open (once).
xdg-open is replaced by a stand-in that only logs. Needs what uitest.py needs, plus python3-gi.
"""
import os, stat, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, PDF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
bindir = tempfile.mkdtemp(prefix="chvd-stub-")
opened = os.path.join(OUT, "xdg-open.log")
with open(os.path.join(bindir, "xdg-open"), "w") as f:
    f.write(f"#!/bin/sh\necho \"$(date +%s.%N) $*\" >> {opened}\n")
os.chmod(os.path.join(bindir, "xdg-open"), stat.S_IRWXU)

failures = []


def system_python():
    """The system Python whose GObject binding loads (python3-gi is built for the distribution's Python)."""
    for exe in ("/usr/bin/python3", "/usr/bin/python3.12", "/usr/bin/python3.13"):
        if os.path.exists(exe) and subprocess.run([exe, "-c", "import gi"], capture_output=True).returncode == 0:
            return exe
    sys.exit("FAIL: no system Python with python3-gi for the stand-in file manager")


def run(case, delay):
    calls = os.path.join(OUT, f"showitems-{case}.log")
    for p in (calls, opened):
        open(p, "w").close()
    app = App(APP_DIR, os.path.join(OUT, case), display=":79" if case == "slow" else ":78",
              env={"PATH": bindir + os.pathsep + os.environ["PATH"]})
    app.start_display()
    fm = None
    try:
        if delay is not None:
            fm = subprocess.Popen([system_python(), os.path.join(HERE, "fake-filemanager.py"), calls, str(delay)],
                                  env=app.env)
            time.sleep(1.5)
            owner = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.DBus", "/",
                                    "org.freedesktop.DBus.NameHasOwner", "string:org.freedesktop.FileManager1"],
                                   env=app.env, capture_output=True, text=True).stdout
            if fm.poll() is not None or "true" not in owner:
                failures.append("the stand-in file manager didn't start")
                return
        app.launch(PDF)
        name = os.path.basename(PDF)
        app.wait(lambda: app.js(f"return [...document.querySelectorAll('.rtab')].some(t => t.innerText.includes('{name}'))"), 30, "tab")
        time.sleep(1)
        ids = [c["Id"] for c in app.commands() if c["Id"] == "doc.reveal" and c["Enabled"]]
        if not ids:
            failures.append(f"{case}: no Show in folder command")
            return
        app.send("invoke " + ids[0])
        time.sleep((delay or 0) + 4)
        n_calls = len(open(calls).read().splitlines())
        n_open = len(open(opened).read().splitlines())
        print(f"{case}: ShowItems calls {n_calls}, xdg-open calls {n_open}")
        if delay is not None and (n_calls != 1 or n_open != 0):
            failures.append(f"slow file manager: {n_calls} ShowItems, {n_open} xdg-open (want 1 and 0)")
        if delay is None and n_open != 1:
            failures.append(f"no file manager: {n_open} xdg-open (want 1)")
    finally:
        app.stop()
        if fm:
            fm.terminate()


run("slow", 8)
run("none", None)
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: one window either way")
