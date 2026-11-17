#!/usr/bin/env python3
# TESTING ONLY. D-195 (F-3) on touch sizes: the Find bar steps to the bottom when it would cover the match.
# Opens tools/PixelProof/fixtures/top.pdf (the word "topmark" three times across the top line of each of four
# pages, and once mid-page) and steps through all 16 matches, in the layout the size opens in and again in
# Fit width. At every step:
#   * the current match is on screen in the page area and not under the Find bar
#   * the Find bar is inside the screen, not under the phone's bottom bar or tool strip, the top element where
#     it is, and its controls are 44 px boxes (in its own place and aside)
#   findaside.py <url> <width> <height>     → PASS/FAIL per layout, exit 1 on any FAIL
import asyncio, os, sys, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
PDF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PixelProof", "fixtures", "top.pdf"))
STEP = """() => { const h = document.querySelector('.rfind-hl.cur'), d = document.querySelector('.rdesk'), f = document.querySelector('.rfind'); if (!h || !f) return null;
    const a = h.getBoundingClientRect(), c = d.getBoundingClientRect(), q = f.getBoundingClientRect();
    const covers = [...document.querySelectorAll('.ph-nav, .ph-strip, .ph-bar, .ph-fab, .tb-top, .lb')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height && getComputedStyle(e).visibility !== 'hidden'; })
        .map(e => e.getBoundingClientRect());
    // what is on screen above or below the desk counts as covering the match too
    const visTop = Math.max(c.top, 0), visBottom = Math.min(c.bottom, innerHeight);
    const midTop = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    const small = [...f.querySelectorAll('input, button')].map(e => { const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return { n: e.className.split(' ')[0], w: Math.round(r.width), h: Math.round(r.height), top: e === t || e.contains(t) }; }).filter(x => x.w < 44 || x.h < 44 || !x.top);
    return { page: h.closest('[data-page]')?.getAttribute('data-page'), aside: f.classList.contains('aside'),
        vis: a.top >= visTop - 1 && a.bottom <= visBottom + 1 && a.left >= c.left - 1 && a.right <= c.right + 1,
        under: a.left < q.right && a.right > q.left && a.top < q.bottom && a.bottom > q.top,
        barInside: q.left >= -0.5 && q.right <= innerWidth + 0.5 && q.top >= -0.5 && q.bottom <= innerHeight + 0.5,
        barOver: covers.some(r => r.left < q.right && r.right > q.left && r.top < q.bottom && r.bottom > q.top) && !(f.contains(midTop)),
        barTop: !!midTop && f.contains(midTop), small,
        bar: [Math.round(q.left), Math.round(q.top), Math.round(q.width), Math.round(q.height)] }; }"""

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
        urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(PDF), method="POST")).read()
        await pg.goto(url + "/reader"); await pg.wait_for_selector(".rdesk .rpage svg", timeout=30000); await pg.wait_for_timeout(1500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        async def open_find():
            if await pg.locator(".rfind-box").count(): return
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Find").first.tap()
            else:
                await pg.locator('.srail .rb[aria-label="Find"]').first.tap()
            await pg.wait_for_selector(".rfind-box", timeout=5000); await pg.wait_for_timeout(400)
        for layout in ("as it opens", "Fit width"):
            if layout == "Fit width":
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
                await pg.locator(".rdesk").first.tap(position={"x": 5, "y": 5}); await pg.keyboard.press("w"); await pg.wait_for_timeout(1500)
            snap = await pg.evaluate("getComputedStyle(document.querySelector('.rdesk')).scrollSnapType")
            await open_find()
            await pg.fill(".rfind-box", "topmark"); await pg.press(".rfind-box", "Enter"); await pg.wait_for_timeout(3000)
            steps, bad, aside, where = 0, [], 0, []
            for i in range(16):
                r = await pg.evaluate(STEP)
                if r:
                    steps += 1; aside += r["aside"]
                    ok = r["vis"] and not r["under"] and r["barInside"] and not r["barOver"] and r["barTop"] and not r["small"]
                    where.append(f"p{r['page']}{'A' if r['aside'] else ''}{'' if ok else '!'}")
                    if not ok: bad.append({k: r[k] for k in ("page", "aside", "vis", "under", "barInside", "barOver", "barTop", "small", "bar")})
                await pg.press(".rfind-box", "Enter"); await pg.wait_for_timeout(1300)
            report(f"{layout} (snap: {snap}): 16 matches, none off screen or under the bar; the bar inside, on top, 44 px controls (aside {aside} times)",
                   steps == 16 and not bad, " ".join(where) + ("  " + str(bad[:2]) if bad else ""))
        if phone:
            await pg.evaluate("document.querySelector('.rfind').classList.add('aside')"); await pg.wait_for_timeout(300)
            r = await pg.evaluate(STEP)
            report("phone: were the bar asked to step aside, it stays in the top bar's place, off the bottom bar", bool(r) and r["bar"][1] == 0 and not r["barOver"], r and r["bar"])
            await pg.evaluate("document.querySelector('.rfind').classList.remove('aside')")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await pg.keyboard.press("p"); await pg.wait_for_timeout(600)
        if phone:
            await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
            await pg.locator(".ph-row", has_text="Close").first.tap()
        else:
            await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
            await pg.locator(".pop-item", has_text="Close").first.tap()
        await pg.wait_for_timeout(1000)
        report("no script errors", not errors, errors[:2])
        await b.close()
    sys.exit(1 if fails else 0)
asyncio.run(main())
