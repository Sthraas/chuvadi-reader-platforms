#!/usr/bin/env python3
# TESTING ONLY. Patch 27 on touch sizes: zoom by every way a pinch can arrive, and marks landing under the
# pointer, by finger and by mouse, at more than one zoom.
#   * PDF: two-finger pinch, Ctrl + wheel (mouse / trackpad), the host's own pinch (window.chuvadiPinch)
#   * Excel and Word: the same three, on their text size
#   * Mark: a rectangle dragged by finger and by mouse lies under the drag, at the fit zoom and zoomed in;
#     a pinch in Mark with a tool on zooms and leaves no mark (H-25)
#   pinchmarks.py <url> <width> <height>     → PASS/FAIL per check, exit 1 on any FAIL
# It opens tests/…/Fixtures/Office/layout.xlsx and discharge.docx and closes their tabs again; marks it draws
# are deleted again; the PDF's zoom is put back.
import asyncio, os, sys, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
FIX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "ChuvadiReader.Tests", "Fixtures", "Office"))
PAGE_W = "(() => { const e = document.querySelector('.rpage-wrap'); return e ? e.getBoundingClientRect().width : 0; })()"

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)

    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"

        async def touch(kind, pts):
            await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})
        async def finger_pinch(cx, cy, scale, start=40):
            await touch("touchStart", [(cx - start, cy), (cx + start, cy)])
            for k in range(1, 11):
                d = start + start * (scale - 1) * k / 10
                await touch("touchMove", [(cx - d, cy), (cx + d, cy)]); await asyncio.sleep(0.02)
            await touch("touchEnd", []); await pg.wait_for_timeout(1000)
        async def ctrl_wheel(cx, cy, dy):
            await pg.mouse.move(cx, cy); await pg.keyboard.down("Control"); await pg.mouse.wheel(0, dy); await pg.keyboard.up("Control")
            await pg.wait_for_timeout(1000)
        async def host_pinch(cx, cy, scale):
            ok = await pg.evaluate("""([x, y, s]) => { if (!window.chuvadiPinch) return null; window.chuvadiPinch('begin', 1, x, y);
                window.chuvadiPinch('change', (1 + s) / 2, x, y); const ok = window.chuvadiPinch('change', s, x, y); window.chuvadiPinch('end', s, x, y); return ok; }""", [cx, cy, scale])
            await pg.wait_for_timeout(1000); return ok
        near = lambda got, want, tol=0.08: want > 0 and abs(got - want) / want <= tol

        # ── PDF ──────────────────────────────────────────────────────────────────────────────────
        desk = await pg.locator(".rdesk").first.bounding_box()
        cx, cy = desk["x"] + desk["width"] / 2, desk["y"] + desk["height"] / 2
        w_start = await pg.evaluate(PAGE_W)
        await finger_pinch(cx, cy, 1.5); w1 = await pg.evaluate(PAGE_W)
        report("PDF: a two-finger pinch ×1.5 zooms ×1.5", near(w1, w_start * 1.5), f"{w_start:.0f} → {w1:.0f} px (×{w1 / w_start:.2f})")
        await ctrl_wheel(cx, cy, -200); w2 = await pg.evaluate(PAGE_W)
        report("PDF: Ctrl + wheel (mouse, trackpad) zooms in", w2 > w1 * 1.1, f"{w1:.0f} → {w2:.0f} px")
        took = await host_pinch(cx, cy, 0.8); w3 = await pg.evaluate(PAGE_W)
        report("PDF: the host's own pinch (window.chuvadiPinch) ×0.8 zooms ×0.8", bool(took) and near(w3, w2 * 0.8), f"{w2:.0f} → {w3:.0f} px, took {took}")
        await host_pinch(cx, cy, w_start / w3); w4 = await pg.evaluate(PAGE_W)     # back to where it started

        # ── Marks: a rectangle lies under the drag, by finger and by mouse, at two zooms ─────────
        if phone: await pg.locator(".ph-nav-b:nth-child(2)").click()
        else: await pg.locator(".lb-mode:nth-of-type(2)").click()
        await pg.wait_for_timeout(1200)
        tool = pg.locator(".ph-strip button", has_text="Box").first if phone else pg.locator('.srail .rb[aria-label="Rectangle"]')
        async def draw(by):
            if "on" not in ((await tool.get_attribute("class")) or "").split():
                await tool.tap(); await pg.wait_for_timeout(400)
            d = await pg.locator(".rdesk").first.bounding_box()
            pb = await pg.locator(".mk-layer").first.bounding_box()      # the first page: it may be smaller than the desk, or run off it
            a = (max(pb["x"], d["x"]) + 40, max(pb["y"], d["y"]) + 40); c = (a[0] + min(110, d["width"] * 0.3), a[1] + min(70, d["height"] * 0.3))
            on_page = await pg.evaluate("([a, c]) => [a, c].every(q => { const e = document.elementFromPoint(q[0], q[1]); return !!(e && e.closest('.rpage-wrap')); })", [a, c])
            before = await pg.locator(".mk-shape").count()
            if by == "finger":
                await touch("touchStart", [a])
                for k in range(1, 9):
                    await touch("touchMove", [(a[0] + (c[0] - a[0]) * k / 8, a[1] + (c[1] - a[1]) * k / 8)]); await asyncio.sleep(0.03)
                await touch("touchEnd", [])
            else:
                await pg.mouse.move(*a); await pg.mouse.down(); await pg.mouse.move(*c, steps=8); await pg.mouse.up()
            await pg.wait_for_timeout(900)
            if await pg.locator(".fcard .fcard-x").count():      # the card may lie over the mark (phone landscape)
                await pg.locator(".fcard .fcard-x").tap(); await pg.wait_for_timeout(500)
            got = await pg.evaluate("""([a, c]) => { const shapes = [...document.querySelectorAll('.mk-shape')]; const s = shapes[shapes.length - 1]; if (!s) return null;
                const under = (x, y) => { const e = document.elementFromPoint(x, y); return !!(e && (e === s || s.contains(e) || e.closest('.mk-shape') === s)); };
                const r = s.getBoundingClientRect();
                return { count: shapes.length, middle: under((a[0] + c[0]) / 2, (a[1] + c[1]) / 2), inA: under(a[0] + 6, a[1] + 6), inC: under(c[0] - 6, c[1] - 6),
                         outside: under(a[0] - 12, a[1] - 12) || under(c[0] + 12, c[1] + 12),
                         off: [Math.round(r.left - a[0]), Math.round(r.top - a[1]), Math.round(r.right - c[0]), Math.round(r.bottom - c[1])] }; }""", [a, c])
            ok = bool(on_page and got and got["count"] == before + 1 and got["middle"] and got["inA"] and got["inC"] and not got["outside"]
                      and max(abs(v) for v in got["off"]) <= 3)
            # take it away again: select it (a tap in its middle), Delete on its card
            if got and got["count"] > before:
                mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
                await pg.touchscreen.tap(*mid); await pg.wait_for_timeout(600)
                dl = pg.locator(".fcard .fc-btn", has_text="Delete")
                if await dl.count(): await dl.first.tap(); await pg.wait_for_timeout(500)
                got["left"] = await pg.locator(".mk-shape").count()
                ok = ok and got["left"] == before
            return ok, got
        for label, scale in [("at the starting zoom", None), ("zoomed in ×1.6", 1.6)]:
            if scale:
                d = await pg.locator(".rdesk").first.bounding_box()
                n0 = await pg.locator(".mk-shape, .mk-text").count(); w0 = await pg.evaluate(PAGE_W)
                await finger_pinch(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2, scale)
                n1 = await pg.locator(".mk-shape, .mk-text").count(); w1 = await pg.evaluate(PAGE_W)
                report("Mark: a pinch with the Rectangle tool on zooms and leaves no mark (H-25)", n1 == n0 and near(w1, w0 * scale), f"marks {n0} → {n1}, ×{w1 / w0:.2f}")
            for by in ("finger", "mouse"):
                ok, got = await draw(by)
                report(f"Mark: a rectangle drawn by {by} {label} lies under the drag", ok, got)
        w_now = await pg.evaluate(PAGE_W)
        d = await pg.locator(".rdesk").first.bounding_box()
        await host_pinch(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2, w_start / w_now)
        if "on" in ((await tool.get_attribute("class")) or "").split(): await tool.tap()
        if phone: await pg.locator(".ph-nav-b:nth-child(1)").click()
        else: await pg.locator(".lb-mode:nth-of-type(1)").click()
        await pg.wait_for_timeout(800)
        w_end = await pg.evaluate(PAGE_W)
        report("PDF: zoom put back", near(w_end, w_start, 0.03), f"{w_start:.0f} → {w_end:.0f} px")

        # ── Excel and Word: the text size is the zoom ────────────────────────────────────────────
        for name, file, sc_sel, zoomed in [("Excel", "layout.xlsx", ".xv-gridwrap", ".xv-canvas"), ("Word", "discharge.docx", ".dv-stage", ".dv-sheet")]:
            urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(os.path.join(FIX, file)), method="POST")).read()
            await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
            if not await pg.locator(zoomed).count():
                report(f"{name}: the viewer opened", False, file); continue
            zoom = lambda: pg.evaluate("s => parseFloat(document.querySelector(s).style.zoom) || 1", zoomed)
            r = await pg.locator(sc_sel).first.bounding_box(); vx, vy = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2
            z0 = await zoom()
            await finger_pinch(vx, vy, 1.4); z1 = await zoom()
            report(f"{name}: a two-finger pinch ×1.4 makes the text ×1.4", near(z1, z0 * 1.4), f"{z0} → {z1}")
            await ctrl_wheel(vx, vy, 200); z2 = await zoom()
            report(f"{name}: Ctrl + wheel (mouse, trackpad) zooms out", z2 < z1 * 0.9, f"{z1} → {z2}")
            took = await host_pinch(vx, vy, 1.25); z3 = await zoom()
            report(f"{name}: the host's own pinch ×1.25 zooms ×1.25", bool(took) and near(z3, z2 * 1.25), f"{z2} → {z3}")
            sw = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
            report(f"{name}: no sideways page overflow after zooming", sw <= 1, f"{sw} px")
            await host_pinch(vx, vy, z0 / z3)
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').click(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Close").first.click()
            else:
                await pg.locator(".tb-doc").click(); await pg.wait_for_timeout(400)
                await pg.locator(".pop-item", has_text="Close").first.click()
            await pg.wait_for_timeout(1200)
        report("no script errors", not errors, errors[:2])
        await b.close()
    sys.exit(1 if fails else 0)

asyncio.run(main())
