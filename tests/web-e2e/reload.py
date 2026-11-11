"""D-174 (WT-22): open tabs belong to the signed-in session, not to the browser connection.

Opens two documents (the second is a large-format page, drawn as an image), then checks through the gateway:
a reload shows both tabs again with the active one drawn; the image the old connection drew stops answering
(its documents were closed, not left behind); opening the portal's address again and a second browser tab of
the same sign-in show the same tabs; a tab closed before a reload stays closed. Development sign-in.

Usage: python3 reload.py <portal base> <some.pdf> <out folder> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

from pdfs import large_format_pdf, sign_in_as

base, pdf, out = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
os.makedirs(out, exist_ok=True)
big = os.path.join(out, "large-format.pdf")
large_format_pdf(big)
names = [os.path.basename(pdf), os.path.basename(big)]
results = []

IMAGE = "() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href') || '').find(h => h.startsWith('_chvd/pages/')) || null"
TABS = "() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


def wait_tabs(page, expected, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        got = page.evaluate(TABS)
        if got == expected:
            return got
        page.wait_for_timeout(300)
    return page.evaluate(TABS)


def wait_status(ctx, url, status, timeout=20):
    end = time.time() + timeout
    got = None
    while time.time() < end:
        got = ctx.request.get(url).status
        if got == status:
            break
        time.sleep(0.5)
    return got


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    # The person is named by cookie, not header: a closing page's "disconnect" beacon carries cookies only.
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "reload-" + engine)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    for f in (pdf, big):
        with page.expect_file_chooser(timeout=15000) as fc:
            page.click("nav.leftbar >> text=Upload")
        fc.value.set_files(f)
        page.wait_for_url("**/reader**", timeout=30000)
        wait_tabs(page, names[: names.index(os.path.basename(f)) + 1])
    page.wait_for_function("() => (" + IMAGE + ")() !== null", timeout=60000)
    before = base + "/" + page.evaluate(IMAGE)
    check("two documents are open", page.evaluate(TABS) == names, page.evaluate(TABS))
    check("the active page's image is served", ctx.request.get(before).status == 200)

    # 1. Reload (F5).
    page.wait_for_timeout(1500)
    page.reload()
    got = wait_tabs(page, names)
    check("after a reload both tabs are back, in order", got == names, got)
    try:
        page.wait_for_function("() => (" + IMAGE + ")() !== null", timeout=60000)
        after = base + "/" + page.evaluate(IMAGE)
        check("the active document is drawn again", ctx.request.get(after).status == 200 and after != before)
    except Exception as ex:  # noqa: BLE001
        after = None
        check("the active document is drawn again", False, str(ex)[:120])
    got = wait_status(ctx, before, 404)
    check("the old connection's page image is freed (its documents were closed)", got == 404, got)

    # 2. The portal's address again.
    page.wait_for_timeout(1500)
    page.goto(base + "/")
    got = wait_tabs(page, names)
    check("opening the portal's address again shows the same tabs", got == names, got)

    # 3. A second browser tab of the same sign-in.
    second = ctx.new_page()
    second.goto(base + "/")
    got = wait_tabs(second, names)
    check("a second browser tab of the same sign-in shows the same tabs", got == names, got)
    second.close()

    # 4. A tab closed before a reload stays closed.
    page.wait_for_timeout(1500)
    page.locator(".rtab", has_text=names[1]).locator("button.rtab-x").click()
    wait_tabs(page, names[:1])
    page.wait_for_timeout(1500)
    page.reload()
    got = wait_tabs(page, names[:1])
    page.wait_for_timeout(1500)
    check("a tab closed before a reload stays closed", page.evaluate(TABS) == names[:1], got)
    if after:
        got = wait_status(ctx, after, 404)
        check("the closed document's page image is gone", got == 404, got)

    # 5. Someone else sees none of it.
    other = b.new_context()
    sign_in_as(other, base, "reload-other-" + engine)
    op = other.new_page()
    op.goto(base + "/")
    op.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    op.wait_for_timeout(2000)
    check("another person sees no tabs", op.evaluate(TABS) == [], op.evaluate(TABS))
    check("no page errors", not errors, "; ".join(errors[:3]))
    b.close()

sys.exit(0 if all(results) else 1)
