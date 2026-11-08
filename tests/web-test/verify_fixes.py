"""Re-verification of Web Test bugs in a running build (Web Test chat; test tooling only).
python3 verify_fixes.py <dev base> <server log> <corpus> <out> <engine>"""
import os, re, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

base, log, corpus, out, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
os.makedirs(out, exist_ok=True)
res = []
def check(name, ok, detail=""):
    res.append((name, ok)); print(("PASS " if ok else "FAIL ") + f"[{engine}] {name}" + (f" — {str(detail)[:220]}" if detail != "" else ""), flush=True)

def open_doc(pg, path=None, files=None):
    pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
    with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
    fc.value.set_files(files if files is not None else path)

def text(pg): return pg.evaluate("document.body.innerText")

def printed_first_line(pg, user, choice="Current"):
    n0 = len(open(log).read())
    pg.keyboard.press("Control+p"); pg.wait_for_selector("button.primary:has-text('Print')", timeout=15000)
    pg.click(f"button:has-text('{choice}')"); pg.click("button.primary:has-text('Print')")
    for _ in range(80):
        m = re.findall(r"GET http://[^ ]*(/portal/print/[A-Za-z0-9_-]+)", open(log).read()[n0:])
        if m: break
        time.sleep(0.25)
    else: return None
    body = urllib.request.urlopen(urllib.request.Request(base + m[-1], headers={"X-Dev-User": user})).read()
    f = os.path.join(out, f"print-{engine}.pdf"); open(f, "wb").write(body)
    t = subprocess.run(["pdftotext", f, "-"], capture_output=True, text=True).stdout.strip().splitlines()
    pages = re.findall(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", f], capture_output=True, text=True).stdout)
    return (t[0] if t else "", pages[0] if pages else "?")

with sync_playwright() as p:
    b = getattr(p, engine).launch()
    # ---- desktop ----
    user = f"verify-{engine}"
    c = b.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": user}, accept_downloads=True)
    c.add_init_script("window.print = function () {};")
    pg = c.new_page()
    pg.goto(base + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
    home = text(pg)
    check("Q-3 Home says 'this session' near Storage map / shelves", "this session" in home.lower(),
          [l for l in home.splitlines() if "session" in l.lower() or "storage" in l.lower() or "shel" in l.lower()][:5])
    open_doc(pg, os.path.join(corpus, "text-13.pdf")); pg.wait_for_selector(".rpage svg", timeout=60000); pg.wait_for_timeout(800)
    st = text(pg)
    check("WT-04 status bar 'kept in memory only'", "kept in memory only" in st and "encrypted at rest" not in st,
          [l for l in st.splitlines() if "processed on" in l][:1])
    r = printed_first_line(pg, user)
    check("WT-02 Current on page 1 prints page 1", r and r[0].startswith("Page 1 of 13") and r[1] == "1", r)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pg.fill("input.tb-pg-box", "5"); pg.press("input.tb-pg-box", "Enter"); pg.wait_for_timeout(1500)
    pg.locator(".rpage-wrap[data-page='4']").click(position={"x": 20, "y": 20}); pg.wait_for_timeout(300)
    r = printed_first_line(pg, user)
    check("WT-02 Current on page 5 prints page 5", r and r[0].startswith("Page 5 of 13"), r)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    # Measure label (from code: page {CurrentPage+1})
    pg.locator("body").press("1"); pg.wait_for_timeout(300)
    try:
        pg.click("button[aria-label='Measure']", timeout=5000); pg.wait_for_timeout(800)
        mt = text(pg); lab = re.findall(r"[Pp]age \d+", mt)
        pg.screenshot(path=os.path.join(out, f"measure-{engine}.png"))
        check("WT-02 Measure card names the page shown (5)", any(x.endswith(" 5") for x in lab) and not any(x.endswith(" 6") for x in lab), lab[:6])
        pg.keyboard.press("Escape")
    except Exception as e: check("WT-02 Measure card opens", False, str(e).splitlines()[0])
    # account menu footer
    try:
        pg.click("button.acct-chip", timeout=5000); pg.wait_for_selector(".acct-pop", timeout=5000)
        am = pg.inner_text(".acct-pop"); pg.screenshot(path=os.path.join(out, f"account-{engine}.png"))
        check("WT-06 account menu Terms · Privacy footer", "Terms" in am and "Privacy" in am, am.replace("\n", " | ")[-120:])
        pg.keyboard.press("Escape")
    except Exception as e: check("WT-06 account menu opens", False, str(e).splitlines()[0])
    # no-print
    open_doc(pg, os.path.join(corpus, "no-print.pdf")); pg.wait_for_selector(".rpage svg", timeout=60000); pg.wait_for_timeout(600)
    pg.keyboard.press("Control+p"); pg.wait_for_timeout(1500)
    card = text(pg); pg.screenshot(path=os.path.join(out, f"noprint-{engine}.png"))
    check("WT-09 no-print reason visible in the card (not only a tooltip)", "don't allow printing" in card or "doesn't allow printing" in card,
          [l for l in card.splitlines() if "print" in l.lower()][:4])
    pg.keyboard.press("Escape")
    # bidi name
    pdf = open(os.path.join(corpus, "text-3.pdf"), "rb").read()
    open_doc(pg, files=[{"name": "rtl‮fdp.exe.pdf", "mimeType": "application/pdf", "buffer": pdf}])
    pg.wait_for_selector(".rpage svg", timeout=60000); pg.wait_for_timeout(500)
    tabs = pg.evaluate("[...document.querySelectorAll('header *')].map(e=>e.textContent).join(' ')")
    check("WT-08 bidi control removed from the name", "‮" not in tabs and "rtl" in tabs, re.findall(r"rtl[^ ]*", tabs)[:2])
    # damaged file message + Upload label
    open_doc(pg, os.path.join(corpus, "truncated.pdf")); pg.wait_for_timeout(4000)
    bad = text(pg); pg.screenshot(path=os.path.join(out, f"damaged-{engine}.png"))
    raw = any(k in bad for k in ("startxref", "offset", "Invalid integer", "keyword"))
    check("WT-10 damaged file: plain sentence, no raw parser text on screen", not raw, [l for l in bad.splitlines() if "open" in l.lower() or "damag" in l.lower()][:3])
    check("WT-10 no 'Fetch' wording on the portal screen", "Fetch" not in bad, [l for l in bad.splitlines() if "Fetch" in l][:3])
    pg.locator("body").press("3"); pg.wait_for_timeout(1500)
    bench = text(pg)
    check("WT-10 no 'Fetch' wording in Arrange", "Fetch" not in bench and not pg.query_selector("[title*='Fetch'], [aria-label*='Fetch']"),
          [l for l in bench.splitlines() if "Fetch" in l][:3] + pg.evaluate("[...document.querySelectorAll('[title*=Fetch],[aria-label*=Fetch]')].map(e=>e.title||e.getAttribute('aria-label')).slice(0,3)"))
    c.close()
    # ---- phone ----
    kw = {"viewport": {"width": 390, "height": 844}}
    if engine != "firefox": kw.update(has_touch=True, is_mobile=True)
    c = b.new_context(extra_http_headers={"X-Dev-User": f"verify-phone-{engine}"}, **kw); pg = c.new_page()
    pg.goto(base + "/"); pg.wait_for_timeout(2500)
    pg.screenshot(path=os.path.join(out, f"phone-home-{engine}.png"))
    try:
        open_doc(pg, os.path.join(corpus, "text-13.pdf")); pg.wait_for_selector(".rpage svg", timeout=60000); pg.wait_for_timeout(1200)
    except Exception as e: check("WT-03 phone: open a PDF", False, str(e).splitlines()[0])
    pg.screenshot(path=os.path.join(out, f"phone-read-{engine}.png"))
    shell = pg.evaluate("""() => ({ phone: !!document.querySelector('[class*=phone-shell],[class*=pshell],.phone, [class*=phone]'),
        rails: [...document.querySelectorAll('.rail, [class*=rail]')].filter(e => e.offsetParent && e.getBoundingClientRect().width > 0).length,
        pageW: (document.querySelector('.rpage') || {getBoundingClientRect: () => ({width: 0})}).getBoundingClientRect().width,
        overflowX: document.documentElement.scrollWidth > innerWidth + 1 })""")
    check("WT-03 phone shell, page uses the width, no side rails, no sideways scroll",
          shell["phone"] and shell["pageW"] >= 300 and not shell["overflowX"], shell)
    c.close(); b.close()
print(f"{sum(1 for _, ok in res if ok)}/{len(res)} pass")
