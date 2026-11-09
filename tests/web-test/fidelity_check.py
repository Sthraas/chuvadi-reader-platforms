"""Word/Excel data fidelity through the portal (Web Test chat; test tooling only).
python3 fidelity_check.py <dev base> <server log> <corpus with expected.json> <out> <engine> <file>...
For each file: open it, collect the text drawn in every page SVG (textContent of each <text>, in order),
and the text of the server's print PDF (pypdf), then check every expected token appears exactly (spaces,
case, spelling, scripts) in at least one of them; print what is missing and how it came out instead."""
import json, os, re, sys, time, urllib.request, unicodedata
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

base, log, corpus, out, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
files = sys.argv[6:]
os.makedirs(out, exist_ok=True)
exp = json.load(open(os.path.join(corpus, "expected.json")))

with sync_playwright() as p:
    b = getattr(p, engine).launch()
    for f in files:
        user = f"fid-{engine}-{os.path.basename(f).replace('.', '-')}"
        c = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": user})
        c.add_init_script("window.print = function () {};")
        pg = c.new_page(); pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
        with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
        t0 = time.time(); fc.value.set_files(f)
        try:
            pg.wait_for_selector(".rpage svg text", timeout=60000)
        except Exception:
            body = pg.evaluate("document.body.innerText")
            print(f"[{engine}] {os.path.basename(f)}: DID NOT OPEN — {[l for l in body.splitlines() if 'open' in l.lower() or 'couldn' in l.lower()][:3]}")
            pg.screenshot(path=os.path.join(out, f"fail-{engine}-{os.path.basename(f)}.png")); c.close(); continue
        ms = round((time.time() - t0) * 1000); pg.wait_for_timeout(1500)
        # scroll through every page so all are drawn
        n = pg.evaluate("document.querySelectorAll('.rpage-wrap').length")
        for i in range(n):
            pg.evaluate(f"document.querySelector('.rpage-wrap[data-page=\"{i}\"]').scrollIntoView()"); pg.wait_for_timeout(250)
        svg = pg.evaluate("""() => [...document.querySelectorAll('.rpage svg')].map(s =>
            [...s.querySelectorAll('text')].map(t => t.textContent).join('\\n')).join('\\n')""")
        pg.screenshot(path=os.path.join(out, f"{engine}-{os.path.basename(f)}.png"), full_page=False)
        # server print PDF (all pages)
        pdf_text = ""
        try:
            n0 = len(open(log).read())
            pg.keyboard.press("Control+p"); pg.wait_for_selector("button.primary:has-text('Print')", timeout=15000)
            pg.click("button.primary:has-text('Print')")
            for _ in range(80):
                m = re.findall(r"GET http://[^ ]*(/portal/print/[A-Za-z0-9_-]+)", open(log).read()[n0:])
                if m: break
                time.sleep(0.25)
            if m:
                body = urllib.request.urlopen(urllib.request.Request(base + m[-1], headers={"X-Dev-User": user})).read()
                pf = os.path.join(out, f"print-{engine}-{os.path.basename(f)}.pdf"); open(pf, "wb").write(body)
                pdf_text = "\n".join(pg_.extract_text() or "" for pg_ in PdfReader(pf).pages)
        except Exception as e:
            pdf_text = ""; print("   (print step:", str(e).splitlines()[0], ")")
        expected = exp["tokens"] + (exp["numbers"] if f.endswith(".xlsx") else [])
        miss = []
        for tok in expected:
            if tok in svg or tok in pdf_text: continue
            core = tok.strip().split()[0] if tok.strip() else tok
            near = [l for l in (svg + "\n" + pdf_text).splitlines() if core[:5] in l][:2]
            miss.append((tok, near))
        print(f"[{engine}] {os.path.basename(f)}: opened in {ms} ms, {n} page(s); {len(expected) - len(miss)}/{len(expected)} exact")
        for tok, near in miss: print(f"     missing {tok!r} -> seen as {near!r}")
        open(os.path.join(out, f"svgtext-{engine}-{os.path.basename(f)}.txt"), "w").write(svg)
        open(os.path.join(out, f"pdftext-{engine}-{os.path.basename(f)}.txt"), "w").write(pdf_text)
        c.close()
    b.close()
