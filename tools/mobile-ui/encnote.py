#!/usr/bin/env python3
# TESTING ONLY. D-205 (F-5, option B) on touch sizes: where the text encoding shows outside the picker.
#   * phone: the ⋮ sheet's "Text encoding…" row shows the encoding as its value; while the bytes do not fit it,
#     a red note under the label ("18 bytes don't fit UTF-8"); no note otherwise. The row a 44 px box, on top.
#   * tablet: no chip while there is no note; with a note, a small chip beside the page box — a 44 px box, on top,
#     inside the screen, not over the page box, the Document button or Search; a tap opens "Read this file as";
#     choosing Windows-1252 takes the chip away again. Narrower than 1100 px the chip shows the encoding's name only
#     (the note would reach the Document button); narrower than 760 px it sits under the top bar.
#   encnote.py <url> <width> <height> [shot.png]   → PASS/FAIL per check, exit 1 on any FAIL
# Needs the H-32 hook (proposal/mobile-ui-hooks-17.patch) applied to the preview. Writes one small Windows-1252
# text file to a temp folder, opens it and closes its tab again.
import asyncio, os, shutil, sys, tempfile, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
SHOT = sys.argv[4] if len(sys.argv) > 4 else None

CHIP = """() => { const c = document.querySelector('.tb-encchip'); if (!c) return null; const r = c.getBoundingClientRect();
  const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const box = e => { if (!e) return null; const q = e.getBoundingClientRect(); return [q.left, q.top, q.right, q.bottom]; };
  const over = q => !!q && r.left < q[2] - 0.5 && r.right > q[0] + 0.5 && r.top < q[3] - 0.5 && r.bottom > q[1] + 0.5;
  const pager = box(document.querySelector('.tb-pager')), doc = box(document.querySelector('.tb-doc'));
  const others = [...document.querySelectorAll('.tb-bar button, .tb-bar a, .tb-bar input, header button')].filter(e => !c.contains(e) && e.offsetParent);
  return { box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], text: c.innerText.trim(),
           label: c.getAttribute('aria-label'), top: !!t && c.contains(t),
           inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= 0 && r.bottom <= innerHeight + 0.5,
           beside: !!pager && r.left >= pager[2] && r.left - pager[2] <= 24 && Math.abs((r.top + r.bottom) / 2 - (pager[1] + pager[3]) / 2) <= 4,
           overPager: over(pager), overDoc: over(doc), overOther: others.filter(e => over(box(e))).map(e => e.getAttribute('aria-label') || e.textContent.trim()).slice(0, 3) }; }"""

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    tmp = tempfile.mkdtemp(prefix="chvd-encnote-"); doc = os.path.join(tmp, "encnote-1252.txt")
    open(doc, "wb").write(("Café crème — prix 12 €, naïve façade.\n" + "\n".join(f"line {i} of the notes" for i in range(1, 80))).encode("cp1252"))
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        urllib.request.urlopen(urllib.request.Request(url + "/__preview/open?path=" + urllib.parse.quote(doc), method="POST")).read()
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"

        async def menu():
            if phone: await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(600)
            else: await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(500)
        async def close_menu():
            scrim = pg.locator(".ph-scrim")
            if phone and await scrim.count():
                await scrim.first.tap(position={"x": 20, "y": 20}); await pg.wait_for_timeout(600)
        async def choose(name):
            await pg.locator(".enc-row", has_text=name).first.tap(); await pg.wait_for_timeout(1500)
            x = pg.locator(".fcard:has(.enc-list) .fcard-x")
            if await x.count(): await x.tap(); await pg.wait_for_timeout(600)
        async def open_picker():
            await menu(); await pg.locator(".ph-row" if phone else ".pop-item", has_text="Text encoding").first.tap(); await pg.wait_for_timeout(900)
        async def row():
            await menu()
            r = pg.locator(".ph-row", has_text="Text encoding").first; await r.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
            return await r.evaluate("""r => { const q = r.getBoundingClientRect(); const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
                const v = r.querySelector('.ph-row-v'), n = r.querySelector('.ph-row-note');
                return { value: v ? v.textContent.trim() : null, note: n ? n.textContent.trim() : '', warn: r.classList.contains('ph-row-warn'),
                         w: Math.round(q.width), h: Math.round(q.height), top: !!t && r.contains(t), label: r.getAttribute('aria-label'),
                         cut: !!n && n.scrollWidth > n.clientWidth + 1 }; }""")

        if phone:
            m = await row()
            report("phone: before choosing, the row shows the encoding it read and no note",
                   bool(m["value"]) and not m["note"] and not m["warn"] and m["w"] >= 44 and m["h"] >= 44 and m["top"], m)
            await close_menu(); await open_picker(); await choose("UTF-8")
            m = await row()
            report("phone: read as UTF-8, the row's value is UTF-8 and the red note says what doesn't fit",
                   m["value"] == "UTF-8" and "don't fit UTF-8" in m["note"] and m["warn"] and not m["cut"], m)
            report("phone: the row is still a 44 px box, on top, and says both aloud",
                   m["w"] >= 44 and m["h"] >= 44 and m["top"] and "UTF-8" in (m["label"] or "") and "fit" in (m["label"] or ""), m["label"])
            if SHOT: await pg.screenshot(path=SHOT)
            await close_menu(); await open_picker(); await choose("Windows-1252")
            m = await row()
            report("phone: back to Windows-1252, the value follows and the note goes", m["value"] == "Windows-1252" and not m["note"] and not m["warn"], m)
            await close_menu()
        else:
            report("tablet: no chip while the file reads cleanly", await pg.evaluate(CHIP) is None)
            await open_picker(); await choose("UTF-8")
            c = await pg.evaluate(CHIP)
            # the whole note where it fits beside the page box (1100 px and wider), else the encoding's name alone
            want = (lambda t: "don't fit UTF-8" in t) if W >= 1100 else (lambda t: t == "UTF-8")
            report("tablet: read as UTF-8, a chip shows (" + ("the note" if W >= 1100 else "the encoding's name — the note would reach the Document button") + ")",
                   bool(c) and want(c["text"]), c)
            if W >= 760:
                report("tablet: the chip is a 44 px box, on top, inside the screen, beside the page box",
                       bool(c) and c["box"][2] >= 44 and c["box"][3] >= 44 and c["top"] and c["inside"] and c["beside"], c)
            else:
                report("tablet: no room beside the page box, so the chip is a 44 px box under the top bar, on top, inside the screen",
                       bool(c) and c["box"][2] >= 44 and c["box"][3] >= 44 and c["top"] and c["inside"] and c["box"][1] >= 48, c)
            report("tablet: the chip covers neither the page box, the Document button nor any other top-bar control",
                   bool(c) and not c["overPager"] and not c["overDoc"] and not c["overOther"], c and c["overOther"])
            report("tablet: the chip says the encoding and the note aloud", bool(c) and "UTF-8" in (c["label"] or "") and "fit" in (c["label"] or ""), c and c["label"])
            if SHOT: await pg.screenshot(path=SHOT, clip={"x": 0, "y": 0, "width": W, "height": 140})
            if c:
                await pg.locator(".tb-encchip").tap(); await pg.wait_for_timeout(900)
                report("tablet: a tap on the chip opens “Read this file as”", await pg.locator(".fcard:has(.enc-list)").count() == 1)
                await choose("Windows-1252")
                report("tablet: back to Windows-1252, the chip goes", await pg.evaluate(CHIP) is None)

        # close this run's tab again
        for _ in range(3):
            if not await pg.evaluate("document.body.innerText.includes('encnote-')"): break
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Close").first.tap()
            else:
                await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
                await pg.locator(".pop-item", has_text="Close").first.tap()
            await pg.wait_for_timeout(1000)
            if await pg.locator(".closeq button", has_text="Discard").count():
                await pg.locator(".closeq button", has_text="Discard").tap(); await pg.wait_for_timeout(800)
        report("no script errors", not errors, errors[:2])
        await b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fails else 0)
asyncio.run(main())
