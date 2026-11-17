#!/usr/bin/env python3
# TESTING ONLY. D-198 (patch 33) on touch sizes: before a page operation the Reader names what each file will lose.
# Reached by finger three ways: Arrange (a desk's ··· › Bind desk), Merge (Merge & Save) and Split (Split).
# For each: "The new file will not have everything", Continue / Cancel each a 44 px box, on top, inside the
# screen, 8 px or more apart; the same with the system bars' insets set and with the keyboard up; the text whole.
# Cancel stops the operation. A file with layers adds the layer line. Continue on Arrange goes on (and the same
# file is not asked about again).
#   pageop.py <url> <width> <height> <plain.pdf>   → PASS/FAIL per check, exit 1 on any FAIL
# Uses tools/PixelProof/fixtures/rich.pdf and layered.pdf too. Every file is copied into a temp folder first, so
# each run is asked about afresh (the Reader asks once per file per run); desks it fills are emptied again.
import asyncio, os, re, shutil, sys, tempfile, urllib.parse, urllib.request
from playwright.async_api import async_playwright
url, W, H, PLAIN = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
FIX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PixelProof", "fixtures"))
def post(path):
    return urllib.request.urlopen(urllib.request.Request(url + path, method="POST"), timeout=120).read()

MEASURE = """(inset) => { const c = document.querySelector('.pageopq'); if (!c) return null; const r = c.getBoundingClientRect();
    const btns = [...c.querySelectorAll('button')].map(e => { const q = e.getBoundingClientRect(); const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
        return { label: e.textContent.trim(), w: Math.round(q.width), h: Math.round(q.height), left: q.left, right: q.right, top: e === t || e.contains(t),
                 inside: q.left >= 0 && q.right <= innerWidth + 0.5 && q.top >= inset[0] && q.bottom <= innerHeight - inset[1] + 0.5 }; });
    const text = c.querySelector('.closeq-text');
    return { title: c.querySelector('.closeq-title').textContent.trim(), text: text.textContent.replace(/\\s+/g, ' ').trim(),
             box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], view: [innerWidth, innerHeight],
             inside: r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= inset[0] && r.bottom <= innerHeight - inset[1] + 0.5,
             cut: text.scrollWidth > text.clientWidth + 1 || c.scrollWidth > c.clientWidth + 1,
             gap: btns.length == 2 ? Math.round(Math.abs(btns[1].left - btns[0].right)) : null,
             btns: btns.map(({ left, right, ...b }) => b) }; }"""

