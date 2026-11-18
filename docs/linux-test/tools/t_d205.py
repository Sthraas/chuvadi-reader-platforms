"""D-205 probe (Linux Test): print server names that the app may not read the way libcups does.

Usage: python3.12 t_d205.py <app dir> <pdf> <work dir> <lx tools dir>
Runs a stand-in CUPS on this machine's network address (not loopback, so "another machine" by name) with full
access logging, keeps the local CUPS running, and for each name records: refused by the app? GTK dialog opened?
requests that reached the stand-in. Never prints: a dialog that opens is closed with Escape.
Needs root (stand-in cupsd, /etc/hosts entries for two test names, restored at the end).
"""
import os, shutil, socket, subprocess, sys, tempfile, time

APP_DIR, PDF, OUT, LX = sys.argv[1:5]
sys.path.insert(0, LX)
from uitest_lib import App  # noqa: E402

ADDR = subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split()[0]
HOSTS_ADD = f"\n{ADDR} print_srv.test\n{ADDR} printsrv.test\n"
os.makedirs(OUT, exist_ok=True)


def start_server():
    root = tempfile.mkdtemp(prefix="lt-d205-")
    for d in ("conf", "spool", "state", "cache", "log", "tmp"):
        os.makedirs(os.path.join(root, d))
    os.chmod(root, 0o755)
    os.chmod(os.path.join(root, "tmp"), 0o1777)
    os.makedirs(os.path.join(root, "conf", "ppd"))
    with open(os.path.join(root, "conf", "cupsd.conf"), "w") as f:
        f.write(f"Listen {ADDR}:631\nBrowsing No\nLogLevel warn\nAccessLogLevel all\nDefaultAuthType None\n"
                "WebInterface No\n<Location />\n  Order allow,deny\n  Allow all\n</Location>\n"
                "<Policy default>\n  <Limit All>\n    Order deny,allow\n  </Limit>\n</Policy>\n")
    with open(os.path.join(root, "conf", "cups-files.conf"), "w") as f:
        f.write(f"ServerRoot {root}/conf\nRequestRoot {root}/spool\nStateDir {root}/state\nCacheDir {root}/cache\n"
                f"TempDir {root}/tmp\nAccessLog {root}/log/access_log\nErrorLog {root}/log/error_log\n"
                f"PageLog {root}/log/page_log\nPidFile {root}/state/cupsd.pid\n")
    proc = subprocess.Popen(["cupsd", "-f", "-c", f"{root}/conf/cupsd.conf", "-s", f"{root}/conf/cups-files.conf"])
    for _ in range(50):
        if subprocess.run(["lpstat", "-h", f"{ADDR}:631", "-r"], capture_output=True, text=True).stdout.startswith("scheduler is running"):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("stand-in didn't start")
    subprocess.run(["lpadmin", "-h", f"{ADDR}:631", "-p", "RemoteOnly", "-E", "-v", "cups-pdf:/",
                    "-m", "lsb/usr/cups-pdf/CUPS-PDF_opt.ppd"], check=True, capture_output=True)
    subprocess.run(["lpadmin", "-h", f"{ADDR}:631", "-d", "RemoteOnly"], check=True, capture_output=True)
    return proc, root


def hits(root):
    try:
        with open(os.path.join(root, "log", "access_log")) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0


def dialogs(app):
    return subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^Print"], env=app.env,
                          capture_output=True, text=True).stdout.split()


def run_case(n, label, root, env=None, client_conf=None, submit=False):
    app = App(APP_DIR, os.path.join(OUT, f"p{n}"), display=f":{90 + n}", env=env)
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
        before = hits(root)
        app.key("ctrl+p")
        time.sleep(1.2)
        app.click("section[aria-label=Print] button.primary")
        refused, dlg = None, []
        for _ in range(40):
            refused = app.js("var t=document.body.innerText; var i=t.search(/set to print through the print server/); "
                             "return i < 0 ? null : t.slice(i, i + 90)")
            dlg = dialogs(app)
            if refused or dlg:
                break
            time.sleep(0.25)
        if dlg:
            time.sleep(4)  # let the dialog list its printers
            subprocess.run(["xdotool", "windowactivate", "--sync", dlg[0]], env=app.env, capture_output=True)
            mid = hits(root) - before
            app.key("Return" if submit else "Escape")
            time.sleep(6 if submit else 1)
        other = None if refused or dlg else app.js(
            "var m=document.body.innerText.match(/(printing service|No printers|Couldn't|isn't set up)[^\\n]{0,80}/); return m ? m[0] : null")
        got = hits(root) - before
        if submit and dlg:
            shown = app.js("var m=document.body.innerText.match(/(Sent|The printer|Couldn't|isn't set up)[^\\n]{0,100}/); return m ? m[0] : null")
            jobs = len(os.listdir(os.path.join(root, "spool")))
            other = f"after Print in the dialog: app says {shown!r}; requests while printing={got - mid}; files in stand-in spool={jobs}"
        verdict = "LEAK" if got else "OK"  # a leak: anything reached the other machine
        return (f"{verdict} {label}: refused={'yes' if refused else 'no'}, dialog={'yes' if dlg else 'no'}, "
                f"requests reaching the stand-in={got}" + (f", app says {other!r}" if other else ""))
    finally:
        app.stop()


shutil.copy("/etc/hosts", "/tmp/lt-hosts.bak")
with open("/etc/hosts", "a") as f:
    f.write(HOSTS_ADD)
subprocess.Popen(["setsid", "nohup", "cupsd", "-f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
proc, root = start_server()
lines = [f"stand-in at {ADDR}:631 (this machine's network address, not loopback); local CUPS running"]
try:
    for n, label, kw in [
        (1, f"CUPS_SERVER={ADDR} (control)", dict(env={"CUPS_SERVER": ADDR})),
        (2, f"CUPS_SERVER={ADDR}:631x", dict(env={"CUPS_SERVER": f"{ADDR}:631x"})),
        (3, f"CUPS_SERVER={ADDR}:", dict(env={"CUPS_SERVER": f"{ADDR}:"})),
        (4, f"CUPS_SERVER=[{ADDR}]", dict(env={"CUPS_SERVER": f"[{ADDR}]"})),
        (5, "CUPS_SERVER=print_srv.test", dict(env={"CUPS_SERVER": "print_srv.test"})),
        (6, "CUPS_SERVER=printsrv.test:ipp", dict(env={"CUPS_SERVER": "printsrv.test:ipp"})),
        (7, f"client.conf ServerName {ADDR}:631x", dict(client_conf=f"ServerName {ADDR}:631x\n")),
        (8, "client.conf ServerName print_srv.test", dict(client_conf="ServerName print_srv.test\n")),
        (9, f"CUPS_SERVER={ADDR}:631x, Print pressed in the dialog", dict(env={"CUPS_SERVER": f"{ADDR}:631x"}, submit=True)),
    ]:
        try:
            lines.append(run_case(n, label, root, **kw))
        except Exception as ex:  # noqa: BLE001
            lines.append(f"ERROR {label}: {type(ex).__name__}: {ex}")
        print(lines[-1], flush=True)
finally:
    proc.terminate()
    proc.wait(10)
    shutil.copy("/tmp/lt-hosts.bak", "/etc/hosts")
    shutil.rmtree(root, ignore_errors=True)

with open(os.path.join(OUT, "d205.txt"), "w") as f:
    f.write("\n".join(lines) + "\n")
print("LEAKS: " + str(sum(l.startswith("LEAK") for l in lines)))
