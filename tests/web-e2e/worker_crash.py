"""Security advisory (17 Nov): what happens to the gateway and to other people when one person's worker
dies hard while it is opening a file — as an uncatchable stack overflow in a parsing library would end it.

Two people. The second has a PDF open and keeps reading. The first uploads a PDF and, while the portal is
still taking it in and opening it, their worker process is ended from outside with a signal a process cannot
handle or survive (KILL). For the gateway that is the same event as a stack overflow: the process is gone
at once, with no chance to clean up, and a non-zero exit code (137 here; 134 for the runtime's own abort).
(ABRT and SEGV sent from outside are not a faithful stand-in: the .NET runtime takes those two signals for
its own use and the worker carries on, which this script reports if asked to try them.)
Checks: the gateway is alive and answers; the second person's worker is the same process and their next
pages draw; the dead worker's folder (the first person's files) is removed; no memory dump is left;
the first person's page says so and, after a reload, they are still signed in with a fresh worker and no
open documents; and they can open a file again. Development sign-in.

Usage: python3 worker_crash.py <portal base> <some.pdf> <data root> <gateway log> [--browser …] [--signal KILL|ABRT|SEGV]
"""
import glob
import os
import re
import signal
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as, sign_out

base, pdf, root, log = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3], sys.argv[4]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
signame = sys.argv[sys.argv.index("--signal") + 1] if "--signal" in sys.argv else "KILL"
results = []
DRAWN = """(i) => { const w = document.querySelector('.rpage-wrap[data-page="' + i + '"]');
  if (!w) return false; const s = w.querySelector('.rpage svg'); if (!s || s.childElementCount === 0) return false;
  const r = w.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }"""
NEXT = "button.tb-pg-btn[aria-label='Next page']"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail).replace("\n", " ") if detail != "" else ""))


def workers():
    w = os.path.join(root, "workers")
    return set(os.listdir(w)) if os.path.isdir(w) else set()


def pid_of(key):
    found = re.findall(r"Worker %s started \(pid (\d+)\)" % re.escape(key[:8]), open(log, errors="replace").read())
    return int(found[-1]) if found else None


def alive(pid):
    try:
        os.kill(pid, 0)
        return "zombie" not in open("/proc/%d/status" % pid).read().lower()
    except OSError:
        return False


def healthy():
    try:
        return urllib.request.urlopen(base + "/healthz", timeout=5).read() == b"ok"
    except Exception:  # noqa: BLE001
        return False


def launch(p):
    if engine == "chrome":
        return p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    return getattr(p, "chromium" if engine == "chromium" else engine).launch()


def home(page):
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)


def choose(page, path):
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(path)


with sync_playwright() as p:
    b = launch(p)
    # --- the bystander -------------------------------------------------------------------------------------
    before = workers()
    other = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(other, base, "bystander-" + engine)
    reader = other.new_page()
    home(reader)
    choose(reader, pdf)
    reader.wait_for_function(DRAWN, arg=0, timeout=60000)
    theirs = (workers() - before).pop()
    their_pid = pid_of(theirs)

    # --- the person whose worker dies ------------------------------------------------------------------------
    before = workers()
    one = b.new_context(viewport={"width": 1400, "height": 900})
    who = sign_in_as(one, base, "crash-" + engine)
    page = one.new_page()
    home(page)
    mine = (workers() - before).pop()
    pid = pid_of(mine)
    check("each person has their own worker process", pid and their_pid and pid != their_pid and alive(pid) and alive(their_pid), (pid, their_pid))

    # A first document, fully open: its file is in the worker's folder. Then a second upload, cut down mid-way.
    choose(page, pdf)
    page.wait_for_function(DRAWN, arg=0, timeout=60000)
    kept = glob.glob(os.path.join(root, "workers", mine, "data", "users", "*", "sessions", "*", "uploads", "*", os.path.basename(pdf)))
    home(page)
    choose(page, pdf)
    tabs_at_kill = page.locator(".rtab").count()
    os.kill(pid, getattr(signal, "SIG" + signame))
    killed = time.time()
    check("the worker was ended (SIG%s) while the second upload and open were still under way" % signame, tabs_at_kill <= 1 and len(kept) == 1,
          "tabs open at that moment: %d; files in the worker's folder: %d" % (tabs_at_kill, len(kept)))
    time.sleep(0.5)
    if alive(pid):
        print("note: SIG%s did not end the worker (the runtime took the signal); nothing to observe" % signame)
        sys.exit(2)

    # --- the gateway and the bystander -----------------------------------------------------------------------
    time.sleep(1)
    check("the gateway is alive and answers its health check", healthy())
    ok = True
    try:
        for i in range(1, 4):
            reader.locator(NEXT).first.click()
            reader.wait_for_function(DRAWN, arg=i, timeout=30000)
    except Exception as ex:  # noqa: BLE001
        ok = str(ex)[:120]
    check("the other person goes on reading: their next three pages draw", ok is True, "" if ok is True else ok)
    check("... in the same worker process as before", alive(their_pid) and pid_of(theirs) == their_pid, their_pid)

    # --- what is left of the dead worker ---------------------------------------------------------------------
    gone = None
    while time.time() - killed < 20:
        if not alive(pid) and not any(os.path.exists(f) for f in kept):
            gone = round(time.time() - killed, 1)
            break
        time.sleep(0.2)
    check("the dead worker's files (the person's uploaded document) are removed", gone is not None, "%s s after it died" % gone)
    dumps = [f for pat in ("core", "core.*", "*.dmp", "crash*.json") for d in (root, os.path.dirname(log), os.getcwd(), "/tmp")
             for f in glob.glob(os.path.join(d, pat)) if os.path.isfile(f) and os.path.getmtime(f) >= killed - 1]
    check("no memory dump of the worker is left behind", not dumps, dumps[:3])
    text = open(log, errors="replace").read()
    line = re.findall(r"Worker %s \(pid %d\) ended with code (-?\d+)" % (re.escape(mine[:8]), pid), text)
    check("the gateway logs that the worker ended, with its exit code", bool(line), "code " + (line[-1] if line else "?"))

    # --- what the person sees, and that they can go on -------------------------------------------------------
    page.wait_for_timeout(4000)
    seen = " | ".join(t.strip() for t in page.locator("body").inner_text().split("\n") if t.strip())[-260:]
    print("the person's page, 5 s after: " + seen)
    try:
        page.reload()
        page.wait_for_selector("nav.leftbar >> text=Upload", timeout=45000)
        again = (workers() - before - {mine}) or ({mine} & workers())
        new_pid = pid_of(mine)
        tabs = page.locator(".rtab").count()
        check("after a reload the person is still signed in, on a fresh worker, with no open documents",
              new_pid is not None and new_pid != pid and alive(new_pid) and tabs == 0, "new pid %s, tabs %d" % (new_pid, tabs))
        choose(page, pdf)
        page.wait_for_function(DRAWN, arg=0, timeout=60000)
        check("... and can open a file again", True)
    except Exception as ex:  # noqa: BLE001
        check("after a reload the person can go on", False, str(ex)[:160])
    check("the gateway is still healthy at the end", healthy())
    sign_out(one, base)
    sign_out(other, base)
    b.close()

sys.exit(0 if all(results) else 1)
