"""D-181: the browser's "Leave site?" question while marks are unsaved. Test tooling only.
python3 leave_prompt.py <dev base> <engine>"""
import sys
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, engine = sys.argv[1].rstrip('/'), sys.argv[2]; res = []
def check(name, ok, detail=""):
    ok = bool(ok); res.append(ok); print(("PASS " if ok else "FAIL ") + f"[{engine}] {name}" + (f" — {str(detail)[:200]}" if detail != "" else ""), flush=True)
with sync_playwright() as p:
    b = getattr(p, engine).launch(); c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); sign_in_as(c, B, "lv-" + engine)
    pg = c.new_page(); asked = []; answer = {"v": "dismiss"}
    def on_dialog(d):
        asked.append(d.type); (d.dismiss() if answer["v"] == "dismiss" else d.accept())
    pg.on("dialog", on_dialog)
    def reload_asks():
        asked.clear()
        try: pg.reload(timeout=8000)
        except Exception: pass
        pg.wait_for_timeout(1500); return list(asked)
    def marks(): return pg.evaluate("document.querySelectorAll('.mk-shape.rect:not(.draft)').length")
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-3.pdf"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(1000)
    pg.mouse.click(700, 400)
    check("no marks: reload asks nothing", reload_asks() == [], asked)
    pg.wait_for_selector("nav.leftbar"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(800)
    pg.locator("body").press("2"); pg.wait_for_selector(".mk-layer[data-page='0']"); pg.mouse.move(700, 300); pg.wait_for_timeout(500)
    pg.click("button[aria-label='Rectangle']"); pg.mouse.move(700, 300); pg.wait_for_timeout(400)
    pg.mouse.move(600, 300); pg.mouse.down(); pg.mouse.move(760, 420, steps=8); pg.mouse.up(); pg.wait_for_timeout(700)
    a = reload_asks()
    check("unsaved mark: reload asks 'Leave site?'", a == ["beforeunload"], a)
    check("staying (Cancel) keeps the mark", marks() == 1, marks())
    try:
        with pg.expect_download(timeout=20000) as d: pg.click("button[aria-label='Save as new PDF']")
        d.value.path(); pg.wait_for_timeout(1200); saved = True
    except Exception as e: saved = False
    a = reload_asks()
    check("after Save as new PDF the question still comes (stated limit, build log §36)", saved and a == ["beforeunload"], (saved, a))
    pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2500)
    pg.locator("body").press("2"); pg.wait_for_timeout(800); pg.mouse.move(700, 300)
    try:
        pg.click("button[aria-label='Rectangle']", timeout=8000); pg.mouse.move(700, 300); pg.wait_for_timeout(400)
        pg.mouse.move(500, 500); pg.mouse.down(); pg.mouse.move(640, 600, steps=8); pg.mouse.up(); pg.wait_for_timeout(700)
        answer["v"] = "accept"; a = reload_asks(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2500)
        tabs = pg.evaluate("[...document.querySelectorAll('header [data-tab-id]')].map(t=>t.textContent.trim().slice(0,24))")
        check("leaving (Leave) reloads; the tab comes back", a == ["beforeunload"] and len(tabs) >= 1, (a, tabs))
    except Exception as e: check("second mark + Leave", False, str(e).splitlines()[0])
    b.close()
print(f"{sum(res)}/{len(res)} pass")
