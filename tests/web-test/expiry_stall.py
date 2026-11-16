"""WT-24: does the session end after the tab is closed? One visit, tab closed cleanly, browser left running; waits 70 s.
Run against a fresh short-limit portal (idle 40 s, checks 2 s, worker idle 5 s); repeat on fresh portals - about 1 run in 8 stalls.
python3 expiry_stall.py <dev base> <engine> <gateway log>      (Web Test chat; test tooling only)"""
import sys, time, os, subprocess
from playwright.sync_api import sync_playwright
B=sys.argv[1]; eng=sys.argv[2]; L=sys.argv[3]; who=f"rs2-{eng}-{int(time.time())%100000}"
def ended(): return int(subprocess.run(f"grep -c 'Session ended' {L}", shell=True, capture_output=True, text=True).stdout or 0)
with sync_playwright() as p:
    b=getattr(p,eng).launch(); c=b.new_context(); c.add_cookies([{"name":"chvd-dev-user","value":who,"url":B}])
    for r in (1,):
        pg=c.new_page(); e0=ended(); pg.goto(B+"/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); pg.wait_for_timeout(2500)
        ck=sorted(x["name"] for x in c.cookies()); pg.close()
        t=time.time(); when=None
        while time.time()-t<70:
            if ended()>e0: when=round(time.time()-t); break
            time.sleep(2)
        print(f"[{eng}] same browser, visit {r}: session ended after {when} s (limit 40 s) | cookies {ck}", flush=True)
        time.sleep(3)
    os._exit(0)
