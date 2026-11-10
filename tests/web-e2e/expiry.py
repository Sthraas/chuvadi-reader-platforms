"""Session expiry (D-30) in a real browser, against a portal started with short limits, e.g.
Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:25 Portal__ExpiryCheckInterval=00:00:02
(Development sign-in; gateway or single mode). Test tool only (Playwright + the machine's Chrome).

Opens a PDF, stays still until the warning shows, says "I'm still here" (the warning goes), downloads
the open document from the next warning, then stays still until the session ends: the tab goes to the
signed-out page. With --data-root, also checks that the person's files are gone.

Usage: python3 expiry.py <portal base> <some.pdf> <out folder> [--data-root <Portal:DataRoot>] [--browser chrome|chromium|firefox|webkit]
"""
import os, sys, time, zipfile
from playwright.sync_api import sync_playwright

from pdfs import large_format_pdf


def launch(p):
    """--browser chrome (the machine's Chrome, default) | chromium | firefox | webkit (Safari's engine)."""
    name = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
    if name == "chrome":
        return p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    if name == "chromium":
        return p.chromium.launch(args=["--no-sandbox"])
    if name == "firefox":
        return p.firefox.launch(firefox_user_prefs={"pdfjs.disabled": False})  # as real Firefox ships
    return p.webkit.launch()

base, pdf, out = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
data_root = sys.argv[sys.argv.index("--data-root") + 1] if "--data-root" in sys.argv else None
results = []

def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (" — " + str(detail) if detail else ""))

def files_under(root):
    return [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs] if root and os.path.isdir(root) else []

with sync_playwright() as p:
    b = launch(p)
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

    # WT-21: a second document whose page is drawn as an image; its address must stop working when the session ends.
    os.makedirs(out, exist_ok=True)
    big = os.path.join(out, "large-format.pdf")
    large_format_pdf(big)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(big)
    page.wait_for_function("() => [...document.querySelectorAll('.rpage svg image')].some(i => (i.getAttribute('href') || '').startsWith('_chvd/pages/'))", timeout=60000)
    image = base + "/" + page.evaluate("() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href')).find(h => h.startsWith('_chvd/pages/'))")
    check("the open page's image is served to its owner", ctx.request.get(image).status == 200)

    # WT-22 (D-174): a reload brings both tabs back; what the first connection drew must not outlive the session.
    first_image = image
    page.wait_for_timeout(1000)
    page.reload()
    page.wait_for_function("() => document.querySelectorAll('.rtab .rtab-name').length === 2", timeout=30000)
    page.wait_for_function("() => [...document.querySelectorAll('.rpage svg image')].some(i => (i.getAttribute('href') || '').startsWith('_chvd/pages/'))", timeout=60000)
    image = base + "/" + page.evaluate("() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href')).find(h => h.startsWith('_chvd/pages/'))")
    check("after a reload both documents are open again", image != first_image and ctx.request.get(image).status == 200)
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
        page.click(".chvd-expiry >> text=Download open documents")
    name = dl.value.suggested_filename
    saved = os.path.join(out, "expiry-" + name)
    dl.value.save_as(saved)
    with zipfile.ZipFile(saved) as z:  # test-only check that other tools open it; both documents, byte for byte
        same = sorted(z.namelist()) == sorted([os.path.basename(pdf), os.path.basename(big)]) \
            and z.read(os.path.basename(pdf)) == open(pdf, "rb").read() and z.read(os.path.basename(big)) == open(big, "rb").read()
    check("the warning hands over both open documents as one zip", name == "Chuvadi documents.zip" and same, name)

    # Stay still again: the session ends and the tab goes to the signed-out page.
    t0 = time.time()
    page.wait_for_selector(".chvd-expiry", timeout=120000)
    page.wait_for_url("**/signed-out", timeout=120000)
    print("ended %.0f s after the second warning began" % (time.time() - t0))
    check("the session ends on the signed-out page", page.url.endswith("/signed-out"))
    # Development sign-in signs the same person straight back in, so only freeing the image makes this a 404.
    check("the ended session's page image is freed at once", ctx.request.get(image).status == 404)
    check("and so is the one drawn before the reload", ctx.request.get(first_image).status == 404)
    if data_root:
        page.wait_for_timeout(3000)
        left = [f for f in files_under(data_root) if f.endswith(".pdf")]
        check("the person's files are gone", not left, left[:3])
    check("no page errors", not errors, errors[:3])
    b.close()

sys.exit(0 if all(ok for _, ok in results) else 1)
