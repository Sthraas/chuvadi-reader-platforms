#!/usr/bin/env python3
# TESTING ONLY. Patch 28 on touch sizes: turned pages (/Rotate) under Find and Fit, and Find in Excel and Word.
#   * Find on a page with /Rotate 0, 90, 180, 270: the highlight is on the word, turned as the word is, on screen
#   * the Find bar is inside the screen and its controls are 44 px boxes
#   * Fit page: every page, upright or turned, is inside the desk; Fit width: no page wider than the desk
#   * Excel: Find takes the cursor; matches in hidden rows and columns are named above the sheet, inside the screen
#   * Word: Find takes the cursor
#   turned.py <url> <width> <height> <four-turns.pdf>   → PASS/FAIL per check, exit 1 on any FAIL
# <four-turns.pdf>: 4 pages with /Rotate 0, 90, 180, 270 and the word "rotmark<turn>" on each. The script opens
# it, tests/…/Fixtures/Office/layout.xlsx and discharge.docx, and closes the three tabs again.
import asyncio, os, sys, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H, PDF = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
FIX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "ChuvadiReader.Tests", "Fixtures", "Office"))

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        async def open_file(path):
            urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(path), method="POST")).read()
            await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        await open_file(PDF)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        async def open_find():
            if await pg.locator(".rfind-box").count(): return
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Find").first.tap()
            else:
                await pg.locator('.srail .rb[aria-label="Find"]').first.tap()
            await pg.wait_for_selector(".rfind-box", timeout=5000); await pg.wait_for_timeout(400)
        async def close_tab():
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').click(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Close").first.click()
            else:
                await pg.locator(".tb-doc").click(); await pg.wait_for_timeout(400)
                await pg.locator(".pop-item", has_text="Close").first.click()
            await pg.wait_for_timeout(1200)
        focused = "document.activeElement && document.activeElement.classList.contains('rfind-box')"

        # ── Find on turned pages (F-1) ───────────────────────────────────────────────────────────
        await pg.wait_for_selector(".rpage svg", timeout=20000)
        for turn in (0, 90, 180, 270):
            await open_find()
            await pg.fill(".rfind-box", f"rotmark{turn}"); await pg.press(".rfind-box", "Enter"); await pg.wait_for_timeout(3000)
            got = await pg.evaluate("""(word) => {
                const hl = document.querySelector('.rfind-hl.cur'); if (!hl) return { noHighlight: true, count: document.querySelectorAll('.rfind-hl').length };
                const wrap = hl.closest('.rpage-wrap'); const texts = [...wrap.querySelectorAll('svg text, svg tspan')].filter(t => t.textContent.includes(word));
                if (!texts.length) return { noText: true };
                const t = texts[texts.length - 1].getBoundingClientRect(), h = hl.getBoundingClientRect(), d = document.querySelector('.rdesk').getBoundingClientRect();
                const cx = h.left + h.width / 2, cy = h.top + h.height / 2;
                const top = document.elementFromPoint(cx, cy);
                return { onWord: cx > t.left - 3 && cx < t.right + 3 && cy > t.top - 3 && cy < t.bottom + 3, sideways: h.height > h.width, wordSideways: t.height > t.width,
                         onScreen: cy > d.top && cy < d.bottom && cx > d.left && cx < d.right && cx < innerWidth && cy < innerHeight,
                         notCovered: !!(top && top.closest('.rpage-wrap')) }; }""", f"rotmark{turn}")
            ok = bool(got.get("onWord") and got["sideways"] == got["wordSideways"] and got["onScreen"] and got["notCovered"])
            report(f"Find, /Rotate {turn}: the highlight is on the word, turned as the word is, on screen and not covered", ok, got)
        bar = await pg.evaluate("""(() => { const b = document.querySelector('.rfind').getBoundingClientRect();
            const small = [...document.querySelectorAll('.rfind input, .rfind button')].map(e => { const r = e.getBoundingClientRect(); return [e.className.split(' ')[0], Math.round(r.width), Math.round(r.height)]; }).filter(x => x[1] < 44 || x[2] < 44);
            return { bar: [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)], inside: b.left >= 0 && b.right <= innerWidth + 0.5, small }; })()""")
        report("Find bar: inside the screen, every control at least 44 px", bar["inside"] and not bar["small"], bar)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)

        # ── Fit on turned pages (F-2) ────────────────────────────────────────────────────────────
        sizes = """(() => { const d = document.querySelector('.rdesk'); return { desk: [d.clientWidth, d.clientHeight], over: d.scrollWidth - d.clientWidth,
            pages: [...document.querySelectorAll('.rpage-wrap')].map(w => { const s = w.querySelector('.rpage svg') || w; const r = s.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }) }; })()"""
        await pg.locator(".rdesk").first.tap(position={"x": 5, "y": 5}); await pg.keyboard.press("p"); await pg.wait_for_timeout(1800)
        fp = await pg.evaluate(sizes)
        report("Fit page: every page, upright or turned, is inside the desk; nothing runs off sideways",
               len(fp["pages"]) == 4 and all(w <= fp["desk"][0] and h <= fp["desk"][1] for w, h in fp["pages"]) and fp["over"] <= 1, fp)
        await pg.keyboard.press("w"); await pg.wait_for_timeout(1800)
        fw = await pg.evaluate(sizes)
        report("Fit width: every page is as wide as the desk allows, none wider", all(fw["desk"][0] - 64 <= w <= fw["desk"][0] for w, h in fw["pages"]) and fw["over"] <= 1, fw)
        await pg.keyboard.press("p"); await pg.wait_for_timeout(800)
        await close_tab()

        # ── Excel: Find takes the cursor; hidden matches are named (D-188) ───────────────────────
        await open_file(os.path.join(FIX, "layout.xlsx"))
        await pg.wait_for_selector(".xv-canvas", timeout=20000)
        await open_find()
        report("Excel: the Find box has the cursor when Find opens", await pg.evaluate(focused))
        await pg.fill(".rfind-box", "hidden"); await pg.press(".rfind-box", "Enter"); await pg.wait_for_timeout(1300)
        line = await pg.evaluate("""(() => { const e = document.querySelector('.xv-hiddenhits'); if (!e) return null; const r = e.getBoundingClientRect();
            const g = document.querySelector('.xv-gridwrap').getBoundingClientRect();
            const top = document.elementFromPoint(r.left + 20, r.top + r.height / 2);
            return { text: e.textContent.trim(), box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= 0,
                     cut: e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1, seen: top === e || e.contains(top), grid: Math.round(g.height),
                     pageOver: document.documentElement.scrollWidth - innerWidth }; })()""")
        report("Excel: matches in a hidden row and a hidden column are named above the sheet",
               bool(line) and line["text"] == "2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)", line and line["text"])
        report("Excel: that line is whole, inside the screen, not covered, and the grid keeps room",
               bool(line) and line["inside"] and not line["cut"] and line["seen"] and line["grid"] >= 120 and line["pageOver"] <= 1, line)
        await pg.fill(".rfind-box", "Title"); await pg.press(".rfind-box", "Enter"); await pg.wait_for_timeout(1000)
        report("Excel: no line when no match is hidden", await pg.locator(".xv-hiddenhits").count() == 0)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await close_tab()

        # ── Word: Find takes the cursor ──────────────────────────────────────────────────────────
        await open_file(os.path.join(FIX, "discharge.docx"))
        await pg.wait_for_selector(".dv-sheet", timeout=20000)
        await open_find()
        report("Word: the Find box has the cursor when Find opens", await pg.evaluate(focused))
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await close_tab()
        report("no script errors", not errors, errors[:2])
        await b.close()
    sys.exit(1 if fails else 0)
asyncio.run(main())
