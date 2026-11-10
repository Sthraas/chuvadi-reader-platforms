"""D-174: the session keeps its documents while it is signed in, even with no browser tab open.

Opens a document, closes the browser tab (no sign-out), waits well past the worker's idle limit, opens the
portal again as the same person and expects the tab back; then leaves, lets the session expire, and expects the
person's worker process and files to be gone. Run the gateway with short limits:
  Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:10 Portal__ExpiryCheckInterval=00:00:02
  Portal__Workers__IdleStop=00:00:05 Portal__Workers__CheckInterval=00:00:02

Usage: python3 comeback.py <portal base> <some.pdf> <data root> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

base, pdf, data_root = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
who = "comeback-" + engine + "-" + str(int(time.time()))
results = []
TABS = "() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


def workers():
    """The per-person worker folders the gateway holds right now (each is deleted when its worker stops)."""
    folder = os.path.join(data_root, "workers")
    return set(os.listdir(folder)) if os.path.isdir(folder) else set()


def pdfs(worker_ids):
    return [f for w in worker_ids for _, _, names in os.walk(os.path.join(data_root, "workers", w)) for f in names if f.endswith(".pdf")]


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    ctx.add_cookies([{"name": "chvd-dev-user", "value": who, "url": base}])
    before = workers()
    page = ctx.new_page()
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_function("() => document.querySelectorAll('.rtab .rtab-name').length === 1", timeout=30000)
    mine = workers() - before
    check("the person has a worker holding the file", len(mine) == 1 and len(pdfs(mine)) == 1, (len(mine), pdfs(mine)))
    page.close()  # the browser tab is closed without signing out

    time.sleep(20)  # four times the worker's idle limit, half the session's
    check("with no tab open the session's worker and file are still there", mine <= workers() and len(pdfs(mine)) == 1)
    page = ctx.new_page()
    page.goto(base + "/")
    try:
        page.wait_for_function("() => document.querySelectorAll('.rtab .rtab-name').length === 1", timeout=30000)
        check("coming back within the session shows the document again", page.evaluate(TABS) == [os.path.basename(pdf)], page.evaluate(TABS))
    except Exception as ex:  # noqa: BLE001
        check("coming back within the session shows the document again", False, str(ex)[:120])
    page.close()

    end = time.time() + 90  # the session expires 40 s after the last activity; then the worker goes
    while time.time() < end and mine & workers():
        time.sleep(2)
    check("after the session expires with no tab open, the worker and files are gone", bool(mine) and not (mine & workers()))
    page = ctx.new_page()
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    page.wait_for_timeout(2500)
    check("a new session starts empty", page.evaluate(TABS) == [], page.evaluate(TABS))
    b.close()

sys.exit(0 if all(results) else 1)