async def main():
    fails = 0
    def report(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name, detail)
    tmp = tempfile.mkdtemp(prefix="chvd-pageop-")
    def copy(src, name):
        f = os.path.join(tmp, name); shutil.copyfile(src, f); return f
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(3000)
        phone = await pg.evaluate("document.documentElement.dataset.shell") == "phone"
        def good(m):
            return bool(m) and m["title"] == "The new file will not have everything" and [x["label"] for x in m["btns"]] == ["Continue", "Cancel"] \
                and all(x["w"] >= 44 and x["h"] >= 44 and x["top"] and x["inside"] for x in m["btns"]) and m["inside"] and not m["cut"] and (m["gap"] or 0) >= 8
        async def look(what):
            m = await pg.evaluate(MEASURE, [0, 0])
            report(f"{what}: the question, Continue / Cancel each 44 px, on top, inside the screen, 8 px or more apart", good(m), m)
            try:
                await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 24, "bottom": 48}}); await pg.wait_for_timeout(500)
                m2 = await pg.evaluate(MEASURE, [24, 48])
                report(f"{what}: with the system bars' insets (24 top, 48 bottom) nothing of it is under them", good(m2), m2 and {k: m2[k] for k in ("box", "inside", "btns")})
                await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {}}); await pg.wait_for_timeout(300)
            except Exception as e:
                report(f"{what}: with the system bars' insets nothing of it is under them", False, f"could not set insets: {e}")
            short = H - (320 if H > W else 200)
            await pg.set_viewport_size({"width": W, "height": short}); await pg.wait_for_timeout(600)
            m3 = await pg.evaluate(MEASURE, [0, 0])
            report(f"{what}: with the keyboard up (window {W}×{short}) both answers are still on screen and on top", good(m3), m3 and {k: m3[k] for k in ("box", "inside", "btns")})
            await pg.set_viewport_size({"width": W, "height": H}); await pg.wait_for_timeout(500)
            return m
        async def answer(label):
            await pg.locator(".pageopq button", has_text=label).tap(); await pg.wait_for_timeout(1500)
        async def mode(name):
            await pg.locator(".ph-nav-b" if phone else ".lb-mode", has_text=name).first.tap(); await pg.wait_for_timeout(1300)
        async def desk_menu(item):
            more = pg.locator('.desk:has([data-bench-id]) .desk-more').last
            await more.tap(); await pg.wait_for_timeout(500)
            it = pg.locator(".desk-menu button", has_text=item).first
            await it.scroll_into_view_if_needed(); await it.tap(); await pg.wait_for_timeout(1200)
        async def empty_desks():
            for _ in range(6):
                if not await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length"): break
                await desk_menu("Delete all pages")

        # ── Arrange: Bind desk ──
        plain = copy(PLAIN, "pageop-plain.pdf")
        post("/__preview/arrange?path=" + urllib.parse.quote(plain))
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(2500); await mode("Arrange")
        await desk_menu("Bind desk")
        if await pg.locator(".pageopq").count():
            m = await look("Arrange, Bind desk")
            report("Arrange: a plain file is told it holds none of what is left out, no layer line",
                   bool(m) and "pageop-plain.pdf has none of what is left out" in m["text"] and "layer" not in m["text"], m and m["text"][:150])
            await answer("Cancel")
            report("Arrange: Cancel stops the bind (no card left, the desk keeps its pages)",
                   await pg.locator(".pageopq").count() == 0 and await pg.evaluate("document.querySelectorAll('.desk [data-bench-id]').length") > 0)
            await desk_menu("Bind desk")
            if await pg.locator(".pageopq").count(): await answer("Continue")
            await pg.wait_for_timeout(2000)
            await desk_menu("Bind desk"); await pg.wait_for_timeout(800)
            report("Arrange: after Continue, the same file is not asked about again", await pg.locator(".pageopq").count() == 0)
            if await pg.locator(".pageopq").count(): await answer("Cancel")
        else:
            report("Arrange: the question comes before Bind desk", False, "no card")
        await empty_desks()
        await mode("Read")

        # ── Merge: two files, one with layers ──
        a = copy(os.path.join(FIX, "rich.pdf"), "pageop-rich.pdf"); l = copy(os.path.join(FIX, "layered.pdf"), "pageop-layered.pdf")
        for f in (a, l): post("/__preview/open?path=" + urllib.parse.quote(f))
        await pg.goto(url + "/merge"); await pg.wait_for_timeout(2500)
        add = pg.locator(".tbtn", has_text="Add open documents")
        if await add.count(): await add.tap(); await pg.wait_for_timeout(1200)
        # keep only the two files of this run
        for _ in range(12):
            names = await pg.evaluate("[...document.querySelectorAll('.mrow, .tool li, [class*=mrow]')].map(e => e.textContent)")
            rm = pg.locator(".mrow:not(:has-text('pageop-')) .mico-x, li:not(:has-text('pageop-')) .mico-x").first
            if not await rm.count(): break
            await rm.tap(); await pg.wait_for_timeout(300)
        go = pg.locator(".tbtn-go", has_text="Merge")
        if await go.count() and await go.is_enabled():
            await go.tap(); await pg.wait_for_timeout(1500)
            if await pg.locator(".pageopq").count():
                m = await look("Merge")
                report("Merge: each file is named, and the layer line is there",
                       bool(m) and "pageop-rich.pdf" in m["text"] and "pageop-layered.pdf" in m["text"] and "layer" in m["text"], m and m["text"][:200])
                await answer("Cancel")
                report("Merge: Cancel stops it (no result)", await pg.locator(".pageopq").count() == 0 and await pg.locator(".tbtn", has_text="Open result").count() == 0)
            else:
                report("Merge: the question comes before Merge & Save", False, "no card")
        else:
            report("Merge: Merge & Save could be reached", False, "not enabled with the two files added")

        # ── Split: the current file ──
        s = copy(PLAIN, "pageop-split.pdf"); post("/__preview/open?path=" + urllib.parse.quote(s))
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(2500)
        await pg.goto(url + "/split"); await pg.wait_for_timeout(2500)
        use = pg.locator(".tbtn", has_text="Use current")
        if await use.count(): await use.tap(); await pg.wait_for_timeout(1200)
        go = pg.locator(".tbtn-go").first
        if await go.count():
            await go.scroll_into_view_if_needed(); await go.tap(); await pg.wait_for_timeout(1500)
            if await pg.locator(".pageopq").count():
                await look("Split")
                await answer("Cancel")
                report("Split: Cancel stops it (no result)", await pg.locator(".pageopq").count() == 0 and await pg.locator(".tbtn", has_text="Open result").count() == 0)
            else:
                report("Split: the question comes before Split", False, "no card")
        else:
            report("Split: the Split button could be reached", False, "none")

        # close this run's tabs again
        await pg.goto(url + "/reader"); await pg.wait_for_timeout(2000)
        for _ in range(5):
            if not await pg.evaluate("document.body.innerText.includes('pageop-')"): break
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
