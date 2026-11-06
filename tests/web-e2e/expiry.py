"""Session expiry (D-30) in a real browser, against a portal started with short limits, e.g.
Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:25 Portal__ExpiryCheckInterval=00:00:02
(Development sign-in; gateway or single mode). Test tool only (Playwright + the machine's Chrome).

Opens a PDF, stays still until the warning shows, says "I'm still here" (the warning goes), downloads
the open document from the next warning, then stays still until the session ends: the tab goes to the
signed-out page. With --data-root, also checks that the person's files are gone.

Usage: python3 expiry.py <portal base> <some.pdf> <out folder> [--data-root <Portal:DataRoot>]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

base, pdf, out = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
data_root = sys.argv[sys.argv.index("--data-root") + 1] if "--data-root" in sys.argv else None
results = []

def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (" — " + str(detail) if detail else ""))

def files_under(root):
    return [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs] if root and os.path.isdir(root) else []

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_selector(".page svg, svg text", timeout=30000)
    check("a document is open", "/reader" in page.url)
    if data_root:
        check("the person's file is on the server", any(f.endswith(os.path.basename(pdf)) for f in files_under(data_root)))

    # Stay still: the warning must come (page.wait_for_* keeps the browser's events flowing).
    t0 = time.time()
    warning = page.wait_for_selector(".chvd-expiry", timeout=120000)
    text = warning.inner_text()
    print("warning after %.0f s: %s" % (time.time() - t0, text.replace("\n", " | ")[:200]))
    check("the idle warning shows", "Are you still there?" in text and "removed from the server" in text)
    page.screenshot(path=os.path.join(out, "expiry-warning.png"))

    page.click(".chvd-expiry >> text=I'm still here")
    page.wait_for_selector(".chvd-expiry", state="detached", timeout=20000)
    check("\"I'm still here\" takes the warning down", page.query_selector(".chvd-expiry") is None)

    # The next warning offers the open document (the click is activity too, so it then goes away).
    page.wait_for_selector(".chvd-expiry", timeout=120000)
    with page.expect_download(timeout=30000) as dl:
        page.click(".chvd-expiry >> text=Download the open document")
    name = dl.value.suggested_filename
    saved = os.path.join(out, "expiry-" + name)
    dl.value.save_as(saved)
    check("the warning hands over the open document", name == os.path.basename(pdf) and os.path.getsize(saved) == os.path.getsize(pdf), name)

    # Stay still again: the session ends and the tab goes to the signed-out page.
    t0 = time.time()
    page.wait_for_selector(".chvd-expiry", timeout=120000)
    page.wait_for_url("**/signed-out", timeout=120000)
    print("ended %.0f s after the second warning began" % (time.time() - t0))
    check("the session ends on the signed-out page", page.url.endswith("/signed-out"))
    if data_root:
        page.wait_for_timeout(3000)
        left = [f for f in files_under(data_root) if f.endswith(".pdf")]
        check("the person's files are gone", not left, left[:3])
    check("no page errors", not errors, errors[:3])
    b.close()

sys.exit(0 if all(ok for _, ok in results) else 1)
