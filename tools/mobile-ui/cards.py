#!/usr/bin/env python3
# TESTING ONLY. The 44 px rule on the cards and pages the box audit (boxes.py) does not open (AT-28):
#   the Export as image card, the Press card (with Custom and a target size on), the Merge page, the Split page.
#   cards.py <url> <width> <height> [shots-dir]   → one PASS/FAIL line per place, exit 1 on any FAIL
# A control is a button, link, input, select, or a label that holds a tick box or a radio (the label is the
# target; the 13 px box inside it is not counted). Every control must be at least 44 × 44 px, the top element
# at its centre once scrolled to, and inside the screen.
import asyncio, os, sys
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
SHOTS = sys.argv[4] if len(sys.argv) > 4 else None
AUDIT = """(root) => { const host = document.querySelector(root); if (!host) return null;
    const out = [];
    for (const e of host.querySelectorAll('button, a[href], input, select, label')) {
        if (e.tagName === 'LABEL' && !e.querySelector('input[type=checkbox], input[type=radio]')) continue;
        if (e.tagName === 'INPUT' && (e.type === 'checkbox' || e.type === 'radio') && e.closest('label')) continue;
        if (!e.getBoundingClientRect().width) continue;
        e.scrollIntoView({ block: 'center', inline: 'nearest' });      // a control further down a long card or page is brought up first
        const r = e.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
        const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.pointerEvents === 'none') continue;
        const name = (e.getAttribute('aria-label') || e.textContent || e.type || '').trim().replace(/\\s+/g, ' ').slice(0, 22);
        const t = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
        const top = !!t && (t === e || e.contains(t) || t.contains(e) && t.tagName === 'LABEL');
        const inside = r.left >= -0.5 && r.right <= innerWidth + 0.5;
        const onScreen = r.top < innerHeight && r.bottom > 0;
        if (r.width < 43.5 || r.height < 43.5 || !inside || (onScreen && !top && !e.disabled))
            out.push(`${name || e.tagName} ${Math.round(r.width)}x${Math.round(r.height)}${inside ? '' : ' off-screen'}${onScreen && !top && !e.disabled ? ' covered' : ''}`);
    }
    return { n: host.querySelectorAll('button, a[href], input, select').length, bad: out }; }"""

async def main():
    fails = 0
    def report(name, got):
        nonlocal fails
        ok = bool(got) and got["n"] > 0 and not got["bad"]
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, f'{got["n"]} controls' if ok else got)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page()
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        async def shot(n):
            if SHOTS: os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, f"{n}-{W}x{H}.png"))
        async def menu(item):
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                row = pg.locator(".ph-row", has_text=item).first
            else:
                await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
                row = pg.locator(".pop-item", has_text=item).first
            if not await row.count(): return False
            await row.tap(); await pg.wait_for_timeout(900); return True

        if await menu("Export"):
            await shot("export"); report("Export as image card", await pg.evaluate(AUDIT, ".rdlg"))
            if await pg.locator(".rdlg-x").count(): await pg.locator(".rdlg-x").tap(); await pg.wait_for_timeout(400)
        else: fails += 1; print("FAIL Export as image card: no way to it in the menu")
        if await menu("Press") or await menu("Reduce"):
            custom = pg.locator(".rdlg-chip", has_text="Custom")
            if await custom.count(): await custom.tap(); await pg.wait_for_timeout(300)
            tick = pg.locator(".rdlg-check", has_text="target size")
            if await tick.count(): await tick.tap(); await pg.wait_for_timeout(300)
            await shot("press"); report("Press card (Custom, target size on)", await pg.evaluate(AUDIT, ".rdlg"))
            if await pg.locator(".rdlg-x").count(): await pg.locator(".rdlg-x").tap(); await pg.wait_for_timeout(400)
        else: fails += 1; print("FAIL Press card: no way to it in the menu")
        for name, path, root in [("Merge page", "/merge", ".tool"), ("Split page", "/split", ".tool")]:
            await pg.goto(url + path); await pg.wait_for_timeout(2500)
            if path == "/merge":
                add = pg.locator(".tbtn", has_text="Add open documents")
                if await add.count(): await add.tap(); await pg.wait_for_timeout(900)
            if path == "/split":
                use = pg.locator(".tbtn", has_text="Use current")
                if await use.count(): await use.tap(); await pg.wait_for_timeout(1200)
                rng = pg.locator(".smode", has_text="Extract a page range")
                if await rng.count(): await rng.tap(); await pg.wait_for_timeout(500)
            await shot(name.split()[0].lower()); report(name, await pg.evaluate(AUDIT, root))
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(1500)
        await b.close()
    sys.exit(1 if fails else 0)
asyncio.run(main())
