"""M-27 reach: other tools that take a position from the zoomed page — move a mark, resize a mark, Redact box.
Works on engines that report zoomed rectangles unzoomed (WebKit <= 18.4) by correcting its own measurements.
python3 zoom_tools.py <dev base> <out> <engine>      (Web Test chat; test tooling only)"""
import io, os, subprocess, sys
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from PIL import Image
from playwright.sync_api import sync_playwright
base, out, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True); res = []
def check(name, ok, detail=""):
    ok = bool(ok); res.append(ok); print(("PASS " if ok else "FAIL ") + f"[{tag}] {name}" + (f" — {str(detail)[:230]}" if detail != "" else ""), flush=True)
UNZ = """() => { const o = document.createElement('div'); o.style.cssText = 'position:fixed;left:0;top:0;zoom:2;visibility:hidden';
  o.innerHTML = '<div style="width:100px;height:50px"></div>'; document.body.appendChild(o);
  const w = o.firstChild.getBoundingClientRect().width; o.remove(); return w < 150; }"""
RECT = """([sel, unz]) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  const z = parseFloat(document.querySelector('[style*="--rpage-zoom"]').style.getPropertyValue('--rpage-zoom')), k = unz ? z : 1;
  return [r.left * k, r.top * k, r.width * k, r.height * k, z]; }"""
def saved_bbox(pdf):
    subprocess.run(["pdftoppm", "-r", "72", "-f", "1", "-l", "1", "-png", pdf, pdf[:-4]], check=True)
    png = [f for f in os.listdir(os.path.dirname(pdf)) if f.startswith(os.path.basename(pdf)[:-4] + "-") and f.endswith(".png")][0]
    im = Image.open(os.path.join(os.path.dirname(pdf), png)); bb = im.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox()
    return [bb[0] / im.width, bb[1] / im.height, bb[2] / im.width, bb[3] / im.height] if bb else None

