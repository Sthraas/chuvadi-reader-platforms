#!/usr/bin/env python3
# TESTING ONLY. D-198 (patch 33) on touch sizes: a signed PDF shows what its signature states and no verdict.
#   * the banner above the page says "not checked in this version", whole, inside the screen
#   * its Details and × are 44 px boxes, on top, inside the screen; Details opens the Signatures card
#   * the card says "Not checked" and why; its Close and per-signature Details are 44 px boxes; Close closes it
#   * × hides the banner
#   signature.py <url> <width> <height> <signed.pdf>   → PASS/FAIL per check, exit 1 on any FAIL
# <signed.pdf>: any PDF with one CMS signature (a self-signed one does). The script opens it and closes the tab.
import asyncio, os, sys, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H, PDF = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
BOX = """(sel) => [...document.querySelectorAll(sel)].filter(e => e.getBoundingClientRect().width).map(e => { const r = e.getBoundingClientRect();
    const t = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    return { t: (e.getAttribute('aria-label') || e.textContent).trim().slice(0, 14), w: Math.round(r.width), h: Math.round(r.height), top: !!t && (e === t || e.contains(t)),
             inside: r.left >= -0.5 && r.right <= innerWidth + 0.5 && r.top >= -0.5 && r.bottom <= innerHeight + 0.5 }; })"""
ok44 = lambda xs: bool(xs) and all(x["w"] >= 44 and x["h"] >= 44 and x["top"] and x["inside"] for x in xs)

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
        await pg.goto(url + "/reader"); await pg.wait_for_selector(".rsigbanner", timeout=30000); await pg.wait_for_timeout(800)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        line = await pg.evaluate("""(() => { const b = document.querySelector('.rsigbanner .sig-banner'), t = b.querySelector('.text'); const r = b.getBoundingClientRect();
            return { text: t.textContent.trim(), whole: t.scrollWidth <= t.clientWidth + 1, inside: r.left >= 0 && r.right <= innerWidth + 0.5,
                     box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] }; })()""")
        report("the banner says what the signature states and that it is not checked, whole and inside the screen",
               "not checked in this version" in line["text"] and line["whole"] and line["inside"], line)
        bx = await pg.evaluate(BOX, ".rsigbanner .details, .rsigbanner-x")
        report("the banner's Details and × are 44 px boxes, on top, inside the screen", ok44(bx) and len(bx) == 2, bx)
        await pg.locator(".rsigbanner .details").tap(); await pg.wait_for_timeout(1200)
        card = pg.locator('.chvd-card[aria-label="Signatures"]')
        if await card.count():
            txt = (await card.inner_text()).replace("\n", " ")
            report('Details opens the Signatures card; it says "Not checked" and why', "Not checked" in txt and "comes back with the next update" in txt, txt[:160])
            await pg.locator('.chvd-card[aria-label="Signatures"] .link').first.tap(); await pg.wait_for_timeout(500)
            cx = await pg.evaluate(BOX, '.chvd-card[aria-label="Signatures"] .close, .chvd-card[aria-label="Signatures"] .link')
            report("the card's Close and Details / Hide details are 44 px boxes, on top, inside the screen", ok44(cx), cx)
            await pg.locator('.chvd-card[aria-label="Signatures"] .close').tap(); await pg.wait_for_timeout(600)
            report("Close closes the card", await card.count() == 0)
        else:
            report("Details opens the Signatures card", False, "no card")
        await pg.locator(".rsigbanner-x").tap(); await pg.wait_for_timeout(500)
        report("× hides the banner", await pg.locator(".rsigbanner").count() == 0)
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
