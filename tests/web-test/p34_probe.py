"""Patch 34 on the portal, independent of the Web chat's scripts:
 - AT-30: on a phone, a greyed tool answers a tap with its reason (Protect: Box, Find while redaction is held);
 - B-36: on the desktop, Save redacted copy is greyed while redaction is held and does nothing but say why;
 - Web UI: on a phone the encoding rows are finger-sized (>= 44 CSS px);
 - AT-24: on a short phone screen, Find lands on the match's own page (page 3 of find-page3-foot.pdf), 5 times;
 - D-203: Arrange's desks on the portal — what the Sign out card promises against what a later sign-in finds (WT-30).
python3 p34_probe.py <dev base> <out> <engine>      (Web Test chat; test tooling only; needs /tmp/p34, /tmp/enc)"""
import sys, time, os, re
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, OUT, eng = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + f"[{eng}] {n}" + (f" — {d}" if d != "" else ""), flush=True)
def phone(b, h=915):
    kw = dict(viewport={"width": 412, "height": h}, has_touch=True, device_scale_factor=2)
    if eng != "firefox": kw["is_mobile"] = True
    c = b.new_context(**kw); sign_in_as(c, B, f"p34-{eng}-{int(time.time() * 10) % 1000000}"); pg = c.new_page()
    pg.goto(B + "/"); pg.locator("text=Upload >> visible=true").first.wait_for(timeout=60000); return c, pg
def ph_up(pg, f, sel):
    with pg.expect_file_chooser() as fc: pg.locator("text=Upload >> visible=true").first.tap()
    fc.value.set_files(f); pg.wait_for_selector(sel, timeout=60000); pg.wait_for_timeout(2000)
