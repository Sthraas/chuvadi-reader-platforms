"""WT-21: what a session held is freed when it ends (expiry or sign-out). Test tooling only.
python3 session_end_free.py <dev base with short idle> <engine> expiry|signout <file> [<file>...]"""
import os, sys, time, urllib.request
from playwright.sync_api import sync_playwright
B, engine, how, files = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], [x for x in sys.argv[4:] if not x.startswith('--')]
def wp():
    s = set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"Portal__Mode=Worker" in open(f"/proc/{pid}/environ", "rb").read(): s.add(int(pid))
        except OSError: pass
    return s
def rss(pid):
    try: return [int(l.split()[1]) // 1024 for l in open(f"/proc/{pid}/status") if l.startswith("VmRSS:")][0]
    except OSError: return None
def st(path, u):
    try:
        with urllib.request.urlopen(urllib.request.Request(B + "/" + path, headers={"X-Dev-User": u}), timeout=20) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
with sync_playwright() as p:
    b = getattr(p, engine).launch(); u = f"sef-{how}-{int(time.time())}"; before = wp()
    c = b.new_context(extra_http_headers={"X-Dev-User": u}, viewport={"width": 1400, "height": 900}); a = c.new_page()
    a.goto(B + "/"); a.wait_for_selector("text=Upload"); mine = (wp() - before).pop(); idle = rss(mine); toks = []
    for f in files:
        if "--no-reload" not in sys.argv: a.goto(B + "/"); a.wait_for_selector("text=Upload")
        with a.expect_file_chooser() as fc: a.locator("text=Upload").first.click()
        fc.value.set_files(f); a.wait_for_selector("td.xv-cell, .rpage svg", timeout=90000); a.wait_for_timeout(1500)
        toks += [h for h in a.evaluate("[...document.querySelectorAll('.rpage svg image')].map(i=>i.getAttribute('href')||'')") if h.startswith('_chvd/pages/')]
    held = rss(mine); live = [st(t, u) for t in toks[:3]]
    if how == "signout":
        a.goto(B + "/"); a.wait_for_selector("text=Upload"); a.click(".acct-chip"); a.click("text=Sign out")
    a.wait_for_url("**/signed-out*", timeout=120000); t0 = time.time(); a.wait_for_timeout(1500)
    after = [st(t, u) for t in toks[:3]]   # note: in Development this request signs the person in again (new empty session)
    samples = []; freed_at = None if 200 in after else 1
    for s in (3, 10, 35) + ((60, 120, 200, 260) if "--long" in sys.argv else ()):
        while time.time() - t0 < s: time.sleep(0.5)
        if freed_at is None and "--long" in sys.argv and 200 not in [st(t, u) for t in toks[:3]]: freed_at = s
        samples.append((s, rss(mine) if mine in wp() else "worker stopped"))
    if "--long" in sys.argv: print("   images freed by:", freed_at, "s")
    print(f"[{engine}] {how}: tokens before {live} -> after {after} | worker idle {idle} MB, with documents {held} MB, after end: " + ", ".join(f"{s}s {m}" for s, m in samples), flush=True)
    b.close()
