"""WT-25: a browser that leaves without a clean close does not keep the person's worker and files.

Opens a PDF, then the browser is closed with the tab still open (or, with --kill, its processes are killed).
The framework keeps such a connection for minutes in case the browser reconnects. Checks: while the session
lives its worker and files stay (D-174); when the session ends (idle limit) the files go with it, and the
worker and its folder go within the worker's idle time and a check or two, not a minute or more later.

Portal: gateway mode with Development sign-in and short limits:
  Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:10 Portal__ExpiryCheckInterval=00:00:02
  Portal__Workers__IdleStop=00:00:05 Portal__Workers__CheckInterval=00:00:02

Usage: python3 gone_browser.py <portal base> <some.pdf> <data root> [--browser chrome|chromium|firefox|webkit] [--kill]
"""
import glob
import os
import signal
import sys
import time

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as

base, pdf, root = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
kill = "--kill" in sys.argv
IDLE, ALLOW = 40, 20  # the session's idle limit; what the worker may take after it (idle stop 5 s, checks 2 s)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


def workers():
    w = os.path.join(root, "workers")
    return set(os.listdir(w)) if os.path.isdir(w) else set()


def children(pid):
    """Every process below pid (the browser and its helpers)."""
    found, todo = [], [pid]
    while todo:
        parent = todo.pop()
        for stat in glob.glob("/proc/[0-9]*/stat"):
            try:
                fields = open(stat).read().rsplit(")", 1)[1].split()
            except OSError:
                continue
            if int(fields[1]) == parent:
                child = int(stat.split("/")[2])
                found.append(child)
                todo.append(child)
    return found


with sync_playwright() as p:
    before = workers()
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "gone-" + engine + ("-kill" if kill else ""))
    page = ctx.new_page()
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_selector(".rpage", timeout=60000)
    page.wait_for_timeout(1500)
    mine = workers() - before
    files = glob.glob(os.path.join(root, "workers", "*", "data", "users", "*", "sessions", "*", "uploads", "*", os.path.basename(pdf)))
    files = [f for f in files if f.split(os.sep + "workers" + os.sep)[1].split(os.sep)[0] in mine]
    check("the person has a worker and the file is in their session", len(mine) == 1 and len(files) == 1, (len(mine), len(files)))

    if kill:
        for pid in children(os.getpid()):
            try:
                cmd = open("/proc/%d/cmdline" % pid).read()
            except OSError:
                continue
            if "playwright" in cmd and "driver" in cmd:
                continue  # the test tool itself
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    else:
        b.close()
    left = time.time()

    time.sleep(15)
    check("15 s later the session still holds its worker and file (the person may come back)", bool(mine & workers()) and all(os.path.exists(f) for f in files))

    files_gone = worker_gone = None
    while time.time() - left < IDLE + 120:
        now = round(time.time() - left)
        if files_gone is None and not any(os.path.exists(f) for f in files):
            files_gone = now
        if not (mine & workers()):
            worker_gone = now
            files_gone = now if files_gone is None else files_gone
            break
        time.sleep(1)

    check("the files go when the session ends", files_gone is not None and files_gone <= IDLE + 10, "%s s after the browser left (idle limit %d s)" % (files_gone, IDLE))
    check("the worker and its folder go right after, not a minute later", worker_gone is not None and worker_gone <= IDLE + ALLOW,
          "%s s after the browser left (limit %d + %d s)" % (worker_gone, IDLE, ALLOW))
    print("left by: " + ("killing the browser's processes" if kill else "closing the browser with the tab open"))
    sys.stdout.flush()
    os._exit(0 if all(results) else 1)  # the tool's own shutdown would wait on a browser that is already gone
