#!/usr/bin/env python3
"""B-20 test (test-only, never shipped): with the printing service (CUPS) stopped, Print explains itself —
a plain message, and no empty GTK print dialog.

  tools/linux/no-printer-test.py <ui-test publish dir> <pdf> <out dir>

The caller stops CUPS before and starts it again after (CI: systemctl; locally: the cupsd you run).
Needs what uitest.py needs.
"""
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, PDF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
app = App(APP_DIR, OUT, display=":82")
app.start_display()
failures = []
try:
    app.launch(PDF)
    name = os.path.basename(PDF)
    app.wait(lambda: app.js(f"return [...document.querySelectorAll('.rtab')].some(t => t.innerText.includes('{name}'))"), 30, "tab")
    time.sleep(1.5)
    app.key("ctrl+p")
    time.sleep(1.2)
    app.click("section[aria-label=Print] button.primary")
    msg = app.wait(lambda: app.js("var t=document.body.innerText; var i=t.search(/printing service|No printers are set up/); "
                                  "return i < 0 ? null : t.slice(i, i + 160)"), 15, "the explanation")
    time.sleep(2)
    dialogs = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^Print"], env=app.env,
                             capture_output=True, text=True).stdout.split()
    if dialogs:
        failures.append("an empty GTK print dialog opened")
    app.shot("no-printer")
    print("message:", " ".join(msg.split()))
except Exception as ex:  # noqa: BLE001
    failures.append(f"{type(ex).__name__}: {ex}")
finally:
    app.stop()

if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: Print explained that there is no printing service, no dialog")