with sync_playwright() as p:
    b = getattr(p, eng).launch()
    # AT-30
    c, pg = phone(b); ph_up(pg, "/tmp/corpus/text-13.pdf", ".rpage")
    pg.locator("button:visible", has_text="Protect").first.tap(); pg.wait_for_timeout(1200)
    tools = {t.inner_text().strip(): (t.get_attribute("aria-disabled"), "dim" in (t.get_attribute("class") or "")) for t in pg.locator(".ph-tool").all()}
    t0 = pg.inner_text("body").split("\n"); pg.locator(".ph-tool", has_text="Box").first.tap(force=True); pg.wait_for_timeout(1200)
    new = [l for l in pg.inner_text("body").split("\n") if l not in t0]
    check("phone, Protect: the held Box tool is greyed and a tap says why", tools.get("Box") == ("true", True) and any("Redaction comes back with the next update" in l for l in new) and "/redact" not in pg.url, (tools.get("Box"), new[:2]))
    c.close()
    # encoding rows
    c, pg = phone(b); ph_up(pg, "/tmp/enc/cp1252.txt", ".txv, pre, .rtext")
    pg.locator("header button[aria-label='More'], button[aria-label='More']").last.tap(); pg.wait_for_timeout(900)
    pg.locator("button:visible", has_text="Text encoding").first.tap(); pg.wait_for_selector(".enc-row", timeout=10000); pg.wait_for_timeout(600)
    hs = pg.evaluate("[...document.querySelectorAll('.enc-row')].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().height))")
    check("phone: every encoding row is at least 44 px high", hs and min(hs) >= 44, hs)
    pg.screenshot(path=f"{OUT}/p34-phone-encoding-{eng}.png"); c.close()
    # AT-24
    c, pg = phone(b, 520); ph_up(pg, "/tmp/p34/find-page3-foot.pdf", ".rpage")
    good = 0; seen = []
    for t in range(5):
        pg.locator("header button[aria-label='More'], button[aria-label='More']").last.tap(); pg.wait_for_timeout(700)
        pg.locator("button:visible").filter(has_text=re.compile(r"^\s*Find\s*$")).first.tap(); pg.wait_for_timeout(700)
        box = pg.locator("input[type=search]:visible, input[placeholder*='Find']:visible").first; box.fill("zephyrine"); box.press("Enter"); pg.wait_for_timeout(2500)
        s = pg.evaluate("""() => { const cur = document.querySelector('.rfind-hl.cur') || document.querySelector('.rfind-hl');
            if (!cur) return null; const r = cur.getBoundingClientRect(); const wrap = cur.closest('[data-page], .rpage-wrap, .rpage');
            const pr = wrap.getBoundingClientRect(); const ind = [...document.querySelectorAll('button')].map(b => b.innerText).find(t => /^\\s*\\d+ \\/ 12/.test(t));
            return { page: wrap.getAttribute('data-page') || wrap.dataset.index || null, ind: ind && ind.trim(), vis: r.top >= 0 && r.bottom <= innerHeight, inside: r.top >= pr.top && r.bottom <= pr.bottom }; }""")
        seen.append(s)
        if s and s["vis"] and s["inside"] and s["ind"] and s["ind"].startswith("3 /"): good += 1
        pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
        pg.evaluate("() => { for (const e of document.querySelectorAll('.rdesk, .rcanvas, main')) e.scrollTop = 0; scrollTo(0, 0); }"); pg.wait_for_timeout(800)
    check("phone 412×520: Find lands on page 3 with the match on screen inside its page, 5 of 5", good == 5, seen[:2])
    pg.screenshot(path=f"{OUT}/p34-phone-find-{eng}.png"); c.close()
    # B-36 desktop
    c = b.new_context(viewport={"width": 1440, "height": 900}); sign_in_as(c, B, f"p34d-{eng}-{int(time.time()) % 100000}"); pg = c.new_page()
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage", timeout=60000); pg.mouse.move(700, 450)
    pg.locator("text=Protect").first.click(); pg.wait_for_timeout(900); pg.mouse.move(700, 450)
    sv = pg.locator("button.rb", has_text="Save redacted copy")
    if sv.count() == 0: sv = pg.locator("button[aria-label='Save redacted copy']")
    info = (sv.count(), sv.first.get_attribute("title") if sv.count() else None, sv.first.get_attribute("class") if sv.count() else None)
    dls = []; pg.on("download", lambda d: dls.append(d)); t0 = pg.inner_text("body").split("\n")
    if sv.count(): sv.first.click(force=True); pg.wait_for_timeout(1500)
    new = [l for l in pg.inner_text("body").split("\n") if l not in t0]
    check("desktop, Protect: Save redacted copy is greyed with its reason and does nothing else", sv.count() == 1 and "comes back with the next update" in ((info[1] or "") + " ".join(new)) and not dls and "/redact" not in pg.url, (info, new[:2], len(dls), pg.url))
    # D-203 / WT-30
    who = f"p34a-{eng}-{int(time.time()) % 100000}"; c2 = b.new_context(viewport={"width": 1440, "height": 900}); sign_in_as(c2, B, who); pg = c2.new_page()
    pages = lambda pg: pg.evaluate("document.querySelectorAll('.desk img, .desk canvas, .desk [class*=page]').length")
    pg.goto(B + "/bench"); pg.wait_for_timeout(3000); pg.locator("button:has-text('Blank')").first.click(); pg.wait_for_timeout(1500)
    n1 = pages(pg); pg.click("button.acct-chip"); pg.click("button.acct-out"); pg.wait_for_selector(".closeq", timeout=10000)
    card = pg.locator(".closeq").inner_text().replace("\n", " | ")
    check("Sign out with arranged pages asks about Arrange", "Keep what you arranged?" in card and n1 > 0, card[:160])
    pg.locator(".closeq button:text-is('Cancel')").click(); pg.wait_for_timeout(1000)
    check("Cancel keeps the person signed in and the desk", "/signed-out" not in pg.url and pages(pg) == n1, (pg.url, pages(pg)))
    pg.click("button.acct-chip"); pg.click("button.acct-out"); pg.wait_for_selector(".closeq", timeout=10000)
    pg.locator(".closeq button:text-is('Save')").click()
    try: pg.wait_for_url("**/signed-out", timeout=20000); out = True
    except Exception: out = False
    c3 = b.new_context(viewport={"width": 1440, "height": 900}); sign_in_as(c3, B, who); p3 = c3.new_page(); p3.goto(B + "/bench"); p3.wait_for_timeout(4000)
    check("WT-30: Save on the Sign out card says it keeps the desks for next time — the same person signing in again finds them", out and pages(p3) == n1, (out, n1, pages(p3)))
    p3.screenshot(path=f"{OUT}/p34-arrange-after-signin-{eng}.png"); b.close()
