"""Large Excel uploads through the portal: time to grid or refusal, message, worker memory, Cancel.
python3 large_xlsx_check.py <dev base> <folder> <engine> [--cancel <file>]   (Web Test chat; test tooling only)"""
import os, sys, time
from playwright.sync_api import sync_playwright
base, folder, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
cancel = sys.argv[sys.argv.index("--cancel") + 1] if "--cancel" in sys.argv else None
FILES = [] if "--only-cancel" in sys.argv else ["big-100k.xlsx", "rows-1048576.xlsx", "rows-1048577.xlsx", "entries-20001.xlsx", "ratio-600.xlsx", "zip-bomb.xlsx"]

def worker_rss():
    best = 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"Portal__Mode=Worker" not in open(f"/proc/{pid}/environ", "rb").read(): continue
            for l in open(f"/proc/{pid}/status"):
                if l.startswith("VmRSS:"): best = max(best, int(l.split()[1]) // 1024)
        except OSError: pass
    return best

def open_file(pg, path):
    pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
    with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
    t0 = time.time(); fc.value.set_files(path); return t0

with sync_playwright() as p:
    b = getattr(p, engine).launch()
    for f in FILES:
        path = os.path.join(folder, f)
        if not os.path.exists(path): continue
        c = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": f"big-{engine}-{f[:10]}"}); pg = c.new_page()
        t0 = open_file(pg, path); outcome = "timeout"; peak = 0
        while time.time() - t0 < 180:
            peak = max(peak, worker_rss())
            if pg.query_selector("td.xv-cell"): outcome = "grid"; break
            txt = pg.evaluate("document.body.innerText")
            msg = [l for l in txt.splitlines() if any(k in l.lower() for k in ("too large", "too many", "couldn't open", "can't open", "damaged", "limit"))]
            if msg: outcome = "refused: " + msg[0][:150]; break
            pg.wait_for_timeout(250)
        ms = round((time.time() - t0) * 1000)
        extra = ""
        if outcome == "grid":
            extra = " | last row shown: " + str(pg.evaluate("[...document.querySelectorAll('tr')].slice(-1)[0]?.innerText.split('\\t')[0]"))
        print(f"[{engine}] {f}: {outcome} in {ms} ms | peak worker {peak} MB{extra}", flush=True)
        pg.screenshot(path=f"/tmp/explore/bigx-{engine}-{f}.png"); c.close()
    if cancel:
        c = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": f"cancel-{engine}"}); pg = c.new_page()
        t0 = open_file(pg, os.path.join(folder, cancel)); stopped = None
        while time.time() - t0 < 60:
            btn = pg.query_selector("button:has-text('Stop'), button:has-text('Cancel')")
            if btn and btn.is_visible():
                shown = round((time.time() - t0) * 1000); t1 = time.time(); btn.click()
                while time.time() - t1 < 20:
                    if not pg.query_selector("text=Opening…"): break
                    pg.wait_for_timeout(100)
                stopped = (shown, round((time.time() - t1) * 1000)); break
            if pg.query_selector("td.xv-cell"): break
            pg.wait_for_timeout(100)
        after = pg.evaluate("document.body.innerText")
        print(f"[{engine}] Cancel on {cancel}: {'Stop shown at %d ms, opening ended %d ms after the click' % stopped if stopped else 'no Stop button seen (opened first?)'}"
              f" | grid shown afterwards: {bool(pg.query_selector('td.xv-cell'))} | page still answers: {pg.evaluate('1+1') == 2}", flush=True)
        pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=30000)
        print(f"[{engine}] after Cancel the person can carry on (Home loads)", flush=True)
        c.close()
    b.close()
