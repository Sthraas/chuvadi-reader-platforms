"""Patch 32/33 on the portal, independent of the Web chat's scripts: D-198 library holds (redaction held, also by
direct address and key; signatures shown with no verdict; page operations ask first and Cancel writes nothing;
Excel conditional colours not drawn, own fills kept), and D-194 Sign out (nothing unsaved: no card; Discard: signed
out, files gone, no download). Needs /tmp/p33 (rich.pdf, layered.pdf, signed.pdf, cond.xlsx).
python3 holds_probe.py <dev base> <data root> <out> <engine>      (Web Test chat; test tooling only)"""
import sys, time, os
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from playwright.sync_api import sync_playwright
B, ROOT, OUT, eng = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4]; P = "/tmp/p33/"
def check(n, ok, d=""): print(("PASS " if ok else "FAIL ") + f"[{eng}] {n}" + (f" — {d}" if d != "" else ""), flush=True)
def up(pg, f, sel=".rpage"):
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(f); pg.wait_for_selector(sel, timeout=60000); pg.wait_for_timeout(1500)
def files_of(who_prefix):
    W = os.path.join(ROOT, "workers"); n = 0
    for w in (os.listdir(W) if os.path.isdir(W) else []):
        for _, _, fs in os.walk(os.path.join(W, w)): n += sum(1 for f in fs if f.lower().endswith((".pdf", ".xlsx")))
    return n
