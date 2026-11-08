#!/usr/bin/env python3
"""Remote CUPS test (test-only, never shipped): Print uses a separate CUPS server named in CUPS_SERVER or in
client.conf's ServerName, as lpstat and GTK's print dialog do.

  tools/linux/remote-cups-test.py <ui-test publish dir> <pdf> <out dir>

The "remote" server is a second cupsd on localhost:8631 with its own folders and one cups-pdf queue (a stand-in
for a print server). The caller stops the local CUPS first and starts it again after, so nothing can fall back
to it. Three cases:
  1. nothing configured        → the plain "can't reach the printing service" message (the old behaviour);
  2. CUPS_SERVER=localhost:8631 → the GTK dialog opens and the job is completed on that server;
  3. ServerName in ~/.cups/client.conf → the same.
Starts the stand-in with sudo when not root; needs what uitest.py needs, plus cups-pdf.
"""
import os, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, PDF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SERVER = "localhost:8631"
SUDO = [] if os.geteuid() == 0 else ["sudo"]  # the stand-in server needs root; the app runs as the caller
os.makedirs(OUT, exist_ok=True)


def start_server():
    root = tempfile.mkdtemp(prefix="chvd-remote-cups-")
    for d in ("conf", "spool", "state", "cache", "log", "tmp"):
        os.makedirs(os.path.join(root, d))
    os.chmod(root, 0o755)  # CUPS' filters run as lp and must reach the spool and temp folders
    os.chmod(os.path.join(root, "tmp"), 0o1777)
    os.makedirs(os.path.join(root, "conf", "ppd"))  # CUPS' own MIME rules come from its data folder
    with open(os.path.join(root, "conf", "cupsd.conf"), "w") as f:
        f.write(f"""Listen {SERVER}
Browsing No
LogLevel warn
DefaultAuthType None
WebInterface No
<Location />
  Order allow,deny
  Allow all
</Location>
<Policy default>
  <Limit All>
    Order deny,allow
  </Limit>
</Policy>
""")
    with open(os.path.join(root, "conf", "cups-files.conf"), "w") as f:
        f.write(f"""ServerRoot {root}/conf
RequestRoot {root}/spool
StateDir {root}/state
CacheDir {root}/cache
TempDir {root}/tmp
AccessLog {root}/log/access_log
ErrorLog {root}/log/error_log
PageLog {root}/log/page_log
PidFile {root}/state/cupsd.pid
""")
    subprocess.run(SUDO + ["chown", "-R", "root:root", root], check=True)
    proc = subprocess.Popen(SUDO + ["cupsd", "-f", "-c", f"{root}/conf/cupsd.conf", "-s", f"{root}/conf/cups-files.conf"])
    for _ in range(50):
        if subprocess.run(["lpstat", "-h", SERVER, "-r"], capture_output=True, text=True).stdout.startswith("scheduler is running"):
            break
        time.sleep(0.2)
    else:
        log = subprocess.run(SUDO + ["tail", "-c", "800", f"{root}/log/error_log"], capture_output=True, text=True).stdout
        raise RuntimeError("the stand-in print server didn't start: " + log)
    subprocess.run(SUDO + ["lpadmin", "-h", SERVER, "-p", "OfficePDF", "-E", "-v", "cups-pdf:/",
                    "-m", "lsb/usr/cups-pdf/CUPS-PDF_opt.ppd"], check=True, capture_output=True)
    subprocess.run(SUDO + ["lpadmin", "-h", SERVER, "-d", "OfficePDF"], check=True, capture_output=True)
    return proc, root


def completed_jobs():
    r = subprocess.run(["lpstat", "-h", SERVER, "-W", "completed", "-o"], capture_output=True, text=True)
    return len(r.stdout.split("\n")) - 1 if r.stdout.strip() else 0


def run_case(n, label, env=None, client_conf=None, expect_print=True):
    app = App(APP_DIR, os.path.join(OUT, f"case{n}"), display=f":{83 + n}", env=env)
    if client_conf:
        os.makedirs(os.path.join(app.home, ".cups"), exist_ok=True)
        with open(os.path.join(app.home, ".cups", "client.conf"), "w") as f:
            f.write(client_conf)
    app.start_display()
    try:
        app.launch(PDF)
        name = os.path.basename(PDF)
        app.wait(lambda: app.js(f"return [...document.querySelectorAll('.rtab')].some(t => t.innerText.includes('{name}'))"), 30, "tab")
        time.sleep(1.5)
        before = completed_jobs()
        app.key("ctrl+p")
        time.sleep(1.2)
        app.click("section[aria-label=Print] button.primary")
        if not expect_print:
            msg = app.wait(lambda: app.js("var t=document.body.innerText; var i=t.search(/printing service|No printers are set up/); "
                                          "return i < 0 ? null : t.slice(i, i + 120)"), 15, "the explanation")
            app.shot(f"remote-cups-{n}")
            return f"{label}: '{' '.join(msg.split())[:70]}…'"
        dialog = app.wait(lambda: subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^Print"], env=app.env,
                                                 capture_output=True, text=True).stdout.split(), 15, "GTK print dialog")[0]
        subprocess.run(["xdotool", "windowactivate", "--sync", dialog], env=app.env, capture_output=True)
        time.sleep(3)  # printers load asynchronously
        app.shot(f"remote-cups-{n}-dialog")
        app.key("Return")
        try:
            app.wait(lambda: completed_jobs() > before, 60, "the job completed on the print server")
        except Exception:
            app.shot(f"remote-cups-{n}-after")
            jobs = subprocess.run(["lpstat", "-h", SERVER, "-W", "all", "-o", "-l"], capture_output=True, text=True).stdout
            shown = app.js("var m=document.body.innerText.match(/(Sent|The printer|Couldn't|isn't set up)[^\\n]{0,160}/); return m ? m[0] : null")
            raise AssertionError(f"no completed job on {SERVER}; app shows {shown!r}; server jobs: {jobs.strip()[:400]!r}; "
                                 f"server log: {subprocess.run(SUDO + ['tail', '-c', '400', os.path.join(root, 'log', 'error_log')], capture_output=True, text=True).stdout!r}")
        toast = app.wait(lambda: app.js("var m=document.body.innerText.match(/Sent \\d+ pages? to the printer/); return m ? m[0] : null"),
                         10, "toast")
        return f"{label}: '{toast}', job completed on {SERVER}"
    finally:
        app.stop()


failures, results = [], []
proc, root = start_server()
try:
    for n, label, kwargs in [
        (1, "nothing configured", dict(expect_print=False)),
        (2, "CUPS_SERVER", dict(env={"CUPS_SERVER": SERVER})),
        (3, "~/.cups/client.conf", dict(client_conf=f"# test\nServerName {SERVER}\n")),
    ]:
        try:
            results.append(run_case(n, label, **kwargs))
        except Exception as ex:  # noqa: BLE001
            failures.append(f"case {n} ({label}): {type(ex).__name__}: {ex}")
finally:
    proc.terminate()
    proc.wait(10)
    subprocess.run(SUDO + ["rm", "-rf", root])

print("\n".join(results))
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: Print uses the CUPS server named in CUPS_SERVER or client.conf")
