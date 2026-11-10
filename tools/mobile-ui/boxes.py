#!/usr/bin/env python3
# TESTING ONLY. Box-size audit, as Android Test measures AT-06 (and as TalkBack and the Accessibility Scanner
# do): every visible, enabled control's own box, on each main screen, should be at least 44 x 44 CSS px.
#   boxes.py <url> <W> <H>     → one line per control class under 44 px, exit 1 if any
import asyncio, sys
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
JS = '''() => { const out = {};
  for (const e of document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea, summary, [role=button]')) {
    if (e.disabled || e.closest('[hidden]')) continue;
    const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) continue;
    const s = getComputedStyle(e); if (s.visibility === 'hidden' || s.pointerEvents === 'none') continue;
    if (r.width >= 43.95 && r.height >= 43.95) continue;
    const k = (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/)[0] : e.tagName.toLowerCase())
      + (e.type && e.tagName === 'INPUT' ? '[' + e.type + ']' : '');
    const v = Math.round(r.width * 10) / 10 + 'x' + Math.round(r.height * 10) / 10;
    (out[k] = out[k] || new Set()).add(v); }
  return Object.entries(out).map(([k, s]) => k + ' ' + [...s].slice(0, 3).join(', ')); }'''
async def main():
    bad = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        async def screen(name, path, steps=()):
            nonlocal bad
            ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); await pg.goto(url + path); await pg.wait_for_timeout(3000)
            for sel in steps:
                loc = pg.locator(sel)
                if await loc.count():
                    try: await loc.first.click(timeout=3000)
                    except Exception: pass
                    await pg.wait_for_timeout(900)
            for line in await pg.evaluate(JS):
                bad += 1; print(f"{W}x{H} {name}: {line}")
            await ctx.close()
        mode = lambda n: f".ph-nav-b:nth-child({n}), .lb-mode:nth-of-type({n})"
        await screen("home", "/")
        await screen("library", "/library")
        await screen("settings", "/settings")
        await screen("read", "/reader", [mode(1)])
        await screen("mark", "/reader", [mode(2)])
        await screen("arrange", "/reader", [mode(3)])
        await screen("shelf", "/reader", [mode(3), ".bench-shelf:not(.chvd-open) .shelf-head"])
        await screen("deskmenu", "/reader", [mode(3), ".desk-more"])
        await screen("protect", "/reader", [mode(4)])
        await screen("menu", "/reader", [mode(1), '.ph-bar button[aria-label="More"], .tb-doc'])
        await pg_done() if False else None
        await b.close()
    print(f"{W}x{H}: {bad} control classes under 44 px")
    sys.exit(1 if bad else 0)
asyncio.run(main())
