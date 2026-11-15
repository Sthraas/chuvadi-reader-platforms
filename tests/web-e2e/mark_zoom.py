"""M-27 on the portal: a mark and a redact box drawn by mouse land where they were drawn, at any zoom, in every engine.

Older WebKit reports a zoomed element's rectangle unzoomed, which would put a mark drawn at a zoom in the
wrong place (patch 27 made mark placement engine-independent). For each zoom (as opened, zoomed in twice,
zoomed out three times from there) this draws a rectangle on the first page with the mouse and compares the
drawn mark's box on screen with the drag: each edge within a few pixels. Then the same on the Redact page
(Protect, "Redact box") with a redaction box, and a look at "Sign with certificate": greyed out on the portal
with its reason (D-187). Development sign-in.

Usage: python3 mark_zoom.py <portal base> <some.pdf> [--browser chrome|chromium|firefox|webkit]
"""
import sys

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as, sign_out

base, pdf = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []
TOLERANCE = 4  # px, each edge (the mark's border and rounding to the page's percent grid)


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail) if detail != "" else ""))


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "markzoom-" + engine)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_selector(".rpage svg", timeout=60000)
    ZOOM = "() => getComputedStyle(document.querySelector('[style*=\"--rpage-zoom\"]')).getPropertyValue('--rpage-zoom').trim()"

    def zoom(label, times):
        """The View rail's zoom buttons (there in Mark too)."""
        for _ in range(times):
            page.click("button.rb[aria-label='%s']" % label)
            page.wait_for_timeout(400)
        page.wait_for_timeout(800)

    def mark_mode():
        if page.locator("button.rb[aria-label='Rectangle']").count() == 0:
            page.click("nav.leftbar >> text=Mark")
            page.wait_for_selector("button.rb[aria-label='Rectangle']", timeout=15000)
            page.wait_for_timeout(500)

    def draw_and_measure(name):
        mark_mode()
        pct = "zoom " + page.evaluate(ZOOM)
        page.evaluate("() => document.querySelector('.rpage').scrollIntoView({ block: 'start' })")
        page.wait_for_timeout(500)
        if page.locator("button.rb[aria-label='Clear all marks']").is_enabled():
            page.click("button.rb[aria-label='Clear all marks']")
            page.wait_for_function("() => document.querySelectorAll('.mk-shape.rect').length === 0", timeout=10000)
        page.click("button.rb[aria-label='Rectangle']")
        box = page.locator(".rpage").first.bounding_box()
        view = page.viewport_size
        # A drag inside the part of the page that is on screen.
        left = max(box["x"], 260) + 40
        top = max(box["y"], 60) + 40
        right = min(box["x"] + box["width"], view["width"] - 80) - 40
        bottom = min(box["y"] + box["height"], view["height"] - 80) - 40
        x1, y1 = left + (right - left) * 0.2, top + (bottom - top) * 0.2
        x2, y2 = left + (right - left) * 0.6, top + (bottom - top) * 0.55
        page.mouse.move(x1, y1)
        page.mouse.down()
        page.mouse.move((x1 + x2) / 2, (y1 + y2) / 2, steps=5)
        page.mouse.move(x2, y2, steps=5)
        page.mouse.up()
        try:
            page.wait_for_selector(".mk-shape.rect", timeout=10000)
        except Exception as ex:  # noqa: BLE001
            check("%s (%s): the rectangle is drawn" % (name, pct), False, str(ex)[:100])
            return
        page.wait_for_timeout(500)
        m = page.locator(".mk-shape.rect").first.bounding_box()
        off = [round(m["x"] - x1, 1), round(m["y"] - y1, 1), round(m["x"] + m["width"] - x2, 1), round(m["y"] + m["height"] - y2, 1)]
        check("%s (%s): the mark lands where it was drawn" % (name, pct), all(abs(o) <= TOLERANCE for o in off),
              "edges off by %s px; drag %dx%d" % (off, x2 - x1, y2 - y1))

    draw_and_measure("as opened")
    zoom("Zoom in", 2)
    draw_and_measure("zoomed in")
    zoom("Zoom out", 3)
    draw_and_measure("zoomed out")

    # --- Protect: "Sign with certificate" is off on the portal, with its reason (D-187) -------------------
    if page.locator("button.rb[aria-label='Clear all marks']").is_enabled():
        page.click("button.rb[aria-label='Clear all marks']")
        page.wait_for_function("() => document.querySelectorAll('.mk-shape.rect').length === 0", timeout=10000)
    page.click("nav.leftbar >> text=Protect")
    page.wait_for_selector("button.rb[aria-label='Redact box']", timeout=15000)
    cert = page.locator("button.rb[aria-label='Sign with certificate']").first
    check("Sign with certificate is greyed out on the portal", cert.count() == 1 and not cert.is_enabled())
    tip = cert.get_attribute("title") or ""
    check("... and says why", "desktop app" in tip and "private key" in tip, tip)

    # --- Redact: a redaction box drawn by mouse, at each zoom ---------------------------------------------
    page.click("button.rb[aria-label='Redact box']")
    page.wait_for_url("**/redact**", timeout=30000)
    page.wait_for_selector(".rd-desk .rpage svg", timeout=60000)
    RZOOM = "() => getComputedStyle(document.querySelector('.rd-desk')).getPropertyValue('--rpage-zoom').trim()"

    def rzoom(label, times):
        for _ in range(times):
            page.locator("button.rb[aria-label='%s']:not(.rb-viewfold)" % label).first.click()
            page.wait_for_timeout(400)
        page.wait_for_timeout(800)

    def box_and_measure(name):
        pct = "zoom " + page.evaluate(RZOOM)
        page.evaluate("() => document.querySelector('.rd-desk .rpage').scrollIntoView({ block: 'start' })")
        page.wait_for_timeout(500)
        if page.locator(".mk-box").count() > 0:
            page.locator(".mk-box").first.hover()
            page.locator(".mk-box-x").first.click()  # the box's own remove button (the Tools rail folds away)
            page.wait_for_function("() => document.querySelectorAll('.mk-box').length === 0", timeout=10000)
        box = page.locator(".rd-desk .rpage").first.bounding_box()
        desk = page.locator(".rd-desk").bounding_box()
        left = max(box["x"], desk["x"]) + 40
        top = max(box["y"], desk["y"]) + 40
        right = min(box["x"] + box["width"], desk["x"] + desk["width"]) - 40
        bottom = min(box["y"] + box["height"], desk["y"] + desk["height"]) - 40
        x1, y1 = left + (right - left) * 0.2, top + (bottom - top) * 0.2
        x2, y2 = left + (right - left) * 0.6, top + (bottom - top) * 0.55
        page.mouse.move(x1, y1)
        page.mouse.down()
        page.mouse.move((x1 + x2) / 2, (y1 + y2) / 2, steps=5)
        page.mouse.move(x2, y2, steps=5)
        page.mouse.up()
        try:
            page.wait_for_selector(".mk-box", timeout=10000)
        except Exception as ex:  # noqa: BLE001
            check("redact, %s (%s): the box is drawn" % (name, pct), False, str(ex)[:100])
            return
        page.wait_for_timeout(500)
        m = page.locator(".mk-box").first.bounding_box()
        off = [round(m["x"] - x1, 1), round(m["y"] - y1, 1), round(m["x"] + m["width"] - x2, 1), round(m["y"] + m["height"] - y2, 1)]
        check("redact, %s (%s): the box lands where it was drawn" % (name, pct), all(abs(o) <= TOLERANCE for o in off),
              "edges off by %s px; drag %dx%d" % (off, x2 - x1, y2 - y1))

    box_and_measure("as opened")
    rzoom("Zoom in", 2)
    box_and_measure("zoomed in")
    rzoom("Zoom out", 3)
    box_and_measure("zoomed out")
    if page.locator(".mk-box").count() > 0:
        page.locator(".mk-box").first.hover()
        page.locator(".mk-box-x").first.click()
        page.wait_for_function("() => document.querySelectorAll('.mk-box').length === 0", timeout=10000)
    check("no page errors", not errors, "; ".join(errors[:3]))
    sign_out(ctx, base)
    b.close()

sys.exit(0 if all(results) else 1)
