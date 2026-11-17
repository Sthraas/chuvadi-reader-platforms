"""D-185 / D-191 encoding picker, independent of the Web chat's encoding_picker.py: Windows-1252 and UTF-16 text, UTF-8 Markdown,
Windows-1252 HTML with a script; what Automatic makes of each, what the picker offers, that choosing reads the same bytes again,
that one tab's choice doesn't touch another tab, and that HTML script doesn't run.
python3 encoding_probe.py <dev base> <out> <engine>      (Web Test chat; test tooling only)"""
import sys, time, os
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, OUT, eng = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + f"[{eng}] {n}" + (f" — {d}" if d != "" else ""), flush=True)
BODY = "() => (document.querySelector('.rcanvas, .reader-main, main') || document.body).innerText"
def up(pg, f):
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(f); pg.wait_for_selector(f".rtab:has(.rtab-name:text-is('{os.path.basename(f)}'))", timeout=60000); pg.wait_for_timeout(1500)
def encbtn(pg): return pg.locator("button.sb-btn[aria-label*='Now ']").first
def label(pg): return encbtn(pg).inner_text().strip() if encbtn(pg).count() else None
def choose(pg, name):
    encbtn(pg).click(); pg.wait_for_selector(".enc-list", timeout=10000); rows = pg.locator(".enc-row .enc-n").all_inner_texts()
    pg.click(f".enc-row:has(.enc-n:text-is('{name}'))"); pg.wait_for_timeout(1200); pg.keyboard.press("Escape"); pg.wait_for_timeout(400); return rows
with sync_playwright() as p:
    b = getattr(p, eng).launch(); c = b.new_context(viewport={"width": 1400, "height": 900}); sign_in_as(c, B, f"encp-{eng}-{int(time.time()) % 10000}"); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:120])); pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload")
    up(pg, "/tmp/enc/cp1252.txt"); t = pg.evaluate(BODY); l0 = label(pg)
    print(f"INFO [{eng}] Windows-1252 file on Automatic: status bar '{l0}', text starts {t.strip()[:40]!r}")
    rows = choose(pg, "Windows-1252"); t = pg.evaluate(BODY)
    check("Windows-1252 chosen: every character of the file is right", "Café – naïve £5 “quoted” Zoë" in t and "façade" in t, t.strip()[:60])
    check("the status bar names it", label(pg) == "Windows-1252", label(pg)); print(f"INFO [{eng}] encodings offered: {rows}")
    pg.screenshot(path=f"{OUT}/enc-cp1252-{eng}.png")
    up(pg, "/tmp/enc/utf8.md"); t = pg.evaluate(BODY)
    check("UTF-8 Markdown reads right", "Heading é" in t and "Body – தமிழ் ✓" in t, (label(pg), t.strip()[:50]))
    check("the second tab starts on its own reading, not the first tab's choice", label(pg) != "Windows-1252", label(pg))
    pg.click(".rtab:has(.rtab-name:text-is('cp1252.txt'))"); pg.wait_for_timeout(1200); t = pg.evaluate(BODY)
    check("back on the first tab its choice is kept", label(pg) == "Windows-1252" and "Café – naïve" in t, (label(pg), t.strip()[:30]))
    up(pg, "/tmp/enc/latin.html"); pg.wait_for_timeout(1000)
    fr = [f for f in pg.frames if f != pg.main_frame]; t = pg.evaluate(BODY) + " ".join((f.locator("body").inner_text() if f.locator("body").count() else "") for f in fr)
    print(f"INFO [{eng}] Windows-1252 HTML on Automatic: status bar '{label(pg)}', text {t.strip()[-40:]!r}")
    if "Prix: 5 € – déjà" not in t and encbtn(pg).count(): choose(pg, "Windows-1252"); fr = [f for f in pg.frames if f != pg.main_frame]; t = pg.evaluate(BODY) + " ".join((f.locator("body").inner_text() if f.locator("body").count() else "") for f in fr)
    check("the Windows-1252 HTML reads right (on Automatic or once chosen)", "Prix: 5 € – déjà" in t, t.strip()[-50:])
    check("script in the HTML file did not run", pg.title() != "x" and all(f.evaluate("document.title") != "x" for f in fr if not f.is_detached()), pg.title())
    def tryup(f, wait=4000):
        with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
        fc.value.set_files(f); pg.wait_for_timeout(wait); d = pg.locator(".chvd-portal-overlay")
        msg = d.inner_text().replace("\n", " | ")[:220] if d.count() else ""
        opened = os.path.basename(f) in pg.locator(".rtab-name").all_inner_texts()
        if d.count():
            b2 = d.locator("button").first
            if b2.count(): b2.click(); pg.wait_for_timeout(400)
        return opened, msg
    for f, txt in (("/tmp/enc/utf16.txt", "Unicode sixteen: தமிழ் café"), ("/tmp/enc/utf16be.txt", "BE sixteen: தமிழ் café"), ("/tmp/enc/utf16le.md", "தமிழ் LE markdown")):
        ok, msg = tryup(f)
        if ok: pg.click(f".rtab:has(.rtab-name:text-is('{os.path.basename(f)}'))"); pg.wait_for_timeout(1200)
        t = pg.evaluate(BODY) if ok else ""
        check(f"WT-26: {os.path.basename(f)} (UTF-16 with byte-order mark) opens and reads right", ok and txt in t, (msg, label(pg), t.strip()[:60]))
        if ok: check(f"WT-26: the status bar names UTF-16 for {os.path.basename(f)}", "UTF-16" in (label(pg) or ""), label(pg))
    ok, msg = tryup("/tmp/enc/utf16le-nobom.txt")
    check("WT-26: UTF-16 without the mark is refused, and the message says how to save it", not ok and "byte-order mark" in msg and "isn't a valid" not in msg, msg)
    for f in ("utf32.txt", "zeros.txt", "badsurr.txt", "exe-as.txt"):
        ok, msg = tryup("/tmp/enc/" + f)
        check(f"WT-26: a binary under a text name stays refused ({f})", not ok and msg != "", msg[:120])
    check("no page errors", not errs, errs[:3]); b.close()
