"""WT-22: a reload gives the tabs back; documents close with their owner. Test tooling only.
python3 reload_tabs.py <dev base> <short-idle dev base> <engine>"""
import os, sys, time
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, BS, engine = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3]
res = []
def check(name, ok, detail=""):
    ok = bool(ok); res.append(ok); print(("PASS " if ok else "FAIL ") + f"[{engine}] {name}" + (f" — {str(detail)[:220]}" if detail != "" else ""), flush=True)
def wp():
    r = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"Portal__Mode=Worker" in open(f"/proc/{pid}/environ", "rb").read():
                r[int(pid)] = [int(l.split()[1]) // 1024 for l in open(f"/proc/{pid}/status") if l.startswith("VmRSS:")][0]
        except (OSError, IndexError): pass
    return r
TABS = "() => [...document.querySelectorAll('header [data-tab-id]')].map(t => t.textContent.trim().replace(/\\s+/g, ' ').slice(0, 30))"
IMGS = "() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href') || '').filter(h => h.startsWith('_chvd/pages/'))"
def upload(pg, base, f):
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(f); name = os.path.basename(f)
    pg.wait_for_function("(n) => [...document.querySelectorAll('header [data-tab-id]')].some(t => t.textContent.includes(n))", arg=name, timeout=90000)
    pg.wait_for_selector(".rpage svg, td.xv-cell", timeout=90000); pg.wait_for_timeout(1500)

with sync_playwright() as p:
    b = getattr(p, engine).launch()
    # ---- 1. reload keeps the tabs, the page position and unsaved marks ----
    c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); sign_in_as(c, B, "rl-" + engine); pg = c.new_page()
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar"); upload(pg, B, "/tmp/corpus/text-13.pdf"); upload(pg, B, "/tmp/pis/large-6.pdf")
    t0 = pg.evaluate(TABS); img0 = pg.evaluate(IMGS)
    pg.reload(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(3000)
    t1 = pg.evaluate(TABS)
    check("reload: both tabs are back", len(t1) == 2 and t1 == t0, (t0, t1))
    check("reload: the active document is drawn again", bool(pg.query_selector(".rpage svg")), pg.url[-20:])
    st_old = [c.request.get(B + "/" + h).status for h in img0[:2]]; img1 = pg.evaluate(IMGS)
    check("reload: new image addresses; the old ones are freed", img1 and not set(img1) & set(img0) and all(s == 404 for s in st_old), (st_old, len(img1)))
    # marks
    pg.locator("body").press("2"); pg.wait_for_selector(".mk-layer[data-page='0']"); pg.mouse.move(700, 300); pg.wait_for_timeout(500)
    pg.click("button[aria-label='Rectangle']"); pg.mouse.move(700, 300); pg.wait_for_timeout(400)
    pg.mouse.move(600, 300); pg.mouse.down(); pg.mouse.move(760, 420, steps=8); pg.mouse.up(); pg.wait_for_timeout(700)
    n0 = pg.evaluate("document.querySelectorAll('.mk-shape.rect:not(.draft)').length")
    pg.reload(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(3000)
    pg.locator("body").press("2"); pg.wait_for_timeout(1200)
    n1 = pg.evaluate("document.querySelectorAll('.mk-shape.rect:not(.draft)').length")
    check("reload: an unsaved mark is NOT kept (documented in the Web build log §34) — recorded, see WT-23", n0 == 1 and n1 == 0, (n0, n1, [l for l in pg.evaluate("document.body.innerText").splitlines() if "unsaved" in l or "shape" in l][:2]))
    # second browser tab of the same person sees the same tabs
    p2 = c.new_page(); p2.goto(B + "/"); p2.wait_for_selector("nav.leftbar"); p2.wait_for_timeout(2500)
    check("a second browser tab of the same person shows the same tabs", len(p2.evaluate(TABS)) == 2, p2.evaluate(TABS))
    # another person sees none
    c2 = b.new_context(); sign_in_as(c2, B, "rl2-" + engine); q = c2.new_page(); q.goto(B + "/"); q.wait_for_selector("nav.leftbar"); q.wait_for_timeout(2000)
    check("another person sees no tabs", q.evaluate(TABS) == [], q.evaluate(TABS)); c2.close()
    # closing a tab closes its document for good
    while pg.query_selector("header button[aria-label^='Close']"):
        pg.locator("header button[aria-label^='Close']").first.click(); pg.wait_for_timeout(500)
        for lbl in ("Discard", "Close without saving", "Don't save"):
            bt = pg.query_selector(f"button:has-text(\"{lbl}\")")
            if bt: bt.click(); pg.wait_for_timeout(400)
    pg.reload(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2500)
    check("closed tabs stay closed after a reload", pg.evaluate(TABS) == [], pg.evaluate(TABS)); c.close()
    # ---- 2. documents close with their owner (short idle): reload in the middle, then expiry ----
    before = set(wp())
    c = b.new_context(viewport={"width": 1440, "height": 900}); sign_in_as(c, BS, "rle-" + engine); pg = c.new_page()
    pg.goto(BS + "/"); pg.wait_for_selector("nav.leftbar"); mine = (set(wp()) - before).pop(); idle = wp()[mine]
    upload(pg, BS, "/tmp/pis/large-6.pdf"); pg.reload(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2500)
    upload(pg, BS, "/tmp/corpus/scan-40.pdf"); pg.reload(); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2500)
    tabs = pg.evaluate(TABS); pg.locator("header [data-tab-id]", has_text="large-6").first.click(); pg.wait_for_function("() => document.querySelectorAll('.rpage svg image').length > 0", timeout=30000); pg.wait_for_timeout(800)
    held = wp()[mine]; imgs = pg.evaluate(IMGS)
    live = [c.request.get(BS + "/" + h).status for h in imgs[:2]]
    pg.wait_for_url("**/signed-out*", timeout=120000); pg.wait_for_timeout(2500)
    after = [c.request.get(BS + "/" + h).status for h in imgs[:2]]; w = wp(); now = w.get(mine)
    check("after two reloads: both tabs shown", len(tabs) == 2, tabs)
    check("after two reloads and expiry: images gone", tabs and live and all(s == 200 for s in live) and all(s == 404 for s in after), (tabs, live, after))
    check("after two reloads and expiry: memory given back", now is None or now < held - 100, f"idle {idle} MB, with documents {held} MB, after {now if now is not None else 'worker stopped'} MB")
    pg.goto(BS + "/"); pg.wait_for_selector("nav.leftbar"); pg.wait_for_timeout(2000)
    check("signing in again after expiry starts with no tabs", pg.evaluate(TABS) == [], pg.evaluate(TABS))
    b.close()
print(f"{sum(res)}/{len(res)} pass")
