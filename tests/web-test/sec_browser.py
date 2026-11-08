"""Security and isolation probes through a real browser (Web Test chat; test tooling only).

python3 sec_browser.py <base> <corpus folder> <out folder> <server log> <data root>
Gateway mode, Development sign-in (X-Dev-User picks the person)."""
import json, os, re, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

base, corpus, out, log, data_root = [a.rstrip('/') for a in sys.argv[1:6]]
os.makedirs(out, exist_ok=True)
results = []
def check(name, ok, detail=""):
    results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:400]})
    print(("PASS " if ok else "FAIL ") + name + (" — " + str(detail)[:300] if detail else ""), flush=True)

def http(path, user, method="GET", headers=None):
    req = urllib.request.Request(base + path, method=method, headers={"X-Dev-User": user, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()

def workers():
    n = 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"Portal__Mode=Worker" in open(f"/proc/{pid}/environ", "rb").read(): n += 1
        except OSError: pass
    return n

def files_on_disk():
    found = []
    for root, _, fs in os.walk(data_root):
        found += [os.path.join(root, f) for f in fs]
    return found

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    def person(name):
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": name}, accept_downloads=True)
        ctx.add_init_script("window.print = function () {};")
        pg = ctx.new_page(); pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=60000)
        return ctx, pg

    def upload(pg, files, wait=20000):
        """Hand files to the Upload chooser; return what happened."""
        pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload", timeout=60000)
        before = pg.evaluate("document.body.innerText")
        with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
        t0 = time.time(); fc.value.set_files(files)
        drawn = False
        try:
            pg.wait_for_function("() => !!document.querySelector('.rpage svg')", timeout=wait); drawn = True
        except Exception: pass
        after = pg.evaluate("document.body.innerText")
        new = [l for l in after.splitlines() if l.strip() and l not in before.splitlines()]
        return {"drawn": drawn, "url": pg.url, "ms": round((time.time() - t0) * 1000), "new_text": new[:8]}

    # ---- 1. isolation: print ticket and download token are owner-only ----
    ca, a = person("iso-a")
    r = upload(a, os.path.join(corpus, "text-13.pdf"))
    check("A opens a PDF", r["drawn"], r)
    n0 = len(open(log).read())
    a.keyboard.press("Control+p"); a.wait_for_selector("button.primary:has-text('Print')", timeout=10000)
    a.click("button:has-text('Current')"); a.click("button.primary:has-text('Print')")
    ticket = None
    for _ in range(60):
        m = re.findall(r"GET http://[^ ]*(/portal/print/[A-Za-z0-9_-]+)", open(log).read()[n0:])
        if m: ticket = m[-1]; break
        time.sleep(0.25)
    check("A's print reaches the server", ticket is not None, ticket)
    if ticket:
        s_b, _ = http(ticket, "iso-b")
        check("B can't fetch A's print PDF", s_b == 404, s_b)
        s_a, body = http(ticket, "iso-a")
        open(os.path.join(out, "print-current.pdf"), "wb").write(body)
        check("A can fetch own print PDF", s_a == 200 and body[:5] == b"%PDF-", (s_a, len(body)))
        txt = subprocess.run(["pdftotext", os.path.join(out, "print-current.pdf"), "-"], capture_output=True, text=True).stdout
        imgs = subprocess.run(["pdfimages", "-list", os.path.join(out, "print-current.pdf")], capture_output=True, text=True).stdout.splitlines()[2:]
        check("print PDF is vector (text extractable, no page images)", "Page 1 of 13" in txt and not imgs, f"text={'Page 1 of 13' in txt} images={len(imgs)}")
        pages = subprocess.run(["pdfinfo", os.path.join(out, "print-current.pdf")], capture_output=True, text=True).stdout
        check("print 'Current' gives exactly one page", re.search(r"Pages:\s+1\b", pages) is not None, re.findall(r"Pages:\s+\d+", pages))
        s_anon = urllib.request.Request(base + ticket)
    # no-print file: refused at the card, and the server
    r = upload(a, os.path.join(corpus, "no-print.pdf"))
    a.keyboard.press("Control+p"); time.sleep(1.5)
    card = a.evaluate("document.body.innerText")
    a.screenshot(path=os.path.join(out, "no-print-card.png"))
    check("a no-print PDF: print card refuses", "permissions don't allow printing" in card, [l for l in card.splitlines() if "print" in l.lower()][:4])

    # ---- 2. hostile file names (valid PDF content) ----
    pdf = open(os.path.join(corpus, "text-3.pdf"), "rb").read()
    names = ["../../../../etc/passwd.pdf", "..\\..\\windows\\win.pdf", "CON.pdf", "a" * 250 + ".pdf", "ok<img src=x onerror=alert(1)>.pdf",
             "rtl‮fdp.exe.pdf", ".pdf", "spaces   .pdf", "tab\tname.pdf", "日本語ファイル.pdf", "x" * 1000 + ".pdf"]
    cn, nn = person("names")
    alerts = []
    nn.on("dialog", lambda d: (alerts.append(d.message), d.dismiss()))
    for nm in names:
        try:
            r = upload(nn, [{"name": nm, "mimeType": "application/pdf", "buffer": pdf}])
        except Exception as e:
            r = {"error": str(e).splitlines()[0]}
        disk = [f for f in files_on_disk() if "/workers/" in f]
        escaped = [f for f in files_on_disk() if "etc/passwd" in f or "windows" in f.lower()]
        outside = [f for f in disk if ".." in f]
        check(f"hostile name {nm[:40]!r}: no path escape", not outside and not escaped and not os.path.exists("/etc/passwd.pdf"), r)
    check("no script ran from a file name", not alerts, alerts)
    nn.screenshot(path=os.path.join(out, "hostile-names.png"))
    print("names on disk:", sorted({os.path.basename(f) for f in files_on_disk() if f.endswith('.pdf')})[:20])

    # ---- 3. wrong content / damaged / hostile documents; another person keeps working ----
    cw, w = person("watcher")
    upload(w, os.path.join(corpus, "text-13.pdf"))
    def watcher_turn():
        t0 = time.time()
        try:
            w.click("button.tb-pg-btn[aria-label='Next page']", timeout=30000)
            w.wait_for_timeout(50)
            return round((time.time() - t0) * 1000)
        except Exception as e: return str(e).splitlines()[0]
    ch, h = person("hostile")
    for f in ["fake.pdf", "pdf-as-docx.docx", "docx-as-pdf.pdf", "empty.pdf", "truncated.pdf", "garbage-after-header.pdf",
              "deep-nest.pdf", "pages-loop.pdf", "flate-bomb.pdf", "zip-bomb.docx", "zip-bomb.xlsx", "user-password.pdf", "over-limit.pdf"]:
        wb = workers()
        try:
            r = upload(h, os.path.join(corpus, f), wait=45000)
        except Exception as e:
            r = {"error": str(e).splitlines()[0]}
        h.screenshot(path=os.path.join(out, f"hostile-{f}.png"))
        turn = watcher_turn()
        alive = True
        try: h.evaluate("1");
        except Exception: alive = False
        print(f"  {f}: {json.dumps(r)[:300]} | workers {wb}->{workers()} | watcher next-page {turn}", flush=True)
        results.append({"case": f"hostile file {f}", "pass": None, "detail": json.dumps({**r, "watcher_ms": turn})[:400]})
        if isinstance(turn, str):
            check(f"other person unaffected by {f}", False, turn)
    check("watcher still served after all hostile files", isinstance(watcher_turn(), int))
    b.close()

json.dump(results, open(os.path.join(out, "sec_browser.json"), "w"), indent=1)
fails = [r for r in results if r["pass"] is False]
print(f"{len([r for r in results if r['pass']])} pass, {len(fails)} fail")
