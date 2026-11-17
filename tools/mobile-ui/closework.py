#!/usr/bin/env python3
# TESTING ONLY. D-195 on touch sizes: the three other questions asked before unsaved work is lost.
#   * Bookmarks (closing a tab with a bookmark not saved):  Save bookmarks / Discard / Cancel
#   * Protect   while redaction is held (D-198): the greyed tool says why on a tap; no Save redacted copy
#               (the redaction-areas question returns with redaction)
#   * Arrange   (closing the app with pages on a desk):      Save session… / Discard / Cancel
# For each: the answers are the ones named, each a 44 px box, the top element at its centre, inside the screen;
# the same with the system bars' insets set (24 px top, 48 px bottom) and with the keyboard up (a shorter
# window); Cancel keeps the work; Discard lets the close go on.
#   closework.py <url> <width> <height> <some.pdf> [shots-dir]   → PASS/FAIL per check, exit 1 on any FAIL
# It opens copies of <some.pdf> from a temp folder and closes them again, and deletes the desk it filled.
import asyncio, json, os, re, shutil, sys, tempfile, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H, PDF = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
SHOTS = sys.argv[5] if len(sys.argv) > 5 else None
def post(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url + path, method="POST"), timeout=120).read() or b"{}")

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    tmp = tempfile.mkdtemp(prefix="chvd-closework-")
    def copy(name):
        f = os.path.join(tmp, name); shutil.copyfile(PDF, f); return f
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3000)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        async def open_doc(f):
            post("/__preview/open?path=" + urllib.parse.quote(f))
            await pg.goto(url + "/reader"); await pg.wait_for_timeout(3500)
        async def touch(kind, pts):
            await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": 0} for x, y in pts]})
        async def mode(name):
            m = pg.locator(".ph-nav-b" if phone else ".lb-mode", has_text=name).first
            await m.tap(); await pg.wait_for_timeout(1200)
        async def ask_close_tab():
            if phone:
                await pg.locator('.ph-bar button[aria-label="More"]').tap(); await pg.wait_for_timeout(500)
                await pg.locator(".ph-row", has_text="Close").first.tap()
            else:
                await pg.locator(".tb-doc").tap(); await pg.wait_for_timeout(400)
                await pg.locator(".pop-item", has_text="Close").first.tap()
            await pg.wait_for_timeout(1000)
        MEASURE = """(inset) => { const c = document.querySelector('.closeq'); if (!c) return null; const r = c.getBoundingClientRect();
            const btns = [...c.querySelectorAll('button')].map(e => { const q = e.getBoundingClientRect(); const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
                return { label: e.textContent.trim(), w: Math.round(q.width), h: Math.round(q.height), top: e === t || e.contains(t),
                         inside: q.left >= 0 && q.right <= innerWidth + 0.5 && q.top >= inset[0] && q.bottom <= innerHeight - inset[1] + 0.5 }; });
            const title = c.querySelector('.closeq-title'), text = c.querySelector('.closeq-text');
            const gaps = btns.length > 1 ? [...c.querySelectorAll('button')].map(e => e.getBoundingClientRect()).sort((a, b) => a.top - b.top || a.left - b.left)
                .reduce((g, q, i, all) => { if (i && Math.abs(q.top - all[i - 1].top) < 4) g.push(Math.round(q.left - all[i - 1].right)); return g; }, []) : [];
            return { title: title.textContent.trim().slice(0, 60), box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], view: [innerWidth, innerHeight],
                     inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= inset[0] && r.bottom <= innerHeight - inset[1] + 0.5,
                     cut: title.scrollWidth > title.clientWidth + 1 || (text && text.scrollWidth > text.clientWidth + 1), gaps, btns }; }"""
        def good(m, labels):
            return bool(m) and [x["label"] for x in m["btns"]] == labels and all(x["w"] >= 44 and x["h"] >= 44 and x["top"] and x["inside"] for x in m["btns"]) \
                   and m["inside"] and not m["cut"] and all(g >= 8 for g in m["gaps"])
        async def look(what, labels):
            m = await pg.evaluate(MEASURE, [0, 0])
            if SHOTS: os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, f"{what.lower()}-{W}x{H}.png"))
            report(f"{what}: the question is there with {' / '.join(labels)}, each 44 px, on top, inside the screen, 8 px or more apart", good(m, labels), m)
            try:
                await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 24, "bottom": 48}}); await pg.wait_for_timeout(500)
                m2 = await pg.evaluate(MEASURE, [24, 48])
                report(f"{what}: with the system bars' insets (24 top, 48 bottom) nothing of it is under them", good(m2, labels), m2)
                await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {}}); await pg.wait_for_timeout(300)
            except Exception as e:
                report(f"{what}: with the system bars' insets nothing of it is under them", False, f"could not set insets: {e}")
            short = H - (320 if H > W else 200)
            await pg.set_viewport_size({"width": W, "height": short}); await pg.wait_for_timeout(600)
            m3 = await pg.evaluate(MEASURE, [0, 0])
            report(f"{what}: with the keyboard up (window {W}×{short}) every answer is still on screen and on top", good(m3, labels), m3)
            await pg.set_viewport_size({"width": W, "height": H}); await pg.wait_for_timeout(500)
        async def answer(label):
            await pg.locator(".closeq button", has_text=re.compile("^" + re.escape(label))).tap(); await pg.wait_for_timeout(1300)
        has_name = lambda n: pg.evaluate("(n) => document.body.innerText.includes(n)", n)

        # ── Bookmarks ──
        await open_doc(copy("closework-bookmarks.pdf"))
        d = await pg.locator(".rdesk").first.bounding_box()
        await pg.touchscreen.tap(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2); await pg.wait_for_timeout(400)
        await pg.keyboard.press("Control+b"); await pg.wait_for_timeout(800); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(600)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await ask_close_tab()
        if await pg.locator(".closeq").count():
            await look("Bookmarks", ["Save bookmarks", "Discard", "Cancel"])
            await answer("Cancel")
            report("Bookmarks: Cancel keeps the tab", await pg.locator(".closeq").count() == 0 and await has_name("closework-bookmarks"))
            await ask_close_tab(); await answer("Discard")
            report("Bookmarks: Discard closes the tab", await pg.locator(".closeq").count() == 0 and not await has_name("closework-bookmarks"))
        else:
            report("Bookmarks: the question is there", False, "no card after Ctrl+B, Enter and Close (could not make a bookmark here)")

        # ── Protect ──
        # D-198 (patch 33): while redaction is held there are no redaction areas to ask about. The greyed tool must
        # say why on a tap instead (phone: Box on the strip; tablet: Redaction on the rail), and Save redacted copy
        # must not be offered.
        await open_doc(copy("closework-protect.pdf"))
        await mode("Protect")
        held = pg.locator(".ph-strip .ph-tool", has_text="Box").first if phone else pg.locator('.srail .rb[aria-label="Redaction"]').first
        if await held.count() and (phone and await held.get_attribute("aria-disabled") == "true" or not phone):
            bb = await held.bounding_box()
            await pg.touchscreen.tap(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); await pg.wait_for_timeout(900)
            note = await pg.evaluate("""(() => { const e = [...document.querySelectorAll('body *')].find(x => x.children.length === 0 && x.textContent.includes('Redaction comes back with the next update'));
                if (!e) return null; const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.left + Math.min(20, r.width / 2), r.top + r.height / 2);
                return { box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], top: !!t && (e === t || e.contains(t) || t.contains(e)),
                         inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= 0 && r.bottom <= innerHeight + 0.5 }; })()""")
            report("Protect (redaction held, D-198): a tap on the greyed redaction tool says when it comes back, on screen and on top",
                   bool(note) and note["top"] and note["inside"] and "/redact" not in pg.url, note)
            offered = await pg.evaluate("[...document.querySelectorAll('.ph-fab, .srail .rb')].some(e => /Save redacted copy/.test(e.getAttribute('aria-label') || '') && e.getBoundingClientRect().width)")
            report("Protect (redaction held): Save redacted copy is not offered", not offered, "offered" if offered else "")
        else:
            report("Protect: the redaction tool shows its hold (D-198)", False, "redaction is not held here, or its tool was not found")
        await mode("Read")
        await ask_close_tab()
        if await pg.locator(".closeq").count(): await answer("Discard")

        # ── Arrange (asked when the app is closed) ──
        desks0 = post("/__preview/arrange?path=" + urllib.parse.quote(copy("closework-arrange.pdf")))
        closing = asyncio.create_task(asyncio.to_thread(post, "/__preview/close-app"))
        try:
            await pg.wait_for_selector(".closeq", timeout=15000); await pg.wait_for_timeout(700)
            await look("Arrange", ["Save session…", "Discard", "Cancel"])
            await answer("Cancel"); r1 = await asyncio.wait_for(closing, 20)
            report("Arrange: Cancel stops the close", r1.get("closed") is False and await pg.locator(".closeq").count() == 0, r1)
            closing = asyncio.create_task(asyncio.to_thread(post, "/__preview/close-app"))
            await pg.wait_for_selector(".closeq", timeout=15000); await pg.wait_for_timeout(500)
            await answer("Discard"); r2 = await asyncio.wait_for(closing, 20)
            report("Arrange: Discard lets the close go on", r2.get("closed") is True, r2)
        except Exception as e:
            report("Arrange: the question is there", False, f"{type(e).__name__}: {str(e)[:120]}")
        # take the desk away again, so later runs start as before
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(2500)
        if await pg.locator(".ph-nav-b, .lb-mode").count():
            await mode("Arrange")
            for _ in range(4):
                if not await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length"): break
                more = pg.locator('.desk:has([data-bench-id]) .desk-more').first
                if not await more.count(): break
                await more.tap(); await pg.wait_for_timeout(500)
                item = pg.locator(".desk-menu button", has_text="Delete all pages").first
                if not await item.count(): break
                await item.scroll_into_view_if_needed(); await item.tap(); await pg.wait_for_timeout(800)
            left = await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length")
            print(f"NOTE desk pages left in Arrange after clean-up: {left}")
            await mode("Read")
        report("no script errors", not errors, errors[:2])
        await b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fails else 0)
asyncio.run(main())