with sync_playwright() as p:
    b = getattr(p, eng).launch(); c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    who = f"holds-{eng}-{int(time.time()) % 100000}"; sign_in_as(c, B, who); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:120]) if "WebSocket is not in the OPEN state" not in str(e) else None)  # Firefox, as the page leaves for /signout
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload")
    # --- redaction held
    up(pg, "/tmp/corpus/text-13.pdf"); pg.mouse.move(700, 450)
    pg.locator("text=Protect").first.click(); pg.wait_for_timeout(900); pg.mouse.move(700, 450)
    held = pg.locator("button.rb[aria-label='Redaction']"); box = pg.locator("button.rb[aria-label='Redact box']")
    tip = (held.first.get_attribute("title") or "") if held.count() else ""
    check("Protect shows Redaction greyed with when it comes back, and no Redact box", held.count() == 1 and not held.first.is_enabled() and "comes back with the next update" in tip and box.count() == 0, (held.count(), tip[:80], box.count()))
    pg.keyboard.press("r"); pg.wait_for_timeout(800)
    check("the R key does not start redaction", "/redact" not in pg.url and pg.locator(".rd-held, .redact-root").count() == 0, pg.url)
    pg.goto(B + "/redact"); pg.wait_for_timeout(2500); t = pg.inner_text("body")
    check("going straight to /redact shows only that redaction comes back, with no tool", "Redaction comes back with the next update" in t and pg.locator(".rd-held").count() == 1 and pg.locator("button:has-text('Apply'), button:has-text('Redact')").count() == 0, t[:120].replace("\n", " | "))
    pg.screenshot(path=f"{OUT}/redact-held-{eng}.png")
    pg.locator("button.rd-empty-btn").click(); pg.wait_for_timeout(1500)
    check("Back to the document returns to the open file", "/reader" in pg.url and pg.locator(".rpage").count() > 0, pg.url)
    # --- signatures: no verdict
    up(pg, P + "signed.pdf"); pg.wait_for_timeout(2500)
    body = pg.inner_text("body"); status = [l for l in body.split("\n") if "signature" in l.lower()][:4]
    verdict = [w for w in ("Valid", "valid signature", "Trusted", "trusted", "Not valid", "has been changed", "Changed since") if w in body]
    check("a signed PDF says what the signature states and gives no verdict", any("not checked in this version" in l for l in status) and not verdict, (status, verdict))
    det = pg.locator("button:has-text('Details'), a:has-text('Details')")
    if det.count(): det.first.click(); pg.wait_for_timeout(1500)
    card = pg.locator("section.chvd-card[aria-label='Signatures']"); ct = card.inner_text() if card.count() else ""
    check("the Signatures card names signer, reason and place, and no verdict", card.count() == 1 and "Test Signer" in ct and "Web Test check" in ct and "Pune" in ct and not any(w in ct for w in ("Valid", "Trusted", "Not valid")), ct.replace("\n", " | ")[:220])
    pg.screenshot(path=f"{OUT}/signature-noverdict-{eng}.png")
    # --- page operations ask first; Cancel writes nothing
    pg.goto(B + "/merge"); pg.wait_for_selector("text=Add files", timeout=30000)
    with pg.expect_file_chooser() as fc: pg.click("text=Add files")
    fc.value.set_files([P + "rich.pdf", P + "layered.pdf"]); pg.wait_for_selector("button.tbtn-go:not([disabled])", timeout=30000)
    dls = []; pg.on("download", lambda d: dls.append(d))
    pg.click("button.tbtn-go"); pg.wait_for_selector(".closeq", timeout=10000); q = pg.locator(".closeq").first.inner_text()
    print(f"INFO [{eng}] merge card: {q.replace(chr(10), ' | ')[:400]}")
    check("Merge asks first, naming rich.pdf's bookmarks, page labels and language", "rich.pdf" in q and "bookmarks" in q and "page labels" in q and "language" in q, q[:200].replace("\n", " | "))
    check("... and has a line for layered.pdf's layers", "layered.pdf" in q and "layer" in q.lower(), "")
    pg.locator(".closeq button:text-is('Cancel')").click(); pg.wait_for_timeout(3000)
    check("Cancel on the card writes nothing (no download)", len(dls) == 0 and pg.locator(".closeq").count() == 0, len(dls))
    with pg.expect_download(timeout=60000) as dl:
        pg.click("button.tbtn-go"); pg.wait_for_selector("button.fc-btn.primary:text-is('Continue')", timeout=10000); pg.click("button.fc-btn.primary:text-is('Continue')")
    sv = f"{OUT}/merged-{eng}.pdf"; dl.value.save_as(sv)
    from pypdf import PdfReader
    check("Continue writes the merged file", len(PdfReader(sv).pages) == 2, os.path.getsize(sv))
    pg.goto(B + "/split")
    with pg.expect_file_chooser() as fc: pg.click("text=Choose file")
    fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector("button.tbtn-go:not([disabled])", timeout=30000)
    n0 = len(dls); pg.click("button.tbtn-go"); pg.wait_for_timeout(4000); asked = pg.locator(".closeq").count()
    print(f"INFO [{eng}] Split of a file with nothing to lose: card shown {asked}, downloads {len(dls) - n0}")
    if asked: pg.locator(".closeq button:text-is('Cancel')").click()
    # --- Excel conditional colours
    pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload"); up(pg, P + "cond.xlsx", ".xv-cell")
    cols = pg.evaluate("""() => [...document.querySelectorAll('.xv-cell')].slice(0, 60).map(c => [c.textContent.trim(), getComputedStyle(c).backgroundColor])""")
    red = [x for x in cols if x[0] in ("60", "70", "80", "90", "100") and ("255, 0, 0" in x[1])]
    own = [x for x in cols if x[0] == "own fill"]
    note = pg.locator(".xv-condheld"); nt = (note.inner_text() + " " + (note.get_attribute("title") or "")) if note.count() else ""
    check("Excel: rule colours are not drawn, values are", not red and any(x[0] == "100" for x in cols), red[:3])
    check("Excel: the cell's own fill is still drawn", own and "255, 255, 0" in own[0][1], own[:1])
    check("Excel: the sheet says its rule colours come back", note.count() == 1 and "not drawn" in nt, nt[:160])
    pg.screenshot(path=f"{OUT}/cond-held-{eng}.png")
    # --- Sign out with nothing unsaved: no card
    def sign_out(): pg.click("button.acct-chip"); pg.click("button.acct-out")
    sign_out(); pg.wait_for_timeout(1500); asked = pg.locator(".closeq").count()
    try: pg.wait_for_url("**/signed-out", timeout=20000); out = True
    except Exception: out = False
    check("Sign out with nothing unsaved: no card, signed out", asked == 0 and out, (asked, pg.url))
    # --- Sign out, Discard
    sign_in_as(c, B, who + "-d"); pg.goto(B + "/"); pg.wait_for_selector("nav.leftbar >> text=Upload"); up(pg, "/tmp/corpus/text-13.pdf")
    pg.click("nav.leftbar >> text=Mark"); pg.click("button.rb[aria-label='Rectangle']"); pg.mouse.move(5, 400)
    bx = pg.locator(".rpage").first.bounding_box(); x, y = bx["x"] + 200, bx["y"] + 200
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 100, y + 60, steps=5); pg.mouse.up(); pg.wait_for_selector(".mk-shape.rect", timeout=10000)
    n_before = files_of(who); dl_before = len(dls); dlg = []; pg.on("dialog", lambda d: (dlg.append(d.type), d.accept()))
    sign_out(); pg.wait_for_selector(".closeq", timeout=10000); btn = [t.strip() for t in pg.locator(".closeq button").all_inner_texts()]
    pg.locator(".closeq button:text-is('Discard')").click()
    try: pg.wait_for_url("**/signed-out", timeout=20000); out = True
    except Exception: out = False
    pg.wait_for_timeout(4000)
    check("Sign out with a mark → Discard: signed out, no download, no browser question", btn == ["Save as…", "Discard", "Cancel"] and out and len(dls) == dl_before and "beforeunload" not in dlg, (btn, pg.url, len(dls) - dl_before, dlg))
    check("... and the person's files are gone", files_of(who) < n_before, (n_before, files_of(who)))
    check("no page errors", not errs, errs[:3]); b.close()
