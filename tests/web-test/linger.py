import sys, time, os, subprocess, threading
from playwright.sync_api import sync_playwright
B=sys.argv[1]; eng=sys.argv[2]; style=sys.argv[3]; root=sys.argv[4]; cap=int(sys.argv[5])
W=os.path.join(root,"workers"); who=f"lg-{style}-{int(time.time())%100000}"
def ws(): return set(os.listdir(W)) if os.path.isdir(W) else set()
with sync_playwright() as p:
    b=getattr(p,eng).launch(); c=b.new_context(); c.add_cookies([{"name":"chvd-dev-user","value":who,"url":B}]); before=ws(); pg=c.new_page()
    pg.goto(B+"/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg", timeout=30000); pg.wait_for_timeout(1500)
    mine=ws()-before
    if style=="pageclose": pg.close(); time.sleep(1); b.close()
    elif style=="browserclose": b.close()
    elif style=="kill": subprocess.run("pkill -9 -f '%s' ; true" % ("chrome-headless-shell" if eng=="chromium" else "firefox-bin|/firefox/firefox"), shell=True)
    t=time.time(); gone=None
    while time.time()-t<cap:
        if not (mine & ws()): gone=round(time.time()-t); break
        time.sleep(2)
    print(f"[{eng}] {style} ({who}): worker and files gone {gone} s after the browser left (session limit 40 s, worker idle 5 s)" if gone is not None else f"[{eng}] {style} ({who}): worker and files STILL THERE after {cap} s; pdfs held: {sum(f.endswith('.pdf') for w in mine for _,_,n in os.walk(os.path.join(W,w)) for f in n)}", flush=True)
    os._exit(0)
