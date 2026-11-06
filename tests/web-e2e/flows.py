"""Browser flows against a running portal (Development sign-in): open, print, merge -> download.
Test tool only (Playwright + the machine's Chrome)."""
import sys, time, os
from playwright.sync_api import sync_playwright

base, pdf, out, serverlog = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
# --browser chrome (the machine's Chrome, default) | chromium | firefox | webkit (Safari's engine)
browser = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (" — " + detail if detail else ""))

with sync_playwright() as p:
    if browser == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    elif browser == "chromium":
        b = p.chromium.launch(args=["--no-sandbox"])
    elif browser == "firefox":
        # Playwright turns Firefox's own PDF viewer off; real Firefox ships with it on.
        b = p.firefox.launch(firefox_user_prefs={"pdfjs.disabled": False})
    else:
        b = getattr(p, browser).launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    # Headless Chrome can't show a print dialog (print() on a PDF frame crashes the page there), so
    # print() is recorded instead of run; what's tested is that the PDF reached the frame and print was called.
    ctx.add_init_script("window.print = function () { try { window.top.__chvdPrinted = (window.top.__chvdPrinted || 0) + 1; } catch (e) {} };")
    page = ctx.new_page()
    errors = []
    # Firefox closes a live circuit's socket when the page is left ("was interrupted while the page was
    # loading", then Blazor's "closed with status code: 1006"); that is the browser leaving, not a portal error.
    leaving = ("was interrupted while the page was loading", "WebSocket closed with status code: 1006")
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text
            and not (browser == "firefox" and any(x in m.text for x in leaving)) else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    prints = []
    ctx.on("response", lambda r: prints.append((r.url, r.status, r.headers.get("content-type"))) if "/portal/print/" in r.url else None)

    # 1. open through the left bar
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_selector(".page svg, svg text", timeout=30000)
    time.sleep(2)
    page.screenshot(path=os.path.join(out, "flow-reader.png"))
    check("open pdf via browser chooser", "/reader" in page.url)

    # 2. print current page -> browser print of an assembled PDF
    page.keyboard.press("Meta+p" if browser == "webkit" and sys.platform == "darwin" else "Control+p")
    page.wait_for_selector("button.primary:has-text('Print')", timeout=10000)
    page.click("button:has-text('Current')")
    def served():
        return [l for l in open(serverlog).read().splitlines() if "Request finished" in l and "/portal/print/" in l]
    before = len(served())  # only this run's print counts (the log may hold earlier runs)
    popup = None
    page.click("button.primary:has-text('Print')")
    if browser in ("webkit", "chromium"):
        # Safari can't print a PDF inside a frame, and blocks tabs a page opens on its own; Playwright's
        # Chromium has no PDF viewer at all (like a browser set to download PDFs). Either way the portal
        # offers a link, and the person's click opens the PDF in its own tab.
        page.wait_for_selector(".chvd-print-offer a", timeout=30000)
        with page.context.expect_page(timeout=15000) as pp:
            page.click(".chvd-print-offer a")
        popup = pp.value  # not waited on: a PDF tab never "loads" where PDFs download; the served PDF is the witness
    # The PDF viewer's own fetch isn't visible to Playwright; the server log is the witness.
    ok, lines = False, []
    for _ in range(40):
        lines = served()[before:]
        if any(" 200 " in l and "application/pdf" in l for l in lines):
            ok = True
            break
        page.wait_for_timeout(250)
    check("print hands a PDF to the browser", ok, (lines[-1].strip()[:160] if lines else "no request"))
    time.sleep(1.5)
    if browser in ("webkit", "chromium"):
        # WebKit reports no address for a PDF tab; the served PDF above is the witness that it loaded.
        check("print offers the PDF in its own tab, opened by the person's click", popup is not None and ok)
    elif browser == "firefox":
        # Firefox shows the PDF in its own viewer, which test scripts can't reach; the Reader's own
        # "sent to the browser's print dialog" message is the witness that print() was called without error.
        page.wait_for_selector("text=print dialog", timeout=15000)
        check("the Reader reports the PDF went to the print dialog", True)
    else:
        printed = page.evaluate("window.__chvdPrinted || 0")
        check("browser print called once", printed == 1, "calls=%s" % printed)

    # 3. merge two uploads -> download
    page.goto(base + "/merge")
    page.wait_for_selector("text=Add files", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("text=Add files")
    check("merge chooser allows several files", fc.value.is_multiple())
    fc.value.set_files([pdf, pdf])
    page.wait_for_selector("button.tbtn-go:not([disabled])", timeout=30000)
    with page.expect_download(timeout=60000) as dl:
        page.click("button.tbtn-go")
    d = dl.value
    target = os.path.join(out, "downloaded-" + d.suggested_filename)
    d.save_as(target)
    head = open(target, "rb").read(5)
    check("merged pdf downloads", d.suggested_filename == "merged.pdf" and head == b"%PDF-",
          "%s %d bytes" % (d.suggested_filename, os.path.getsize(target)))

    check("no console errors", not errors, "; ".join(errors[:3]))
    b.close()

sys.exit(0 if all(ok for _, ok, _ in results) else 1)
