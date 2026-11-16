"""Patch 28/29 Excel checks on the portal: sheet pager (arrows and number box change the sheet), column / row resize by
dragging (viewing only: kept on reload? reset; the downloaded file untouched), D-188 hidden-row/column Find line.
python3 excel_p29.py <dev base> <out> <engine>      (Web Test chat; test tooling only)"""
import sys, hashlib
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, OUT, eng = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]; F = "/tmp/p29/sheets.xlsx"
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + f"[{eng}] {n}" + (f" — {d}" if d != "" else ""), flush=True)
ST = """() => ({box: document.querySelector('.tb-pg-box')?.value, total: document.querySelector('.tb-pg-total')?.textContent,
 on: [...document.querySelectorAll('.xv-tab.on')].map(t => t.textContent.trim()), txt: [...document.querySelectorAll('.xv-cell')].slice(0, 40).map(c => c.textContent.trim()).filter(Boolean).slice(0, 3)})"""
HDR = "(c) => { const e = document.querySelector(`.xv-colhdr[data-c='${c}']`); const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
RH = "(c) => { const e = document.querySelector(`.xv-rowhdr[data-r='${c}']`); const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
with sync_playwright() as p:
    b = getattr(p, eng).launch(); c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); sign_in_as(c, B, "x29-" + eng); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(F); pg.wait_for_selector(".xv-canvas", timeout=60000); pg.wait_for_timeout(1500)
    s = pg.evaluate(ST); check("opens on the first sheet, pager 1 of 3", s["box"] == "1" and "3" in (s["total"] or "") and s["on"][0].startswith("Alpha"), s)
    pg.locator(".tb-pager button[aria-label^='Next']").click(); pg.wait_for_timeout(900); s = pg.evaluate(ST)
    check("Next arrow shows the second sheet", s["box"] == "2" and s["on"][0].startswith("Beta") and "beta-first" in s["txt"], s)
    pg.fill(".tb-pg-box", "3"); pg.keyboard.press("Enter"); pg.wait_for_timeout(900); s = pg.evaluate(ST)
    check("number box 3 shows the third sheet", s["on"][0].startswith("Gamma") and "gamma-first" in s["txt"], s)
    pg.locator(".tb-pager button[aria-label^='Previous']").click(); pg.wait_for_timeout(700); pg.locator(".xv-tab").first.click(); pg.wait_for_timeout(900); s = pg.evaluate(ST)
    check("clicking a sheet tab moves the pager back to 1", s["box"] == "1" and s["on"][0].startswith("Alpha"), s)
    # resize column D (4) by dragging its right edge
    h0 = pg.evaluate(HDR, 4); x, y = h0[0] + h0[2] - 1, h0[1] + h0[3] / 2
    pg.mouse.move(x, y); pg.wait_for_timeout(300); cur = pg.evaluate("document.querySelector('.xv-gridwrap').style.cursor")
    pg.mouse.down(); pg.mouse.move(x + 90, y, steps=6); pg.mouse.up(); pg.wait_for_timeout(700); h1 = pg.evaluate(HDR, 4)
    check("the edge of a column header shows the resize cursor", cur == "col-resize", cur)
    check("dragging a column edge by 90 px widens the column by about that", abs((h1[2] - h0[2]) - 90) <= 6, (round(h0[2]), round(h1[2])))
    r0 = pg.evaluate(RH, 3); x, y = r0[0] + r0[2] / 2, r0[1] + r0[3] - 1
    pg.mouse.move(x, y); pg.wait_for_timeout(300); pg.mouse.down(); pg.mouse.move(x, y + 40, steps=6); pg.mouse.up(); pg.wait_for_timeout(700); r1 = pg.evaluate(RH, 3)
    check("dragging a row edge by 40 px makes the row taller by about that", abs((r1[3] - r0[3]) - 40) <= 6, (round(r0[3]), round(r1[3])))
    pg.screenshot(path=f"{OUT}/xlsx-resized-{eng}.png")
    pg.locator(".tb-pager button[aria-label^='Next']").click(); pg.wait_for_timeout(700); pg.locator(".xv-tab").first.click(); pg.wait_for_timeout(900)
    h2 = pg.evaluate(HDR, 4); check("the size is kept when coming back to the sheet", abs(h2[2] - h1[2]) <= 2, (round(h1[2]), round(h2[2])))
    pg.reload(); pg.wait_for_selector(".xv-canvas", timeout=60000); pg.wait_for_timeout(1500); h3 = pg.evaluate(HDR, 4)
    print(f"INFO [{eng}] after a page reload column D is {round(h3[2])} px (was {round(h0[2])} before the drag, {round(h1[2])} after)")
    rs = pg.locator(".xv-resetsizes")
    if rs.count() and abs(h3[2] - h0[2]) > 2:
        rs.click(); pg.wait_for_timeout(800); h4 = pg.evaluate(HDR, 4); check("Reset sizes puts the column back", abs(h4[2] - h0[2]) <= 2, (round(h0[2]), round(h4[2])))
    else: print(f"INFO [{eng}] reset control present: {rs.count()}")
    # D-188
    pg.mouse.click(700, 500); pg.keyboard.press("Control+f"); pg.wait_for_timeout(600); pg.keyboard.type("needle"); pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
    hh = pg.locator(".xv-hiddenhits"); t = hh.inner_text() if hh.count() else None
    check("Find names the matches in hidden cells", t is not None and "A5 (hidden row)" in t and "C6 (hidden column)" in t and t.startswith("2 matches"), t)
    check("the visible match is outlined", pg.locator(".xv-cell.hit").count() >= 1, pg.locator(".xv-cell.hit").count())
    pg.screenshot(path=f"{OUT}/xlsx-hiddenhits-{eng}.png")
    check("no page errors", not errs, errs[:3]); b.close()