with sync_playwright() as pw:
    b = getattr(pw, engine).launch(); tag = f"{engine} {b.version}"
    ctx = b.new_context(viewport={"width": 1440, "height": 716}, accept_downloads=True); sign_in_as(ctx, base, "zt-" + engine)
    def open_doc(f, key):
        pg = ctx.new_page(); pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar")
        with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
        fc.value.set_files(f); pg.wait_for_selector(".rpage svg, .rpage", timeout=60000); pg.wait_for_timeout(1200)
        pg.locator("body").press(key); pg.wait_for_timeout(600)
        if key == "2": pg.click("button[title='Fit page']")
        else:
            pg.mouse.move(330, 20); pg.wait_for_timeout(400); pg.click("button[aria-label='Fit page']"); pg.wait_for_timeout(400)
            pg.click("button[aria-label='Zoom in']"); pg.wait_for_timeout(400)
        pg.mouse.move(330, 20); pg.wait_for_timeout(900)
        return pg
    def close_all(pg):
        try:
            while pg.query_selector("header button[aria-label^='Close']"):
                pg.locator("header button[aria-label^='Close']").first.click(timeout=3000); pg.wait_for_timeout(300)
                for lbl in ("Discard", "Close without saving", "Don't save"):
                    bt = pg.query_selector(f"button:has-text(\"{lbl}\")")
                    if bt: bt.click(); pg.wait_for_timeout(300)
        except Exception: pass
        pg.close()
    # ---- move and resize a rectangle at ~54 % ----
    pg = open_doc("/tmp/m27/plain.pdf", "2"); unz = pg.evaluate(UNZ)
    L, T, W, H, z = pg.evaluate(RECT, [".mk-layer[data-page='0']", unz])
    pg.click("button[aria-label='Rectangle']"); pg.mouse.move(330, 20); pg.wait_for_timeout(400)
    x0, y0, x1, y1 = L + 0.2 * W, T + 0.2 * H, L + 0.5 * W, T + 0.4 * H
    pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x1, y1, steps=8); pg.mouse.up(); pg.wait_for_timeout(700)
    r0 = pg.evaluate(RECT, [".mk-layer[data-page='0'] .mk-shape.rect:not(.draft)", unz])
    check(f"zoom {z:.2f}: drawn under the pointer", r0 and abs(r0[0] - x0) < 2 and abs(r0[1] - y0) < 2, [round(v, 1) for v in r0[:4]] if r0 else None)
    # move: drag the body by (+70, +90)
    pg.mouse.move(r0[0] + r0[2] / 2, r0[1] + r0[3] / 2); pg.mouse.down(); pg.mouse.move(r0[0] + r0[2] / 2 + 70, r0[1] + r0[3] / 2 + 90, steps=8); pg.mouse.up(); pg.wait_for_timeout(600)
    r1 = pg.evaluate(RECT, [".mk-layer[data-page='0'] .mk-shape.rect:not(.draft)", unz])
    check("move by (+70, +90) px moves the shape by that much", abs((r1[0] - r0[0]) - 70) < 2 and abs((r1[1] - r0[1]) - 90) < 2, [round(r1[0] - r0[0], 1), round(r1[1] - r0[1], 1)])
    # resize: drag the resize handle by (+40, +30)
    h = pg.evaluate(RECT, [".mk-layer[data-page='0'] .mk-shape.rect:not(.draft) .mk-th.resize", unz])
    if h:
        pg.mouse.move(h[0] + h[2] / 2, h[1] + h[3] / 2); pg.mouse.down(); pg.mouse.move(h[0] + h[2] / 2 + 40, h[1] + h[3] / 2 + 30, steps=8); pg.mouse.up(); pg.wait_for_timeout(600)
        r2 = pg.evaluate(RECT, [".mk-layer[data-page='0'] .mk-shape.rect:not(.draft)", unz])
        check("resize by (+40, +30) px grows the shape by that much", abs((r2[2] - r1[2]) - 40) < 2 and abs((r2[3] - r1[3]) - 30) < 2, [round(r2[2] - r1[2], 1), round(r2[3] - r1[3], 1)])
    else:
        r2 = r1; check("resize handle found", False)
    pg.keyboard.press("Escape"); pg.mouse.move(330, 20); pg.wait_for_timeout(300)
    with pg.expect_download(timeout=30000) as d: pg.click("button[aria-label='Save as new PDF']")
    pdf = os.path.join(out, f"moved-{engine}.pdf"); d.value.save_as(pdf); sv = saved_bbox(pdf)
    exp = [(r2[0] - L) / W, (r2[1] - T) / H, (r2[0] + r2[2] - L) / W, (r2[1] + r2[3] - T) / H]
    check("saved where it was left after move and resize (within 0.6 % of the page)", sv and all(abs(a - e) < 0.006 for a, e in zip(sv, exp)), ([round(v, 3) for v in exp], [round(v, 3) for v in sv] if sv else None))
    close_all(pg)
    # ---- Redact box at ~54 % ----
    pg = open_doc("/tmp/corpus/text-3.pdf", "4"); unz = pg.evaluate(UNZ)
    pg.click("button[aria-label='Redact box']"); pg.mouse.move(330, 20); pg.wait_for_url("**/redact"); pg.wait_for_timeout(900)
    for _ in range(2):
        pg.evaluate("[...document.querySelectorAll(\"button[aria-label='Zoom out'], button[title='Zoom out']\")].filter(b => b.offsetParent)[0].click()"); pg.wait_for_timeout(350)
    pg.mouse.move(330, 20); pg.wait_for_timeout(600)
    t = pg.evaluate("""(unz) => { const z = parseFloat(document.querySelector('[style*="--rpage-zoom"]').style.getPropertyValue('--rpage-zoom')), k = unz ? z : 1;
        const el = [...document.querySelectorAll('svg text, svg tspan')].find(e => e.textContent.includes('Line 10:'));
        const r = el.getBoundingClientRect(); return [r.left * k, r.top * k, r.width * k, r.height * k, z]; }""", unz)
    pg.mouse.move(t[0] - 3, t[1] - 1); pg.mouse.down(); pg.mouse.move(t[0] + t[2] + 3, t[1] + t[3] + 1, steps=8); pg.mouse.up(); pg.wait_for_timeout(700)
    pg.screenshot(path=os.path.join(out, f"redact-{engine}.png")); pg.mouse.move(330, 20)
    print("   redact page state:", pg.evaluate("""() => ({ boxes: document.querySelectorAll('.mk-box, [class*=rd-box], .rd-mark').length, save: [...document.querySelectorAll("button[aria-label='Save redacted copy']")].map(b => [b.disabled, !!b.offsetParent]), text: (document.body.innerText.match(/\\d+ (box|area|region|redaction)[a-z]*/gi) || []).slice(0, 3) })"""), "line10 true rect", [round(v) for v in t])
    with pg.expect_download(timeout=30000) as d: pg.click("button[aria-label='Save redacted copy']")
    pdf = os.path.join(out, f"redacted-{engine}.pdf"); d.value.save_as(pdf)
    txt = subprocess.run(["pdftotext", "-l", "1", pdf, "-"], capture_output=True, text=True).stdout
    gone = [n for n in range(1, 41) if f"Line {n}:" not in txt]
    check(f"zoom {t[4]:.2f}: Redact box over line 10 removes line 10 and nothing far from it", 10 in gone and all(abs(n - 10) <= 1 for n in gone), gone)
    close_all(pg); b.close()
print(f"{sum(res)}/{len(res)} pass")
