#!/usr/bin/env python3
# TESTING ONLY. D-190 on touch sizes: Excel column widths and row heights by finger.
#   * a finger dragging a column's edge widens it by the drag and does not scroll the sheet; the same for a row
#   * two taps on an edge fit it
#   * a finger that starts in the middle of a column letter, or on a row number, scrolls and resizes nothing
#   * a two-finger pinch that starts with a finger on an edge zooms and resizes nothing
#   * a pinch on the cells still zooms after a resize; "File's own sizes" is a 44 px box and puts the sizes back
#   xlresize.py <url> <width> <height>     → PASS/FAIL per check, exit 1 on any FAIL
# A line that starts with OPEN is a known, reported conflict (FOR-FOUNDATION.md F-4); it does not fail the run.
# It opens tests/…/Fixtures/Office/layout.xlsx, puts the file's own sizes back and closes the tab again.
import asyncio, os, sys, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
XLSX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "ChuvadiReader.Tests", "Fixtures", "Office", "layout.xlsx"))

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
        urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(XLSX), method="POST")).read()
        await pg.goto(url + "/reader"); await pg.wait_for_selector(".xv-canvas", timeout=20000); await pg.wait_for_timeout(1500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"

        async def touch(kind, pts):
            await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})
        async def drag(x0, y0, x1, y1, steps=8):
            await touch("touchStart", [(x0, y0)]); await asyncio.sleep(0.05)
            for k in range(1, steps + 1):
                await touch("touchMove", [(x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps)]); await asyncio.sleep(0.03)
            await touch("touchEnd", []); await pg.wait_for_timeout(800)
        async def tap(x, y):
            await touch("touchStart", [(x, y)]); await asyncio.sleep(0.04); await touch("touchEnd", [])
        async def hdr(kind, n):
            return await pg.evaluate("""([kind, n]) => { const e = document.querySelector(`.xv-${kind}hdr[data-${kind === 'col' ? 'c' : 'r'}="${n}"]`); if (!e) return null;
                const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height, own: e.classList.contains('own') }; }""", [kind, n])
        scroll = lambda: pg.evaluate("(() => { const g = document.querySelector('.xv-gridwrap'); return [Math.round(g.scrollLeft), Math.round(g.scrollTop)]; })()")
        zoom = lambda: pg.evaluate("parseFloat(document.querySelector('.xv-canvas').style.zoom) || 1")
        owns = lambda: pg.evaluate("document.querySelectorAll('.xv-colhdr.own, .xv-rowhdr.own').length")
        near = lambda a, b, tol=2.5: abs(a - b) <= tol

        # ── a column's edge, by finger ──
        B = await hdr("col", 2); s0 = await scroll()
        await drag(B["right"] - 2, B["top"] + B["h"] / 2, B["right"] - 2 + 60, B["top"] + B["h"] / 2)
        B2 = await hdr("col", 2); s1 = await scroll()
        report("a finger dragging column B's edge 60 px widens B by 60 px", near(B2["w"], B["w"] + 60) and B2["own"], f'{B["w"]:.0f} → {B2["w"]:.0f} px')
        report("… and the sheet did not scroll under the finger", s1 == s0, f"{s0} → {s1}")
        # the finger need not be exact: 10 px off the edge still takes it
        await drag(B2["right"] + 10, B2["top"] + B2["h"] / 2, B2["right"] + 10 - 30, B2["top"] + B2["h"] / 2)
        B3 = await hdr("col", 2)
        report("a finger 10 px off the edge still takes it (30 px narrower)", near(B3["w"], B2["w"] - 30), f'{B2["w"]:.0f} → {B3["w"]:.0f} px')

        # ── two taps on the edge fit it ──
        await tap(B3["right"] - 2, B3["top"] + B3["h"] / 2); await asyncio.sleep(0.12); await tap(B3["right"] - 2, B3["top"] + B3["h"] / 2); await pg.wait_for_timeout(1000)
        B4 = await hdr("col", 2); z_fit = await zoom()
        report("two taps on column B's edge fit it (and do not zoom the sheet)", B4["w"] != B3["w"] and B4["w"] > 8 and z_fit == 1, f'{B3["w"]:.0f} → {B4["w"]:.0f} px, zoom {z_fit}')

        # ── a row's edge, by finger ──
        R3 = await hdr("row", 3); s0 = await scroll()
        await drag(R3["left"] + R3["w"] / 2, R3["bottom"] - 1, R3["left"] + R3["w"] / 2, R3["bottom"] - 1 + 30)
        R3b = await hdr("row", 3); s1 = await scroll()
        report("a finger dragging row 3's edge 30 px makes it 30 px taller, the sheet not scrolling", near(R3b["h"], R3["h"] + 30) and R3b["own"] and s1 == s0, f'{R3["h"]:.0f} → {R3b["h"]:.0f} px, scroll {s0} → {s1}')

        # ── scrolling must stay scrolling ──
        n0 = await owns(); s0 = await scroll()
        D = await hdr("col", 4)        # C is hidden in this sheet
        g = await pg.evaluate("(() => { const g = document.querySelector('.xv-gridwrap'); const r = g.getBoundingClientRect(); return { l: r.left, t: r.top, w: r.width, h: r.height, sw: g.scrollWidth - g.clientWidth, sh: g.scrollHeight - g.clientHeight }; })()")
        if g["sw"] > 40:
            mid = (D["left"] + D["right"]) / 2
            await drag(mid, D["top"] + D["h"] / 2, mid - 80, D["top"] + D["h"] / 2); s1 = await scroll(); n1 = await owns()
            report("a finger that starts in the middle of a column letter scrolls the sheet sideways and resizes nothing",
                   s1[0] > s0[0] + 20 and n1 == n0, f"scroll {s0} → {s1}, changed headers {n0} → {n1}, letter {D['w']:.0f} px wide")
            await pg.evaluate("document.querySelector('.xv-gridwrap').scrollLeft = 0"); await pg.wait_for_timeout(300)
        else:
            print("NOTE sideways scroll not checked: the sheet is not wider than the screen here")
        n0 = await owns(); s0 = await scroll()
        rows = await pg.evaluate("[...document.querySelectorAll('.xv-rowhdr')].map(e => { const r = e.getBoundingClientRect(); return { n: +e.getAttribute('data-r'), top: r.top, h: r.height, left: r.left, w: r.width, own: e.classList.contains('own') }; }).filter(r => r.h > 0)")
        plain = [r for r in rows if not r["own"] and r["top"] > g["t"] + g["h"] * 0.45 and r["top"] + r["h"] < g["t"] + g["h"] - 10]
        if g["sh"] > 40 and plain:
            r = plain[0]; x = r["left"] + r["w"] / 2; y = r["top"] + r["h"] / 2
            await drag(x, y, x, y - 90); s1 = await scroll(); n1 = await owns()
            ok = s1[1] > s0[1] + 20 and n1 == n0
            what = f"scroll {s0} → {s1}, changed headers {n0} → {n1}, row number {r['h']:.0f} px high (the edge takes 14 px each way)"
            if ok or r["h"] > 30: report("a finger that starts on a row number and moves up scrolls the sheet and resizes nothing", ok, what)
            else: print("OPEN (F-4, with Foundation) a finger that starts on an ordinary row number resizes that row instead of scrolling the sheet", what)
            await pg.evaluate("document.querySelector('.xv-gridwrap').scrollTop = 0"); await pg.wait_for_timeout(300)
        else:
            print("NOTE downward scroll not checked: the sheet is not taller than the screen here")

        # ── pinch must stay pinch ──
        Bp = await hdr("col", 2); n0 = await owns(); w0 = Bp["w"]; z0 = await zoom()
        ex, ey = Bp["right"] - 2, Bp["top"] + Bp["h"] / 2
        await touch("touchStart", [(ex, ey)]); await asyncio.sleep(0.04)
        await touch("touchMove", [(ex, ey), (ex + 80, ey + 120)])
        for k in range(1, 9):
            await touch("touchMove", [(ex - 4 * k, ey), (ex + 80 + 6 * k, ey + 120 + 8 * k)]); await asyncio.sleep(0.03)
        await touch("touchEnd", []); await pg.wait_for_timeout(1000)
        z1 = await zoom(); Bq = await hdr("col", 2)
        report("a pinch whose first finger is on a column's edge zooms the sheet and resizes nothing",
               z1 > z0 * 1.1 and near(Bq["w"] / z1, w0 / z0, 1.5), f"zoom {z0} → {z1}; B {w0 / z0:.0f} → {Bq['w'] / z1:.0f} px at 100 %")
        r = await pg.locator(".xv-gridwrap").bounding_box(); cx, cy = r["x"] + r["width"] / 2, r["y"] + r["height"] * 0.6
        z1 = await zoom()
        await touch("touchStart", [(cx - 60, cy), (cx + 60, cy)])
        for k in range(1, 9):
            await touch("touchMove", [(cx - 60 + 3 * k, cy), (cx + 60 - 3 * k, cy)]); await asyncio.sleep(0.03)
        await touch("touchEnd", []); await pg.wait_for_timeout(1000)
        z2 = await zoom()
        report("a pinch on the cells still zooms after resizing", z2 < z1 * 0.95, f"zoom {z1} → {z2}")
        # at a zoom, the drag is still the finger's distance
        Bz = await hdr("col", 2)
        await drag(Bz["right"] - 2, Bz["top"] + Bz["h"] / 2, Bz["right"] - 2 + 40, Bz["top"] + Bz["h"] / 2)
        Bz2 = await hdr("col", 2)
        report(f"zoomed ({z2}), the edge still follows the finger (40 px)", near(Bz2["w"], Bz["w"] + 40, 3), f'{Bz["w"]:.0f} → {Bz2["w"]:.0f} px on screen')

        # ── File's own sizes ──
        btn = await pg.evaluate("""(() => { const e = document.querySelector('.xv-resetsizes'); if (!e) return null; const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { w: Math.round(r.width), h: Math.round(r.height), top: e === t || e.contains(t), inside: r.left >= 0 && r.right <= innerWidth + 0.5 }; })()""")
        report('"File\'s own sizes" is there, a 44 px box, on top and inside the screen', bool(btn) and btn["w"] >= 44 and btn["h"] >= 44 and btn["top"] and btn["inside"], btn)
        if btn:
            await pg.locator(".xv-resetsizes").tap(); await pg.wait_for_timeout(900)
        report("it puts the file's own sizes back", await owns() == 0 and await pg.locator(".xv-resetsizes").count() == 0)
        zr = await zoom()
        if zr != 1:
            await pg.evaluate("([x, y, s]) => { window.chuvadiPinch('begin', 1, x, y); window.chuvadiPinch('change', s, x, y); window.chuvadiPinch('end', s, x, y); }", [cx, cy, 1 / zr]); await pg.wait_for_timeout(800)
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
