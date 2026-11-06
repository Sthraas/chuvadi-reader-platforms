#!/usr/bin/env python3
# TESTING ONLY (external tool, never shipped). Drives the preview page in headless Chromium with
# touch emulation and saves screenshots, plus any browser console error, for comparison with the
# design frames. Usage:
#   shoot.py <url> <outdir> <scenario> [width height]
# Scenarios: phone-read, phone-mark, phone-protect, phone-arrange, phone-viewsheet, phone-menu,
#            tablet-read, tablet-mark, tablet-arrange, desktop-read
import asyncio, json, sys
from playwright.async_api import async_playwright

url, out, scen = sys.argv[1], sys.argv[2], sys.argv[3]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 392
h = int(sys.argv[5]) if len(sys.argv) > 5 else 816
touch = not scen.startswith("desktop")

async def tap(pg, sel):
    await pg.locator(sel).first.click()
    await pg.wait_for_timeout(700)

async def main():
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch,
                                  device_scale_factor=1)
        pg = await ctx.new_page()
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        await pg.goto(url + "/reader")
        await pg.wait_for_timeout(3500)
        if scen.endswith("-mark"):
            await tap(pg, ".ph-nav-b:nth-child(2), .lb-mode:nth-of-type(2)")
        elif scen.endswith("-protect"):
            await tap(pg, ".ph-nav-b:nth-child(4)")
        elif scen.endswith("-arrange"):
            await tap(pg, ".ph-nav-b:nth-child(3), .lb-mode:nth-of-type(3)")
            await pg.wait_for_timeout(1500)
        elif scen.endswith("-viewsheet"):
            await tap(pg, ".ph-nav-b:nth-child(4)")
            await tap(pg, ".ph-bar .ph-ib[aria-label='More']")
            await tap(pg, ".ph-row:has-text('View')")
        elif scen.endswith("-menu"):
            await tap(pg, ".ph-bar .ph-ib[aria-label='More']")
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f"{out}/{scen}-{w}x{h}.png")
        json.dump(errors, open(f"{out}/{scen}-{w}x{h}.errors.json", "w"), indent=1)
        await b.close()
    print(scen, f"{w}x{h}", "console errors:", len(errors))

asyncio.run(main())
