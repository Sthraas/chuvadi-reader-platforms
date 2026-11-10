#!/usr/bin/env python3
# TESTING ONLY. Phone / tablet checks beyond gestures, from the Android emulator run's findings:
#   * → on a fresh load moves the page and the counter follows (H-8)
#   * the ⋮ menu's Print opens the Print card (H-8)
#   * Redact on a phone opens at fit width: page within the screen, no sideways overflow (H-7)
#   * a tap just outside a small control reaches it (D-37); Arrange keeps Document ▾ (H-18);
#     Find brings the match on screen (H-19)
#   checks.py <url> <width> <height>     → PASS/FAIL per check, exit 1 on any FAIL
import asyncio, sys
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
COUNTER = "(document.querySelector('.ph-pager, .tb-pg-box')?.value || document.querySelector('.ph-pager')?.textContent || '').trim()"

async def main():
    fails = 0
    def report(name, ok, detail):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)

    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        async def fresh():
            ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
            return pg
        pg = await fresh()
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"

        # 1. → on a fresh load (focus on the page body, as after Open with)
        c0 = await pg.evaluate(COUNTER)
        await pg.keyboard.press("ArrowRight"); await pg.wait_for_timeout(1200)
        c1 = await pg.evaluate(COUNTER)
        report("→ moves the page and the counter follows", c1 != c0 and c1[:1] == "2", f"{c0} → {c1}")

        # 1b. The first fit of a new document, measured before its pages render (slow device), must
        #     not use the placeholder (595 px wide, 3/4 of a rendered page): H-9.
        r = await pg.evaluate('''async () => {
            const m = await import('/_content/ChuvadiReader.Ui/js/reader.js');
            const d = document.querySelector('.rdesk'), pages = [...d.querySelectorAll('.rpage')];
            const want = await m.measureFit(d, 'width');
            const saved = pages.map(p => p.innerHTML);
            pages.forEach(p => p.innerHTML = '<div class="rpage-load" style="width:595px;height:842px"></div>');
            setTimeout(() => pages.forEach((p, i) => p.innerHTML = saved[i]), 300);   // the render arrives
            const got = await m.measureFit(d, 'width');
            return { rendered: want, beforeRender: got };
        }''')
        report("fit measured before the pages render matches the rendered fit",
               abs(r["beforeRender"] - r["rendered"]) <= 0.01, r)

        # 1c. Older WebViews (Android API 35) report a CSS-zoomed box unzoomed. Fit must not depend on
        #     it (round 3: Fit page 147 px on a 402 px phone): fake that WebView and compare (H-13).
        r = await pg.evaluate('''async () => {
            const m = await import('/_content/ChuvadiReader.Ui/js/reader.js');
            const d = document.querySelector('.rdesk');
            const want = await m.measureFit(d, 'width');
            const z = parseFloat(getComputedStyle(d).getPropertyValue('--rpage-zoom')) || 1;
            const orig = Element.prototype.getBoundingClientRect;
            Element.prototype.getBoundingClientRect = function () {
                const b = orig.call(this);
                if (!this.closest || !this.closest('.rpage')) return b;
                return new DOMRect(b.left, b.top, b.width / z, b.height / z);   // unzoomed, as API 35
            };
            try { return { modern: want, oldWebView: await m.measureFit(d, 'width') }; }
            finally { Element.prototype.getBoundingClientRect = orig; }
        }''')
        report("fit is the same when the WebView reports zoomed boxes unzoomed (API 35)",
               abs(r["oldWebView"] - r["modern"]) <= 0.01, r)

        # 2. ⋮ (phone) / Document (tablet) → Print opens the Print card
        if phone:
            await pg.locator('.ph-bar button[aria-label="More"]').click(); await pg.wait_for_timeout(500)
            await pg.locator(".ph-row", has_text="Print").first.click()
        else:
            await pg.locator(".tb-doc").click(); await pg.wait_for_timeout(400)
            await pg.locator(".pop-item", has_text="Print").first.click()
        await pg.wait_for_timeout(1200)
        btn = await pg.evaluate("(document.querySelector('section.chvd-card[aria-label=\"Print\"] .footer .primary')?.textContent || '').trim() || null")
        report("Document menu › Print opens the Print card", btn is not None, f"button {btn}")
        await pg.context.close()

        # 3. Redact on a phone opens at fit width
        if phone:
            pg = await fresh()
            await pg.locator(".ph-nav-b:nth-child(4)").click(); await pg.wait_for_timeout(600)
            await pg.locator(".ph-tool:first-child").click(); await pg.wait_for_timeout(3000)
            r = await pg.evaluate('''() => { const d = document.querySelector('.rd-desk'), p = d && d.querySelector('.rpage');
                if (!d || !p) return null; const b = p.getBoundingClientRect();
                return { zoom: d.style.getPropertyValue('--rpage-zoom'), page: Math.round(b.width), left: Math.round(b.left),
                         desk: d.clientWidth, overflow: d.scrollWidth - d.clientWidth }; }''')
            ok = bool(r) and r["overflow"] <= 0 and r["page"] >= r["desk"] - 40 and r["left"] >= 8
            report("Redact opens at fit width", ok, r)
            await pg.context.close()
        # 4. 44 px tap areas (D-37): a tap 20 px below the centre of a small control drawn at desktop size
        #    (Watermark's 29 px "B", so 5 px outside it) lands on nothing; mobile.js gives it to the control.
        pg = await fresh()
        await pg.locator(".ph-nav-b:nth-child(3), .lb-mode:nth-of-type(3)").first.click(); await pg.wait_for_timeout(1500)
        await pg.locator(".desk-more").first.click(); await pg.wait_for_timeout(500)
        await pg.locator(".desk-menu button", has_text="Watermark").first.click(); await pg.wait_for_timeout(900)
        bold = pg.locator(".modal .seg button", has_text="B").first
        bb = await bold.bounding_box()
        before = await bold.get_attribute("class") or ""
        await pg.touchscreen.tap(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2 + 20)
        await pg.wait_for_timeout(600)
        after = await bold.get_attribute("class") or ""
        report("a tap just outside a small control reaches it (44 px area)", ("on" in before.split()) != ("on" in after.split()),
               f"B class '{before}' → '{after}'")
        await pg.context.close()

        # 5. Arrange keeps Document ▾ (tablet top bar / phone ⋮) and its items run in Read (H-18, AT-05, 12f).
        pg = await fresh()
        await pg.locator(".ph-nav-b:nth-child(3), .lb-mode:nth-of-type(3)").first.click(); await pg.wait_for_timeout(1500)
        if phone:
            await pg.locator('.ph-bar button[aria-label="More"]').click(); await pg.wait_for_timeout(500)
            item = pg.locator(".ph-row", has_text="Properties")
        else:
            await pg.locator(".tb-doc").click(); await pg.wait_for_timeout(400)
            item = pg.locator(".pop-item", has_text="Properties")
        has = await item.count() > 0
        if has:
            await item.first.click(); await pg.wait_for_timeout(2500)
        shown = await pg.get_by_text("Document properties").count() > 0
        report("Arrange › Document › Properties opens the Properties card in Read", has and shown and pg.url.endswith("/reader"),
               f"item {has}, card {shown}, {pg.url.rsplit('/', 1)[-1]}")
        await pg.context.close()

        # 6. Find brings the match itself into view, not only its page's top (H-19, AT-09): zoomed in, the
        #    fixture's one "zephyrine" sits near the foot of page 3, more than a screen below the page's top.
        pg = await fresh()
        if phone:
            await pg.locator(".ph-nav-b:nth-child(1)").click(); await pg.wait_for_timeout(800)
        for _ in range(3):
            await pg.keyboard.press("Control+Equal"); await pg.wait_for_timeout(400)
        await pg.wait_for_timeout(800)
        await pg.keyboard.press("Control+f"); await pg.wait_for_timeout(700)
        await pg.locator(".rfind-box").last.fill("zephyrine"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(2500)
        r = await pg.evaluate('''() => { const d = document.querySelector('.rdesk'), h = document.querySelector('.rfind-hl.cur');
            if (!h) return null; const a = d.getBoundingClientRect(), c = h.getBoundingClientRect();
            return { count: document.querySelector('.rfind-count')?.textContent, top: Math.round(c.top), bottom: Math.round(c.bottom),
                     desk: [Math.round(a.top), Math.round(a.bottom)], counter: '' + eval(COUNTER) }; }'''.replace("COUNTER", repr(COUNTER)))
        ok = bool(r) and r["desk"][0] <= r["top"] and r["bottom"] <= r["desk"][1] and r["counter"][:1] == "3"
        report("Find shows the match on screen and the counter is on its page", ok, r)
        # The preview keeps a tab's zoom between runs: put it back to Fit page, so the next run (gestures:
        # swiping needs pages that fit) starts as a fresh install would.
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await pg.keyboard.press("p"); await pg.wait_for_timeout(800)
        await pg.context.close()
        # 7. Tablet: the tools rail shows "TOOLS" and keeps the mode name for screen readers (H-20, D-151);
        #    Mark's Save and Save as new PDF stay in view while the rail scrolls (D-150).
        if not phone:
            pg = await fresh()
            await pg.locator(".lb-mode:nth-of-type(2)").first.click(); await pg.wait_for_timeout(1500)
            r = await pg.evaluate('''async () => { const r = document.querySelector('.srail-tools'), out = [];
                for (const top of [0, 60, 99999]) {
                    r.scrollTop = top; await new Promise(f => setTimeout(f, 150));
                    const rb = r.getBoundingClientRect();
                    const seen = [...r.querySelectorAll('.rb')].filter(x => /^Save/.test(x.getAttribute('aria-label') || ''))
                        .map(x => { const b = x.getBoundingClientRect(), mid = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
                                    return b.top >= rb.top && b.bottom <= rb.bottom + 1 && !!mid && x.contains(mid); });
                    out.push(seen.length === 2 && seen.every(Boolean));
                }
                return { head: r.querySelector('.srail-h').textContent, label: r.getAttribute('aria-label'),
                         scrolls: r.scrollHeight > r.clientHeight, bothSavesInView: out }; }''')
            ok = r["head"] == "TOOLS" and r["label"] == "MARK" and all(r["bothSavesInView"])
            report("tablet Mark rail: TOOLS shown, MARK announced, both Saves in view while it scrolls", ok, r)
            await pg.locator(".lb-mode:nth-of-type(1)").first.click(); await pg.wait_for_timeout(800)   # back to Read
            await pg.context.close()
        await b.close()
    sys.exit(1 if fails else 0)

asyncio.run(main())
