#!/usr/bin/env python3
# TESTING ONLY. D-191 on touch sizes: the encoding picker ("Read this file as") for text, Markdown and HTML.
#   * there is a way to it on the phone (⋮) and the tablet (Document ▾): "Text encoding…"
#   * the card: every row and its close control a 44 px box, on top, inside the screen — also with the system
#     bars' insets set (24 px top, 48 px bottom) and with the keyboard up (a shorter window)
#   * choosing works by finger: a Windows-1252 file read as UTF-8 says so on the card; back to Windows-1252
#     the note goes and the accented words are right; Automatic names what it found
#   encpicker.py <url> <width> <height>     → PASS/FAIL per check, exit 1 on any FAIL
# It writes one small Windows-1252 text file to a temp folder, opens it and closes its tab again.
import asyncio, os, shutil, sys, tempfile, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
SHOT = sys.argv[4] if len(sys.argv) > 4 else None

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    tmp = tempfile.mkdtemp(prefix="chvd-enc-"); doc = os.path.join(tmp, "notes-1252.txt")
    open(doc, "wb").write(("Café crème — prix 12 €, naïve façade.\n" + "\n".join(f"line {i} of the notes" for i in range(1, 80))).encode("cp1252"))
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
        async def menu(item):
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                row = pg.locator(".ph-row", has_text=item).first
            else:
                await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
                row = pg.locator(".pop-item", has_text=item).first
            if not await row.count(): return None
            await row.scroll_into_view_if_needed(); bb = await row.bounding_box()
            await row.tap(); await pg.wait_for_timeout(900); return bb
        bb = await menu("Text encoding")
        report('a way to it: "Text encoding…" in the menu, a 44 px row', bool(bb) and bb["height"] >= 44 and await pg.locator(".enc-row").count() >= 5, bb and [round(bb["width"]), round(bb["height"])])
        MEASURE = """(inset) => { const c = document.querySelector('.fcard:has(.enc-list)'); if (!c) return null;
            // the phone shows cards in a bottom sheet that scrolls: the sheet is what must be inside the screen
            const sheet = document.documentElement.dataset.shell === 'phone' ? c.closest('.fcards') : null; const r = (sheet || c).getBoundingClientRect(); const bad = [];
            for (const e of c.querySelectorAll('button')) { e.scrollIntoView({ block: 'nearest' }); const q = e.getBoundingClientRect();
                const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); const top = e === t || e.contains(t);
                const inside = q.left >= 0 && q.right <= innerWidth + 0.5 && q.top >= inset[0] - 0.5 && q.bottom <= innerHeight - inset[1] + 0.5;
                if (q.width < 43.5 || q.height < 43.5 || !top || !inside) bad.push(`${(e.getAttribute('aria-label') || e.textContent).trim().slice(0, 16)} ${Math.round(q.width)}x${Math.round(q.height)}${top ? '' : ' covered'}${inside ? '' : ' outside'}`); }
            return { card: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], view: [innerWidth, innerHeight], n: c.querySelectorAll('button').length,
                     cardInside: r.top >= inset[0] - 0.5 && r.bottom <= innerHeight - inset[1] + 0.5 && r.left >= 0 && r.right <= innerWidth + 0.5, bad }; }"""
        good = lambda m: bool(m) and m["n"] >= 6 and not m["bad"] and m["cardInside"]
        m = await pg.evaluate(MEASURE, [0, 0])
        if SHOT: await pg.screenshot(path=SHOT)
        report("the card: every row and the close control a 44 px box, on top, inside the screen", good(m), m)
        try:
            await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 24, "bottom": 48}}); await pg.wait_for_timeout(500)
            m2 = await pg.evaluate(MEASURE, [24, 48])
            report("with the system bars' insets (24 top, 48 bottom) nothing of the card is under them", good(m2), m2)
            await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {}}); await pg.wait_for_timeout(300)
        except Exception as e:
            report("with the system bars' insets nothing of the card is under them", False, f"could not set insets: {e}")
        short = H - (320 if H > W else 200)
        await pg.set_viewport_size({"width": W, "height": short}); await pg.wait_for_timeout(600)
        m3 = await pg.evaluate(MEASURE, [0, 0])
        report(f"with the keyboard up (window {W}×{short}) every row can still be reached", good(m3), m3)
        await pg.set_viewport_size({"width": W, "height": H}); await pg.wait_for_timeout(500)

        text = lambda: pg.evaluate("(() => { const e = document.querySelector('.tv, .tv-body, .tview, [class*=tv-]') || document.querySelector('.rdesk') || document.body; return e.innerText.slice(0, 200); })()")
        auto = (await pg.locator(".enc-row", has_text="Automatic").first.inner_text()).replace("\n", " ")
        t0 = await text()
        report("Automatic names what it found, and the accented words read right", "1252" in auto and "Café crème" in t0 and "€" in t0, f"{auto!r}; text starts {t0[:40]!r}")
        row = pg.locator(".enc-row", has_text="UTF-8").first
        await row.scroll_into_view_if_needed(); await row.tap(); await pg.wait_for_timeout(1500)
        note = await pg.locator(".fcard .fc-status.err").count(); t1 = await text()
        on = await pg.evaluate("[...document.querySelectorAll('.enc-row.on')].map(e => e.textContent.trim())")
        note_seen = await pg.evaluate("(() => { const e = document.querySelector('.fcard .fc-status.err'); if (!e) return null; e.scrollIntoView({ block: 'nearest' }); const r = e.getBoundingClientRect(); return [e.textContent.trim().slice(0, 70), r.top >= 0 && r.bottom <= innerHeight]; })()")
        report("a tap on UTF-8 reads the file as UTF-8, marks that row, and the card says the bytes that did not fit", note == 1 and on == ["UTF-8"] and "Café" not in t1 and bool(note_seen) and note_seen[1], f"{note_seen}; chosen {on}")
        row = pg.locator(".enc-row", has_text="Windows-1252").last
        await row.scroll_into_view_if_needed(); await row.tap(); await pg.wait_for_timeout(1500)
        t2 = await text(); note = await pg.locator(".fcard .fc-status.err").count()
        report("a tap on Windows-1252 puts it right: the note goes, the words are right", note == 0 and "Café crème" in t2, f"text starts {t2[:40]!r}")
        row = pg.locator(".enc-row", has_text="Automatic").first
        await row.scroll_into_view_if_needed(); await row.tap(); await pg.wait_for_timeout(1200)
        x = pg.locator(".fcard:has(.enc-list) .fcard-x")
        await x.tap(); await pg.wait_for_timeout(500)
        report("the close control closes the card", await pg.locator(".enc-list").count() == 0)
        await menu("Close")
        # Markdown and HTML get the same card
        for name, body in [("readme.md", "# Caf\u00e9\n\nprix 12 \u20ac\n"), ("page.html", "<html><body><h1>Caf\u00e9</h1><p>prix 12 \u20ac</p></body></html>")]:
            f = os.path.join(tmp, name); open(f, "wb").write(body.encode("cp1252"))
            urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(f), method="POST")).read()
            await pg.goto(url + "/reader"); await pg.wait_for_timeout(3000)
            got = await menu("Text encoding")
            mm = await pg.evaluate(MEASURE, [0, 0])
            report(f"{name}: the same card, from the same menu entry", bool(got) and good(mm), mm and mm["bad"])
            x = pg.locator(".fcard:has(.enc-list) .fcard-x")
            if await x.count(): await x.tap(); await pg.wait_for_timeout(400)
            await menu("Close")
        report("no script errors", not errors, errors[:2])
        await b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fails else 0)
asyncio.run(main())
