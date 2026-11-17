"""aae1d69e (patch 32): a dead worker's late clean-up must never touch the person's replacement worker. A person's
worker is killed (SIGKILL) and the page reloaded at once, so the replacement starts in the same folder while the old
one's exit is still being handled; the person uploads again and must be able to read on, and the new file must still
be there 10 s later. Repeated N times. Gateway log is searched for errors.
python3 cleanup_race.py <dev base> <data root> <gateway log> <engine> <rounds> [seconds between kill and reload, default 0]      (Web Test chat; test tooling only)"""
import sys, time, os, signal, subprocess
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, ROOT, LOG, eng, N = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]); DELAY = float(sys.argv[6]) if len(sys.argv) > 6 else 0
W = os.path.join(ROOT, "workers")
def ws(): return set(os.listdir(W)) if os.path.isdir(W) else set()
def pid_of(folder):
    for pid in subprocess.run("pgrep -f ChuvadiReader.Web.dll", shell=True, capture_output=True, text=True).stdout.split():
        try:
            env = open(f"/proc/{pid}/environ", "rb").read().decode(errors="replace")
            if "Portal__Mode=Worker" in env and folder in env + open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace"): return int(pid)
        except Exception: pass
def up(pg):
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg", timeout=60000)
def pdfs(folder): return sum(1 for _, _, fs in os.walk(os.path.join(W, folder)) for f in fs if f.endswith(".pdf"))
bad = 0; l0 = len(open(LOG, errors="replace").read())
with sync_playwright() as p:
    b = getattr(p, eng).launch(); c = b.new_context(); sign_in_as(c, B, f"race-{eng}-{int(time.time()) % 100000}"); pg = c.new_page()
    before = ws(); pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); up(pg)
    mine = (ws() - before).pop()
    for r in range(1, N + 1):
        pid = pid_of(mine)
        if pid is None:
            print(f"INFO [{eng}] round {r}: no worker for {mine}; folders {sorted(ws())}; reloading", flush=True); pg.reload(); pg.wait_for_selector('nav.leftbar >> text=Upload', timeout=30000); up(pg); time.sleep(2); pid = pid_of(mine)
            if pid is None: print(f'FAIL [{eng}] round {r}: still no worker'); bad += 1; break
        os.kill(pid, signal.SIGKILL); time.sleep(DELAY)
        try:
            pg.reload(timeout=30000); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); up(pg); ok_open = True
        except Exception as e:
            ok_open = False; print(f'INFO [{eng}] round {r}: {str(e)[:140]} | url {pg.url} | page: {pg.inner_text("body")[:200]!r} | folders {sorted(ws())}', flush=True); pg.screenshot(path=f'/tmp/out18/race-{eng}-{r}.png')
        new = pid_of(mine); time.sleep(10)
        n = pdfs(mine) if os.path.isdir(os.path.join(W, mine)) else -1
        try: pg.locator("button.tb-pg-btn[aria-label='Next page']").click(timeout=10000); pg.wait_for_timeout(1200); reads = pg.locator(".rpage svg").count() > 0
        except Exception: reads = False
        ok = ok_open and new is not None and new != pid and n >= 1 and reads; bad += not ok
        print(("PASS " if ok else "FAIL ") + f"[{eng}] round {r}: killed {pid}, replacement {new}, uploaded again {ok_open}, its file still there after 10 s {n >= 1} ({n}), reads on {reads}", flush=True)
    L = open(LOG, errors="replace").read()[l0:]
    errs = [l.strip()[:160] for l in L.splitlines() if "DirectoryNotFound" in l or "fail:" in l or "Unhandled" in l]
    print(("PASS " if not errs else "FAIL ") + f"[{eng}] gateway log: no DirectoryNotFoundException or failures — {errs[:3]}; exits logged {L.count('ended with code')}")
    print(f"SUMMARY [{eng}] {N - bad} of {N} rounds clean", flush=True); os._exit(0)
