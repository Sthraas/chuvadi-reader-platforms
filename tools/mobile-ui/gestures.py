#!/usr/bin/env python3
# TESTING ONLY. Real touch input through Chrome's input pipeline (CDP Input.dispatchTouchEvent) with
# mobile emulation, so the browser's own pan / touch-action / pointercancel behaviour applies — the
# failures the Android emulator found (BUILD-LOG steps 32-34) reproduce here.
#   gestures.py <url> <width> <height>     → prints PASS/FAIL per gesture, exit 1 on any FAIL
import asyncio, sys
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
JITTER = len(sys.argv) > 4 and sys.argv[4] == "jitter"   # long-press with a shaky hold
STATE = '''() => { const d=document.querySelector('.rdesk'), p=d&&d.querySelector('.rpage');
  const c=document.querySelector('.ph-pager, .tb-pg-box');
  return { counter: c ? (c.value || c.textContent).trim() : '', page: p ? Math.round(p.getBoundingClientRect().width) : 0,
           deskW: d ? d.clientWidth : 0, sw: d ? d.scrollWidth : 0 }; }'''

async def touch(cdp, kind, pts):
    await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})

async def drag(cdp, x0, y0, x1, y1, steps=8, hold_ms=0, step_ms=16, jitter=False):
    await touch(cdp, "touchStart", [(x0, y0)])
    if hold_ms and jitter:
        # A real finger isn't still: tiny moves (under the 10 px tap slop) while holding.
        for k in range(int(hold_ms / 50)):
            await touch(cdp, "touchMove", [(x0 + (2 if k % 2 else -2), y0 + (3 if k % 3 else 0))])
            await asyncio.sleep(0.05)
    elif hold_ms: await asyncio.sleep(hold_ms / 1000)
    for k in range(1, steps + 1):
        await touch(cdp, "touchMove", [(x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps)])
        await asyncio.sleep(step_ms / 1000)
    await touch(cdp, "touchEnd", [])

async def main():
    fails = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        await pg.add_init_script('''window.__ev=[];for(const t of ['pointerdown','pointercancel','pointerup'])
            document.addEventListener(t,e=>{if(e.pointerType==='touch')window.__ev.push(t)},true);''')
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        phone = await pg.evaluate("document.documentElement.getAttribute('data-shell')") == "phone"
        if phone:
            await pg.locator(".ph-nav-b:nth-child(1)").click(); await pg.wait_for_timeout(800)
        cx, cy = W // 2, H // 2

        def report(name, ok, detail):
            nonlocal fails
            fails += 0 if ok else 1
            print(("PASS " if ok else "FAIL ") + name, detail)

        # 1. swipe → next page
        s0 = await pg.evaluate(STATE)
        await pg.evaluate("window.__ev=[]")
        await drag(cdp, cx + 120, cy, cx - 120, cy, steps=6, step_ms=12)
        await pg.wait_for_timeout(1200)
        s1 = await pg.evaluate(STATE)
        report("swipe → next page", s1["counter"] != s0["counter"], f'{s0["counter"]} → {s1["counter"]}; events {await pg.evaluate("window.__ev")}')

        # 2. double-tap zooms in, a second double-tap returns (handout: double-tap = zoom)
        w0 = (await pg.evaluate(STATE))["page"]
        for _ in range(2):
            await touch(cdp, "touchStart", [(cx, cy)]); await touch(cdp, "touchEnd", []); await asyncio.sleep(0.06)
        await pg.wait_for_timeout(900); w1 = (await pg.evaluate(STATE))["page"]
        for _ in range(2):
            await touch(cdp, "touchStart", [(cx, cy)]); await touch(cdp, "touchEnd", []); await asyncio.sleep(0.06)
        await pg.wait_for_timeout(900); w2 = (await pg.evaluate(STATE))["page"]
        report("double-tap zooms in and back", w1 > w0 * 1.5 and abs(w2 - w0) <= 2, f"{w0} → {w1} → {w2} px")

        # 2b. a two-finger pinch that doubles the finger spread zooms the page about 2× — once, not twice
        #     (the old mobile.js pinch ran on top of reader.js's own)
        p0 = (await pg.evaluate(STATE))["page"]
        await touch(cdp, "touchStart", [(cx - 40, cy), (cx + 40, cy)])
        for k in range(1, 11):
            d = 40 + 40 * k / 10
            await touch(cdp, "touchMove", [(cx - d, cy), (cx + d, cy)]); await asyncio.sleep(0.016)
        await touch(cdp, "touchEnd", [])
        await pg.wait_for_timeout(1000)
        p1 = (await pg.evaluate(STATE))["page"]
        ratio = p1 / p0 if p0 else 0
        report("pinch ×2 spread zooms ≈2× (single handler)", 1.6 <= ratio <= 2.4, f"{p0} → {p1} px (×{ratio:.2f})")

        # 3. fit page never wider than fit width, and stable (phone View sheet)
        if phone:
            async def fit(row):
                await pg.locator(".ph-bar .ph-ib[aria-label='More']").click(); await pg.wait_for_timeout(300)
                await pg.locator(".ph-row:has-text('View')").click(); await pg.wait_for_timeout(300)
                await pg.locator(f".ph-sheet .ph-row:has-text('{row}')").click(); await pg.wait_for_timeout(900)
                await pg.locator(".ph-sheet-a").click(); await pg.wait_for_timeout(400)
                return await pg.evaluate(STATE)
            fw = await fit("Fit width"); fp = await fit("Fit page"); fw2 = await fit("Fit width")
            ok = fp["page"] <= fw["page"] and fp["sw"] <= fp["deskW"] + 1 and fw["sw"] <= fw["deskW"] + 1 and fw2["page"] == fw["page"]
            report("fit page ≤ fit width, no overflow, stable", ok, f'width {fw["page"]} page {fp["page"]} width {fw2["page"]} (desk {fw["deskW"]}, overflow {fp["sw"] - fp["deskW"]})')

        # 4. Arrange: long-press a Shelf page and drag it onto the first desk
        if phone:
            await pg.locator(".ph-nav-b:nth-child(3)").click()
        else:
            await pg.locator(".lb-mode:nth-of-type(3)").click()
        await pg.wait_for_timeout(1800)
        before = await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length")
        if phone:
            await pg.locator(".bench-shelf .shelf-head").first.tap(); await pg.wait_for_timeout(700)
        # Bring a Shelf page into view inside the sheet (in phone landscape the sheet's tools come first).
        await pg.evaluate("document.querySelector('[data-shelf]')?.scrollIntoView({block: 'center'})")
        await pg.wait_for_timeout(400)
        src = await pg.locator("[data-shelf]").first.bounding_box()
        dst = await pg.locator(".desk .desk-drop, .desk").first.bounding_box()
        await pg.evaluate("window.__ev=[]")
        if src and dst:
            await drag(cdp, src["x"] + src["width"] / 2, src["y"] + src["height"] / 2,
                       dst["x"] + dst["width"] / 2, dst["y"] + min(60, dst["height"] / 2), steps=14, hold_ms=650, step_ms=30,
                       jitter=JITTER)
        await pg.wait_for_timeout(1200)
        after = await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length")
        ev = await pg.evaluate("window.__ev")
        report("long-press drag Shelf page → desk", after > before and "pointercancel" not in ev, f"desk pages {before} → {after}; events {ev}")
        await b.close()
    sys.exit(1 if fails else 0)

asyncio.run(main())
