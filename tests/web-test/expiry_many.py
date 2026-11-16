"""WT-24, many runs: rounds of N people on one short-limit portal; each opens the portal (odd ones with a PDF, even ones with
nothing, so their workers idle-stop before the session ends), tabs closed a little apart; every session must end each round.
python3 expiry_many.py <dev base> <data root> <gateway log> <people> <rounds>      (Web Test chat; test tooling only)"""
import sys, time, os
from playwright.sync_api import sync_playwright
B, ROOT, LOG, N, R = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
W = os.path.join(ROOT, "workers")
def log(): return open(LOG, errors="replace").read()
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for r in range(1, R + 1):
        tag = f"{int(time.time()) % 100000}"; pages = []; e0 = log().count("Session ended")
        for i in range(N):
            c = b.new_context(); c.add_cookies([{"name": "chvd-dev-user", "value": f"m{i}-{tag}", "url": B}]); pg = c.new_page()
            pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=60000)
            if i % 2:
                with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
                fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg", timeout=60000)
            pages.append((c, pg))
        for c, pg in pages: pg.close(); time.sleep(0.4)
        t = time.time(); n = 0; when = None
        while time.time() - t < 75:
            n = log().count("Session ended") - e0
            if n >= N: when = round(time.time() - t); break
            time.sleep(1)
        left = len(os.listdir(W)) if os.path.isdir(W) else 0; time.sleep(8); left = len(os.listdir(W)) if os.path.isdir(W) else 0
        ok = n >= N and left == 0; bad += not ok
        L = log(); print(("PASS " if ok else "FAIL ") + f"round {r}: {n} of {N} sessions ended (last at {when} s; limit 40 s); worker folders left {left}; "
              f"'pass failed' lines {L.count('pass failed')}, 'given up' {L.count('given up')}, 'wasn\\'t reached' {L.count('reached for')}", flush=True)
        for c, _ in pages: c.close()
    print(f"SUMMARY {R - bad} of {R} rounds clean", flush=True); os._exit(0)
