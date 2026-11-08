#!/usr/bin/env python3
# TESTING ONLY. Phone / tablet checks beyond gestures, from the Android emulator run's findings:
#   * → on a fresh load moves the page and the counter follows (H-8)
#   * the ⋮ menu's Print opens the Print card (H-8)
#   * Redact on a phone opens at fit width: page within the screen, no sideways overflow (H-7)
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
        await b.close()
    sys.exit(1 if fails else 0)

asyncio.run(main())
