"""744be4f8 claim: after Save as… / Discard on the Sign out card, the sign-out is never cut off in the browser.
Repeats: a mark, Sign out, the card's choice; then records where the page ended up, whether the person's worker
folder (their files) is gone 10 s later, and whether the session cookie still opens the person's documents.
python3 signout_reach.py <dev base> <data root> <engine> <rounds> <save|discard>      (Web Test chat; test tooling only)"""
import sys, time, os
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, ROOT, eng, N, how = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
W = os.path.join(ROOT, "workers"); ws = lambda: set(os.listdir(W)) if os.path.isdir(W) else set()
bad = 0
with sync_playwright() as p:
    b = getattr(p, eng).launch()
    for r in range(1, N + 1):
        c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); sign_in_as(c, B, f"so-{eng}-{int(time.time() * 10) % 1000000}"); pg = c.new_page()
        before = ws(); pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload")
        with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
        fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg", timeout=60000); mine = ws() - before
        pg.click("nav.leftbar >> text=Mark"); pg.click("button.rb[aria-label='Rectangle']"); pg.mouse.move(5, 400)
        bx = pg.locator(".rpage").first.bounding_box(); x, y = bx["x"] + 200, bx["y"] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 100, y + 60, steps=5); pg.mouse.up(); pg.wait_for_selector(".mk-shape.rect", timeout=10000)
        pg.click("button.acct-chip"); pg.click("button.acct-out"); pg.wait_for_selector(".closeq", timeout=10000)
        nav_err = ""
        try:
            if how == "save":
                with pg.expect_download(timeout=60000): pg.locator(".closeq button:text-is('Save as…')").click()
            else: pg.locator(".closeq button:text-is('Discard')").click()
            pg.wait_for_url("**/signed-out", timeout=20000)
        except Exception as e: nav_err = str(e).split("\n")[0][:90]
        time.sleep(10)
        pdfs = sum(1 for w in mine if os.path.isdir(os.path.join(W, w)) for _, _, fs in os.walk(os.path.join(W, w)) for f in fs if f.lower().endswith('.pdf'))
        gone = pdfs == 0
        p2 = c.new_page(); p2.goto(B + "/"); p2.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); p2.wait_for_timeout(1500)
        tabs = p2.locator(".rtab-name").all_inner_texts()
        ok = gone and tabs == []; bad += not ok
        print(("PASS " if ok else "FAIL ") + f"[{eng}] round {r} ({how}): page at {pg.url.replace(B, '')} {('(' + nav_err + ')') if nav_err else ''}; the person's PDFs gone after 10 s {gone} ({pdfs} left); coming back shows {tabs}", flush=True)
        c.close()
    print(f"SUMMARY [{eng}] {N - bad} of {N} sign-outs reached the server", flush=True)
