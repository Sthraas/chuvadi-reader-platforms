#!/usr/bin/env python3
# TESTING ONLY. D-190 on touch sizes: the card that asks before a tab with unsaved marks closes.
#   * all four answers (Save / Save as… / Discard / Cancel) are there, each a 44 px box, each the top element
#     at its centre, all inside the screen — also with a long file name, with the system bars' insets set
#     (24 px top, 48 px bottom, as an edge-to-edge Android window has), and with the keyboard up (the window
#     320 px shorter in portrait, 200 px in landscape)
#   * Cancel keeps the tab and the mark; Discard closes the tab
#   closecard.py <url> <width> <height> <some.pdf>   → PASS/FAIL per check, exit 1 on any FAIL
# It opens a copy of <some.pdf> under a long name (the copy is made beside this run's temp folder), draws one
# rectangle on it and closes that tab again with Discard.
import asyncio, os, shutil, sys, tempfile, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H, PDF = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
LONG = "Discharge summary and follow-up plan - cardiology outpatient - final signed copy for records 2026-11-16.pdf"

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    tmp = tempfile.mkdtemp(prefix="chvd-closecard-"); doc = os.path.join(tmp, LONG); shutil.copyfile(PDF, doc)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(doc), method="POST")).read()
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        async def touch(kind, pts):
            await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": 0} for x, y in pts]})
        async def ask_close():
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Close").first.tap()
            else:
                await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
                await pg.locator(".pop-item", has_text="Close").first.tap()
            await pg.wait_for_timeout(900)
        MEASURE = """(inset) => { const c = document.querySelector('.closeq'); if (!c) return null; const r = c.getBoundingClientRect();
            const btns = [...c.querySelectorAll('button')].map(e => { const q = e.getBoundingClientRect(); const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
                return { label: e.textContent.trim(), w: Math.round(q.width), h: Math.round(q.height), top: e === t || e.contains(t),
                         inside: q.left >= 0 && q.right <= innerWidth + 0.5 && q.top >= inset[0] && q.bottom <= innerHeight - inset[1] + 0.5 }; });
            const title = c.querySelector('.closeq-title');
            return { box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], view: [innerWidth, innerHeight],
                     inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= inset[0] && r.bottom <= innerHeight - inset[1] + 0.5,
                     titleCut: title.scrollWidth > title.clientWidth + 1, scrolls: c.scrollHeight > c.clientHeight + 1, btns }; }"""
        def good(m, need_inside=True):
            return bool(m) and [x["label"] for x in m["btns"]] == ["Save", "Save as…", "Discard", "Cancel"] and all(x["w"] >= 44 and x["h"] >= 44 and x["top"] and x["inside"] for x in m["btns"]) \
                   and (m["inside"] or not need_inside) and not m["titleCut"]

        # one mark, then ask to close
        if phone:
            await pg.locator(".ph-nav-b:nth-child(2)").tap(); await pg.wait_for_timeout(1200)
            await pg.locator(".ph-strip button", has_text="Box").first.tap()
        else:
            await pg.locator(".lb-mode:nth-of-type(2)").tap(); await pg.wait_for_timeout(1200)
            await pg.locator('.srail .rb[aria-label="Rectangle"]').tap()
        await pg.wait_for_timeout(500)
        pb = await pg.locator(".mk-layer").first.bounding_box(); d = await pg.locator(".rdesk").first.bounding_box()
        x0, y0 = max(pb["x"], d["x"]) + 40, max(pb["y"], d["y"]) + 40
        await touch("touchStart", [(x0, y0)])
        for k in range(1, 9):
            await touch("touchMove", [(x0 + 10 * k, y0 + 7 * k)]); await pg.wait_for_timeout(30)
        await touch("touchEnd", []); await pg.wait_for_timeout(900)
        if await pg.locator(".fcard .fcard-x").count():
            await pg.locator(".fcard .fcard-x").tap(); await pg.wait_for_timeout(500)
        marks = await pg.locator(".mk-shape").count()
        await ask_close()
        m = await pg.evaluate(MEASURE, [0, 0])
        report("the card asks, with its four answers, each 44 px, on top and inside the screen (long file name)", marks == 1 and good(m), m)

        # the system bars: an edge-to-edge window reports them as safe-area insets
        try:
            await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 24, "bottom": 48}})
            await pg.wait_for_timeout(500)
            got = await pg.evaluate("(() => { const e = document.createElement('div'); e.style.cssText = 'position:fixed;top:0;height:env(safe-area-inset-bottom)'; document.body.appendChild(e); const h = e.getBoundingClientRect().height; e.remove(); return h; })()")
            m2 = await pg.evaluate(MEASURE, [24, 48])
            report("with the system bars' insets (24 top, 48 bottom) nothing of the card is under them", got == 48 and good(m2), {"insetSeen": got, "card": m2})
            await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {}})
        except Exception as e:
            report("with the system bars' insets nothing of the card is under them", False, f"could not set insets: {e}")

        # the keyboard up: the window is shorter
        short = H - (320 if H > W else 200)
        await pg.set_viewport_size({"width": W, "height": short}); await pg.wait_for_timeout(600)
        m3 = await pg.evaluate(MEASURE, [0, 0])
        report(f"with the keyboard up (window {W}×{short}) the four answers are still on screen and on top", good(m3), m3)
        await pg.set_viewport_size({"width": W, "height": H}); await pg.wait_for_timeout(500)

        await pg.locator(".closeq button", has_text="Cancel").tap(); await pg.wait_for_timeout(900)
        report("Cancel: the card goes, the tab and its mark stay", await pg.locator(".closeq").count() == 0 and await pg.locator(".mk-shape").count() == 1)
        await ask_close()
        await pg.locator(".closeq button", has_text="Discard").tap(); await pg.wait_for_timeout(1500)
        name_left = await pg.evaluate("(n) => document.body.innerText.includes(n.slice(0, 30))", LONG)
        report("Discard: the tab closes, no card left", await pg.locator(".closeq").count() == 0 and not name_left)
        if phone:
            if await pg.locator(".ph-nav-b").count(): await pg.locator(".ph-nav-b:nth-child(1)").tap()
        elif await pg.locator(".lb-mode").count(): await pg.locator(".lb-mode:nth-of-type(1)").tap()
        await pg.wait_for_timeout(500)
        report("no script errors", not errors, errors[:2])
        await pg.screenshot(path=os.path.join(tmp, "end.png"))
        await b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fails else 0)
asyncio.run(main())
