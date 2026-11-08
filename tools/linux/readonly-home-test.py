#!/usr/bin/env python3
"""B-16 test (test-only, never shipped): with a home folder Chuvadi can't write (kiosk, locked-down or full
disk), the app starts, opens the file it was given, and says once that settings can't be saved.

  tools/linux/readonly-home-test.py <ui-test publish dir> <pdf> <out dir>

Runs as the current user, who must not be root (root writes anywhere); as root it reports and exits 0 — run
it as an ordinary user (CI's runner is one). Needs what uitest.py needs.
"""
import os, shutil, stat, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, PDF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
if os.geteuid() == 0:
    print("SKIP: root can write a read-only folder; run this test as an ordinary user")
    sys.exit(0)

home = tempfile.mkdtemp(prefix="chvd-ro-home-")
doc = os.path.join(tempfile.mkdtemp(prefix="chvd-ro-doc-"), os.path.basename(PDF))
shutil.copy(PDF, doc)
os.chmod(home, stat.S_IRUSR | stat.S_IXUSR)  # read-only: no .config, .cache or Documents can be made
app = App(APP_DIR, OUT, display=":83", env={"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config"),
                                             "XDG_CACHE_HOME": os.path.join(home, ".cache")})
app.home = home
app.start_display()
failures = []
try:
    app.launch(doc)
    name = os.path.basename(doc)
    app.wait(lambda: app.js(f"return [...document.querySelectorAll('.rtab')].some(t => t.innerText.includes('{name}'))"),
             30, "the document's tab")
    note = app.wait(lambda: app.js("var t=document.body.innerText; var i=t.indexOf(\"can't save its settings\"); "
                                   "return i < 0 ? null : t.slice(Math.max(0, i - 8), i + 160)"), 15, "the notice")
    app.shot("readonly-home")
    if "denied" not in note:
        failures.append("notice gives no reason: " + note)
    if os.path.exists(os.path.join(home, ".config")):
        failures.append("a settings folder was created in a read-only home")
    print("notice:", " ".join(note.split()))
except Exception as ex:  # noqa: BLE001 — report what happened
    failures.append(f"{type(ex).__name__}: {ex}")
finally:
    app.stop()
    os.chmod(home, stat.S_IRWXU)
    log = open(app.log_path).read()
    if "Chuvadi error" in log:
        failures.append("unhandled error: " + log[log.index("Chuvadi error"):][:300])

if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: started with a read-only home, opened the file, one notice")
