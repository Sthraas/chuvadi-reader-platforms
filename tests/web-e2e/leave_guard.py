"""D-181: the browser's own "Leave site?" question while the open document has unsaved marks.

Opens a PDF and checks: with no marks, leaving is not questioned; after drawing a rectangle (Mark), a
reload raises the browser's question, and staying keeps the mark; after "Clear all marks" the question is
gone and a reload goes straight through with the tab back (D-174). Development sign-in.

The question itself is the browser's (we can't style or word it). Playwright sees it as a "beforeunload"
dialog in Chromium and WebKit; Firefox shows it only after a real person's input, so there the check is that
the page asks for it (the unload event is cancelled).

Usage: python3 leave_guard.py <portal base> <some.pdf> [--browser chrome|chromium|firefox|webkit]
"""
import sys

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as, sign_out

base, pdf = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []

# Would leaving be questioned right now? (What the browser itself checks: is "beforeunload" cancelled.)
ASKS = "() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }"
TABS = "() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


def wait_asks(page, expected, timeout=10000):
    try:
        page.wait_for_function("want => (" + ASKS + ")() === want", arg=expected, timeout=timeout)
    except Exception:  # noqa: BLE001 - reported by the caller's check
        pass
    return page.evaluate(ASKS)


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "leave-" + engine)
    page = ctx.new_page()
    dialogs = []

    def on_dialog(d):
        dialogs.append(d.type)
        d.dismiss()  # "Stay on the page"

    page.on("dialog", on_dialog)
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_selector(".rpage svg", timeout=60000)
    page.wait_for_timeout(1500)
    check("with no marks, leaving is not questioned", page.evaluate(ASKS) is False)

    # Draw a rectangle on the first page.
    page.click("nav.leftbar >> text=Mark")
    page.click("button.rb[aria-label='Rectangle']")
    box = page.locator(".rpage").first.bounding_box()
    x, y = box["x"] + box["width"] * 0.3, box["y"] + min(box["height"], 700) * 0.3
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 120, y + 80, steps=6)
    page.mouse.up()
    asks = wait_asks(page, True)
    check("with an unsaved mark, leaving is questioned", asks is True)
    check("the Reader itself says the marks are unsaved", page.locator("button.rb[aria-label='Clear all marks']").is_enabled())

    if engine != "firefox":
        try:
            page.reload(timeout=8000)
        except Exception:  # noqa: BLE001 - the reload was called off by staying
            pass
        page.wait_for_timeout(1500)
        check("a reload raises the browser's question, and staying keeps the mark",
              dialogs == ["beforeunload"] and page.locator("button.rb[aria-label='Clear all marks']").is_enabled(), dialogs)

    page.click("button.rb[aria-label='Clear all marks']")
    asks = wait_asks(page, False)
    check("with the marks cleared, leaving is not questioned again", asks is False)
    seen = len(dialogs)
    page.wait_for_timeout(1000)
    page.reload()
    page.wait_for_function("() => document.querySelectorAll('.rtab .rtab-name').length === 1", timeout=30000)
    check("a reload then goes straight through, with the tab back", len(dialogs) == seen and len(page.evaluate(TABS)) == 1, dialogs)

    # When the portal itself sends the tab away (the session ended), nobody is asked: it couldn't be undone anyway.
    page.click("nav.leftbar >> text=Mark")
    page.click("button.rb[aria-label='Rectangle']")
    box = page.locator(".rpage").first.bounding_box()
    x, y = box["x"] + box["width"] * 0.3, box["y"] + min(box["height"], 700) * 0.3
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 120, y + 80, steps=6)
    page.mouse.up()
    armed = wait_asks(page, True)
    seen = len(dialogs)
    page.evaluate("() => window.chvdPortal.leave('/signed-out')")
    try:
        page.wait_for_url("**/signed-out", timeout=15000)
    except Exception:  # noqa: BLE001 - reported below
        pass
    check("the portal's own leave at session end is not questioned", armed is True and len(dialogs) == seen and page.url.endswith("/signed-out"), page.url[-30:])
    sign_out(ctx, base)
    b.close()

sys.exit(0 if all(results) else 1)
