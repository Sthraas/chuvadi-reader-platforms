"""Worker memory given back after close / cancel (Web Test chat; test tooling only).
python3 memory_relief.py <dev base> <file> <engine> [--cancel]"""
import os, sys, time
from playwright.sync_api import sync_playwright
base, path, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]; cancel = "--cancel" in sys.argv
user = f"mem-{engine}-{int(time.time())}"
def worker_pids():
    out = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"Portal__Mode=Worker" in open(f"/proc/{pid}/environ", "rb").read(): out.append(int(pid))
        except OSError: pass
    return set(out)
def rss(pid):
    try:
        for l in open(f"/proc/{pid}/status"):
            if l.startswith("VmRSS:"): return int(l.split()[1]) // 1024
    except OSError: return None
with sync_playwright() as p:
    b = getattr(p, engine).launch(); before = worker_pids()
    c = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": user}); pg = c.new_page()
    pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
    mine = (worker_pids() - before).pop(); idle = rss(mine)
    with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
    t0 = time.time(); fc.value.set_files(path); peak = 0
    while time.time() - t0 < 120:
        peak = max(peak, rss(mine) or 0)
        if cancel:
            btn = pg.query_selector("button:has-text('Stop')")
            if btn and btn.is_visible(): btn.click(); break
        elif pg.query_selector("td.xv-cell, .rpage svg text, .wv-run"): break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(1500); opened = rss(mine); peak = max(peak, opened)
    if not cancel:
        n_before = pg.evaluate("document.querySelectorAll('header [class*=tab]').length")
        pg.locator("header button[aria-label^='Close'], header .tab-x, header [title^='Close']").first.click(timeout=5000)
        pg.wait_for_timeout(800)
        print("   tab closed:", "Upload" in pg.evaluate("document.body.innerText") and not pg.query_selector("td.xv-cell, .rpage svg text, .wv-run"), flush=True)
    samples = []
    for s in (2, 5, 10, 20, 30):
        while time.time() - t0 < 0: pass
        time.sleep(s - (samples[-1][0] if samples else 0)); samples.append((s, rss(mine)))
    print(f"[{engine}] {os.path.basename(path)} {'cancelled' if cancel else 'opened then closed'}: idle {idle} MB, peak {peak} MB, open {opened} MB, after: " + ", ".join(f"{s}s {m} MB" for s, m in samples), flush=True)
    b.close()
