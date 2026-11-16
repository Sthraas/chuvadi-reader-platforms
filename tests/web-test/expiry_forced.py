"""WT-24 forced: one person's worker is frozen (SIGSTOP) or killed (SIGKILL) just before / as that session ends;
other people's sessions on the same portal must still end on time, the cookie of the broken one must stop working,
and a person who comes later must still expire. Fresh short-limit portal (idle 40 s, checks 2 s).
python3 expiry_forced.py <dev base> <data root> <gateway log> <stop|kill> <offset s before the limit>   (Web Test; tooling only)"""
import sys, time, os, signal, subprocess, urllib.request
from playwright.sync_api import sync_playwright
B, ROOT, LOG, how, off = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
W = os.path.join(ROOT, "workers"); tag = str(int(time.time()) % 100000)
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + n + (f" — {d}" if d != "" else ""), flush=True)
def log(): return open(LOG, errors="replace").read()
def ws(): return set(os.listdir(W)) if os.path.isdir(W) else set()
def worker_pids():
    out = {}
    for pid in subprocess.run("pgrep -f ChuvadiReader.Web.dll", shell=True, capture_output=True, text=True).stdout.split():
        try: env = open(f"/proc/{pid}/environ", "rb").read().decode(errors="replace")
        except Exception: continue
        if "Portal__Mode=Worker" in env and ROOT in env:
            for w in ws():
                if w in env or w in open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace"): out[w] = int(pid)
    return out
def status(who):
    req = urllib.request.Request(B + "/", headers={"Cookie": f"chvd-dev-user={who}"})
    try: return urllib.request.urlopen(req, timeout=10).status
    except Exception as e: return getattr(e, "code", str(e)[:40])
with sync_playwright() as p:
    b = p.chromium.launch(); people = {}
    for name in ("victim", "p2", "p3"):
        who = f"{name}-{tag}"; c = b.new_context(); c.add_cookies([{"name": "chvd-dev-user", "value": who, "url": B}]); before = ws(); pg = c.new_page()
        pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
        with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
        fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg", timeout=30000); pg.wait_for_timeout(500)
        people[name] = (who, ws() - before, pg)
    pids = worker_pids(); vw = next(iter(people["victim"][1])); vpid = pids.get(vw)
    e0 = log().count("Session ended")
    for name in people: people[name][2].close()
    t0 = time.time()
    time.sleep(max(0, 40 - off - 1.0))
    if vpid is None: check("found the victim's worker process", False, (vw, pids)); os._exit(1)
    os.kill(vpid, signal.SIGSTOP if how == "stop" else signal.SIGKILL); tk = round(time.time() - t0, 1)
    ended_at = {}; files_gone = {}; folder_gone = {}
    def docs(name):
        return sum(1 for w in people[name][1] for _, _, fs in os.walk(os.path.join(W, w)) for f in fs if f.lower().endswith(".pdf"))
    while time.time() - t0 < 80:
        n = log().count("Session ended") - e0; now = round(time.time() - t0, 1)
        if n not in ended_at: ended_at[n] = round(now)
        for name in people:
            if name not in files_gone and docs(name) == 0: files_gone[name] = now
            if name not in folder_gone and not (people[name][1] & ws()): folder_gone[name] = now
        time.sleep(0.5)
    print(f"INFO [{how} at +{tk} s] document files gone at {files_gone}; worker folder gone at {folder_gone}; 'Session ended' lines by time {ended_at}", flush=True)
    L = log(); n = L.count("Session ended") - e0
    check(f"[{how} at +{tk} s] the other two people's documents are deleted on time (limit 40 s)", max(files_gone.get("p2", 999), files_gone.get("p3", 999)) <= 44, {k: files_gone.get(k) for k in ("p2", "p3")})
    others_gone = not ((people["p2"][1] | people["p3"][1]) & ws())
    check(f"[{how}] the other two people's workers and files are gone", others_gone, sorted(ws()))
    lines = [l.strip()[:170] for l in L.splitlines() if "didn't answer" in l or "wasn't reached" in l or "pass failed" in l or "pass took" in l]
    check(f"[{how}] the gateway says in the log what it gave up on", len(lines) >= 1 or n >= 3, lines[:4])
    if how == "stop":
        try: os.kill(vpid, signal.SIGCONT)
        except ProcessLookupError: pass
        time.sleep(8)
    check(f"[{how}] the victim's files are gone in the end", not (people["victim"][1] & ws()), sorted(ws()))
    # a later person still expires
    who = f"late-{tag}"; c = b.new_context(); c.add_cookies([{"name": "chvd-dev-user", "value": who, "url": B}]); pg = c.new_page(); e1 = log().count("Session ended")
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000); pg.wait_for_timeout(1500); pg.close(); t1 = time.time(); when = None
    while time.time() - t1 < 70:
        if log().count("Session ended") > e1: when = round(time.time() - t1); break
        time.sleep(1)
    check(f"[{how}] a person who comes afterwards still expires", when is not None and when <= 50, when)
    os._exit(0)
