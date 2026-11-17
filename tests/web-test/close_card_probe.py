"""WT-23 / D-186 / D-190, independent of the Web chat's close_card.py: marks kept with the tab, Leave-site for a tab
that isn't showing, the ask-before-closing card (Save puts the mark in the file; Esc; phone width), session end.
python3 close_card_probe.py <dev base> <short-idle dev base> <out> <engine>      (Web Test chat; test tooling only)"""
import sys, time, os, io
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, S, OUT, eng = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4]
A, Bf = "/tmp/corpus/text-13.pdf", "/tmp/m27/plain.pdf"
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + f"[{eng}] {n}" + (f" — {d}" if d != "" else ""), flush=True)
def up(pg, f):
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(f); pg.wait_for_selector(f".rtab:has(.rtab-name:text-is('{os.path.basename(f)}'))", timeout=60000); pg.wait_for_selector(".rpage", timeout=60000); pg.wait_for_timeout(800)
def tab(pg, name): pg.click(f".rtab:has(.rtab-name:text-is('{name}'))"); pg.wait_for_timeout(1200)
def draw(pg):
    pg.click("nav.leftbar >> text=Mark"); pg.click("button.rb[aria-label='Rectangle']"); pg.mouse.move(5, 400)
    bx = pg.locator(".rpage").first.bounding_box(); x, y = bx["x"] + bx["width"] * .3, bx["y"] + min(bx["height"], 600) * .3
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 120, y + 80, steps=6); pg.mouse.up(); pg.wait_for_selector(".mk-shape.rect", timeout=10000)
def marks(pg): return pg.locator(".mk-shape.rect").count()
def start(p, base, vw=(1400, 900)):
    b = getattr(p, eng).launch(); c = b.new_context(viewport={"width": vw[0], "height": vw[1]}, accept_downloads=True); sign_in_as(c, base, "ccp-" + eng); pg = c.new_page()
    pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); return b, c, pg
with sync_playwright() as p:
    # 1. marks stay with the tab; reload from the other tab asks
    b, c, pg = start(p, B); up(pg, A); draw(pg); up(pg, Bf)
    check("the other tab shows no mark of the first", marks(pg) == 0, marks(pg))
    tab(pg, "text-13.pdf"); check("back on the first tab its mark is still there", marks(pg) == 1, marks(pg))
    tab(pg, "plain.pdf"); seen = []
    pg.on("dialog", lambda d: (seen.append(d.type), d.dismiss()))
    try: pg.reload(timeout=6000)
    except Exception: pass
    pg.wait_for_timeout(800)
    check("reload while another tab holds unsaved marks raises the Leave-site question", seen == ["beforeunload"], seen)
    tab(pg, "text-13.pdf"); check("staying keeps the mark", marks(pg) == 1, marks(pg))
    # 2. close card: Esc, then Save -> file has the mark
    pg.locator(".rtab:has(.rtab-name:text-is('text-13.pdf')) .rtab-x").click(); pg.wait_for_selector(".closeq", timeout=10000)
    txt = pg.locator(".closeq").inner_text(); check("the card names the file", "text-13.pdf" in txt, txt.replace("\n", " | ")[:160])
    pg.screenshot(path=f"{OUT}/closecard-{eng}.png")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(700)
    check("Esc closes the card and keeps the tab and mark", pg.locator(".closeq").count() == 0 and marks(pg) == 1, (pg.locator(".closeq").count(), marks(pg)))
    pg.locator(".rtab:has(.rtab-name:text-is('text-13.pdf')) .rtab-x").click(); pg.wait_for_selector(".closeq", timeout=10000)
    try:
        with pg.expect_download(timeout=20000) as dl: pg.locator(".closeq button:text-is('Save as…')").click()
        path = f"{OUT}/saved-{eng}.pdf"; dl.value.save_as(path)
        from pypdf import PdfReader
        def data(page):
            o = page["/Contents"].get_object()
            return b"".join(x.get_object().get_data() for x in o) if isinstance(o, list) else o.get_data()
        r = PdfReader(path); cont = data(r.pages[0]); orig = data(PdfReader(A).pages[0])
        check("Save as… on the card delivers the file with the mark in it", len(r.pages) == 13 and len(cont) > len(orig) and b" Do" in cont[len(orig) - 20:], (len(r.pages), len(orig), len(cont)))
    except Exception as ex: check("Save as… on the card delivers the file with the mark in it", False, str(ex)[:150])
    pg.wait_for_timeout(1000); check("after Save as… the tab is closed, the other stays", pg.locator(".rtab-name").all_inner_texts() == ["plain.pdf"], pg.locator(".rtab-name").all_inner_texts())
    seen.clear()
    try: pg.reload(timeout=8000)
    except Exception: pass
    pg.wait_for_timeout(1000); check("nothing unsaved now: reload asks nothing", seen == [], seen); b.close()
    # 3. phone width: the card fits
    b, c, pg = start(p, B, (390, 844))
    try:
        with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
        fc.value.set_files(A); pg.wait_for_selector(".rpage", timeout=60000)
        pg.screenshot(path=f"{OUT}/phone-open-{eng}.png")
    except Exception as ex: print("phone open:", str(ex)[:120])
    b.close()
    # 4. session end with unsaved marks: closes without asking
    b, c, pg = start(p, S); up(pg, A); draw(pg); t = time.time(); ended = None
    while time.time() - t < 75:
        if pg.locator(".rpage").count() == 0 and pg.locator(".closeq").count() == 0: ended = round(time.time() - t); break
        if pg.locator(".closeq").count(): break
        pg.wait_for_timeout(1000)
    body = pg.inner_text("body")[:200].replace("\n", " | ")
    check("session end with unsaved marks closes the document without a question", ended is not None, (ended, pg.url, body)); pg.screenshot(path=f"{OUT}/expired-with-marks-{eng}.png"); b.close()
