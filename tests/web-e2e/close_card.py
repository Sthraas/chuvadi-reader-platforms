"""D-190 on the portal: closing a tab with unsaved marks asks first (Save / Save as / Discard / Cancel).

Opens two PDFs and draws a rectangle on the first. Checks: the mark is still there after a visit to the
other tab (marks are kept with the tab), and the browser's "Leave site?" is armed while the other tab shows
(any tab's marks count, D-181); the tab's own close button raises the card, Cancel keeps the tab and the
mark, Discard closes it and disarms the browser's question; "Close inactive tabs" asks about a marked tab
that is not showing; "Close all tabs" with "Save as…" delivers the PDF as a download and closes; and "Save"
closes the tab too (it writes the marks into the session's copy of the file on the server; nothing is
downloaded). Development sign-in.

Usage: python3 close_card.py <portal base> <some.pdf> <out dir> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys

from playwright.sync_api import sync_playwright

from pdfs import large_format_pdf, sign_in_as, sign_out

base, pdf, out = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []
os.makedirs(out, exist_ok=True)
big = os.path.join(out, "large-format.pdf")
large_format_pdf(big)
first = os.path.basename(pdf)

ASKS = "() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }"
TABS = "() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())"
MARKS = "() => document.querySelectorAll('.mk-shape.rect').length"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


def wait_for(page, js, want, timeout=15000):
    try:
        page.wait_for_function("want => JSON.stringify((" + js + ")()) === JSON.stringify(want)", arg=want, timeout=timeout)
    except Exception:  # noqa: BLE001 - reported by the caller's check
        pass
    return page.evaluate(js)


def upload(page, path):
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(path)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_selector(".rpage", timeout=60000)
    page.wait_for_timeout(1200)


def show(page, name):
    page.click(".rtab:has(.rtab-name:text-is('%s'))" % name)
    page.wait_for_selector(".rtab.on:has(.rtab-name:text-is('%s')), .rtab.active:has(.rtab-name:text-is('%s'))" % (name, name), timeout=15000)
    page.wait_for_selector(".rpage", timeout=30000)
    page.wait_for_timeout(1200)


def draw(page):
    page.click("nav.leftbar >> text=Mark")
    page.click("button.rb[aria-label='Rectangle']")
    page.evaluate("() => document.querySelector('.rpage').scrollIntoView({ block: 'start' })")
    page.wait_for_timeout(400)
    box = page.locator(".rpage").first.bounding_box()
    x, y = box["x"] + box["width"] * 0.3, max(box["y"], 120) + 120
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 120, y + 80, steps=6)
    page.mouse.up()
    page.wait_for_selector(".mk-shape.rect", timeout=10000)
    page.mouse.move(600, 500)


def close_tab(page, name):
    tab = page.locator(".rtab:has(.rtab-name:text-is('%s'))" % name)
    tab.hover()
    tab.locator(".rtab-x").click()


def card(page, timeout=10000):
    page.wait_for_selector(".closeq", timeout=timeout)
    return page.locator(".closeq")


def tab_menu(page, item):
    page.click("button.rtabs-menu")
    page.click(".tabmenu-pop >> text=%s" % item)


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    sign_in_as(ctx, base, "closecard-" + engine)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    upload(page, pdf)
    draw(page)
    upload(page, big)

    # Marks are kept with the tab, and any tab's marks arm the browser's own question.
    check("the browser's Leave site question is armed while another tab holds the marks", wait_for(page, ASKS, True) is True)
    show(page, first)
    check("the mark is still there after a visit to the other tab", wait_for(page, MARKS, 1) == 1)

    # The tab's own close button: the card; Cancel keeps everything.
    close_tab(page, first)
    q = card(page)
    text = q.inner_text()
    buttons = [t.strip() for t in q.locator("button").all_inner_texts()]
    check("closing the tab asks about its marks, by name", first in text and "1 mark" in text, text.replace("\n", " ")[:120])
    check("the card offers Save, Save as, Discard and Cancel", buttons == ["Save", "Save as…", "Discard", "Cancel"], buttons)
    q.locator("button:text-is('Cancel')").click()
    page.wait_for_selector(".closeq", state="detached", timeout=10000)
    check("Cancel keeps the tab and its mark", page.evaluate(TABS) == [first, "large-format.pdf"] and page.evaluate(MARKS) == 1, page.evaluate(TABS))

    # "Close inactive tabs" from the other tab: the marked tab is not showing, and is still asked about.
    show(page, "large-format.pdf")
    tab_menu(page, "Close inactive tabs")
    q = card(page)
    check("Close inactive tabs asks about the marked tab that was not showing", first in q.inner_text())
    q.locator("button:text-is('Cancel')").click()
    page.wait_for_selector(".closeq", state="detached", timeout=10000)
    check("... and Cancel closes nothing", sorted(page.evaluate(TABS)) == sorted([first, "large-format.pdf"]), page.evaluate(TABS))

    # Discard.
    close_tab(page, first)
    card(page).locator("button:text-is('Discard')").click()
    got = wait_for(page, TABS, ["large-format.pdf"])
    check("Discard closes the tab", got == ["large-format.pdf"], got)
    check("... and the browser's question is disarmed", wait_for(page, ASKS, False) is False)

    # Close all tabs, with "Save as…": the PDF arrives as a download.
    upload(page, pdf)
    draw(page)
    with page.expect_download(timeout=60000) as dl:
        tab_menu(page, "Close all tabs")
        card(page).locator("button:text-is('Save as…')").click()
    saved = os.path.join(out, "close-card-" + engine + "-" + dl.value.suggested_filename)
    dl.value.save_as(saved)
    head = open(saved, "rb").read(5)
    got = wait_for(page, TABS, [])
    check("Close all tabs with Save as delivers the PDF with the marks", head == b"%PDF-" and os.path.getsize(saved) > 1000, dl.value.suggested_filename)
    check("... and then closes every tab", got == [], got)
    check("... leaving nothing for the browser to ask about", wait_for(page, ASKS, False) is False)

    # "Save": into the session's copy of the file on the server (no download).
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    upload(page, big)
    draw(page)
    close_tab(page, "large-format.pdf")
    card(page).locator("button:text-is('Save')").click()
    got = wait_for(page, TABS, [], timeout=60000)
    check("Save closes the tab", got == [], got)
    check("no page errors", not errors, "; ".join(errors[:3]))
    sign_out(ctx, base)
    b.close()

sys.exit(0 if all(results) else 1)
