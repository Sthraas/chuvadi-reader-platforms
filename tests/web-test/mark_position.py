"""M-27 check: does a mark drawn with the mouse land under the pointer, on screen and in the saved PDF?
python3 mark_position.py <dev base> <out> <engine> [<engine>...]      (Web Test chat; test tooling only)

For each engine x zoom (Fit, ~54 %, ~100 %, ~150 %) x page (unrotated, /Rotate 90) x tool (Rectangle, Text):
  pointer box  = where the mouse was pressed and released (client px)
  drawn box    = the shape's element on screen (getBoundingClientRect, client px), checked against a screenshot
  saved box    = the non-white pixels of page 1 of the saved PDF (pdftoppm, 72 dpi), as a fraction of the page
  expected     = pointer box as a fraction of the page on screen
"""
import io, json, os, subprocess, sys
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from PIL import Image
from playwright.sync_api import sync_playwright

base, out, engines = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
DOCS = {"unrotated": "/tmp/m27/plain.pdf", "rot90": "/tmp/m27/rot90.pdf"}
# (label, viewport height, how to get there)
ZOOMS = [("fit", {"unrotated": 900, "rot90": 900}, 0), ("54", {"unrotated": 716, "rot90": 538}, 0), ("100", {"unrotated": 671, "rot90": 507}, 2), ("150", {"unrotated": 671, "rot90": 507}, 4)]
GEOM = """() => { const l = document.querySelector('.mk-layer[data-page="0"]').getBoundingClientRect();
  const d = document.querySelector('[style*="--rpage-zoom"]'); const dr = d.getBoundingClientRect();
  return { layer: [l.left, l.top, l.width, l.height], desk: [dr.left, dr.top, dr.right, dr.bottom],
           zoom: parseFloat(d.style.getPropertyValue('--rpage-zoom')), vw: innerWidth, vh: innerHeight }; }"""
rows = []

def nonwhite_bbox(img, thr=235):
    g = img.convert("L").point(lambda v: 255 if v < thr else 0); return g.getbbox()

def run(pw, engine):
    b = getattr(pw, engine).launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    sign_in_as(ctx, base, f"m27-{engine}")
    for zl, vhs, steps in ZOOMS:
        for dl, doc in DOCS.items():
            vh = vhs[dl]
            for tool in ("Rectangle", "Text"):
                pg = ctx.new_page(); pg.set_viewport_size({"width": 1440, "height": vh}); row = {"engine": engine, "zoom": zl, "page": dl, "tool": tool}
                try:
                    pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar")
                    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
                    fc.value.set_files(doc); pg.wait_for_selector(".rpage", timeout=60000); pg.wait_for_timeout(1000)
                    pg.locator("body").press("2"); pg.wait_for_selector(".mk-layer[data-page='0']"); pg.wait_for_timeout(400)
                    pg.click("button[title='Fit page']"); pg.wait_for_timeout(500)
                    for _ in range(steps): pg.click("button[title^='Zoom in']"); pg.wait_for_timeout(250)
                    pg.wait_for_timeout(600)
                    pg.mouse.move(700, 300); pg.wait_for_timeout(600)
                    g = pg.evaluate(GEOM); L, T, W, H = g["layer"]; row["zoom_actual"] = round(g["zoom"], 3)
                    # the part of the page that is on screen
                    vx0, vy0 = max(L, g["desk"][0], 0) + 8, max(T, g["desk"][1], 0) + 8
                    vx1, vy1 = min(L + W, g["desk"][2], g["vw"]) - 8, min(T + H, g["desk"][3], g["vh"]) - 8
                    px0, py0 = vx0 + 0.20 * (vx1 - vx0), vy0 + 0.20 * (vy1 - vy0)
                    px1, py1 = vx0 + 0.55 * (vx1 - vx0), vy0 + 0.50 * (vy1 - vy0)
                    pg.mouse.move(700, 300); pg.wait_for_timeout(500)
                    pg.click(f"button[aria-label='{tool}']"); pg.mouse.move(700, 300); pg.wait_for_timeout(500)
                    pg.mouse.move(px0, py0); pg.mouse.down(); pg.mouse.move((px0 + px1) / 2, (py0 + py1) / 2, steps=6)
                    pg.mouse.move(px1, py1, steps=6); pg.mouse.up(); pg.wait_for_timeout(700)
                    if tool == "Text":
                        pg.keyboard.type("HHHH"); pg.wait_for_timeout(300)
                    sel = ".mk-shape.rect:not(.draft)" if tool == "Rectangle" else ".mk-text:not(.draft)"
                    d = pg.evaluate(f"() => {{ const e = document.querySelector('.mk-layer[data-page=\"0\"] {sel}'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }}")
                    g2 = pg.evaluate(GEOM); L, T, W, H = g2["layer"]
                    row["pointer"] = [round(px0), round(py0), round(px1 - px0), round(py1 - py0)]
                    row["drawn"] = [round(v) for v in d] if d else None
                    if d: row["screen_offset_px"] = [round(d[0] - px0, 1), round(d[1] - py0, 1)]
                    if d: row["screen_size_diff_px"] = [round(d[2] - (px1 - px0), 1), round(d[3] - (py1 - py0), 1)]
                    exp = [(px0 - L) / W, (py0 - T) / H, (px1 - L) / W, (py1 - T) / H]
                    row["expected_frac"] = [round(v, 3) for v in exp]
                    shot = Image.open(io.BytesIO(pg.screenshot()))
                    if tool == "Rectangle" and d:      # screenshot truth: stroke pixels along the pointer box's left edge?
                        crop = shot.crop((int(px0) - 6, int(py0) - 6, int(px1) + 6, int(py1) + 6)).convert("RGB")
                        page_bg = crop.getpixel((crop.width // 2, crop.height // 2))
                        edge = [crop.getpixel((x, crop.height // 2)) for x in range(0, 12)]
                        row["stroke_at_pointer_edge"] = any(sum(abs(a - b_) for a, b_ in zip(px, page_bg)) > 60 for px in edge)
                    shot.save(os.path.join(out, f"{engine}-{zl}-{dl}-{tool}.png"))
                    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
                    with pg.expect_download(timeout=30000) as dlw: pg.click("button[aria-label='Save as new PDF']")
                    pdf = os.path.join(out, f"{engine}-{zl}-{dl}-{tool}.pdf"); dlw.value.save_as(pdf)
                    subprocess.run(["pdftoppm", "-r", "72", "-f", "1", "-l", "1", "-png", pdf, pdf[:-4]], check=True)
                    png = [f for f in os.listdir(out) if f.startswith(os.path.basename(pdf)[:-4] + "-") and f.endswith(".png")][0]
                    im = Image.open(os.path.join(out, png)); bb = nonwhite_bbox(im)
                    if bb:
                        sv = [bb[0] / im.width, bb[1] / im.height, bb[2] / im.width, bb[3] / im.height]
                        row["saved_frac"] = [round(v, 3) for v in sv]
                        row["saved_offset_pct_of_page"] = [round((sv[0] - exp[0]) * 100, 1), round((sv[1] - exp[1]) * 100, 1)]
                        if tool == "Rectangle": row["saved_size_diff_pct"] = [round(((sv[2] - sv[0]) - (exp[2] - exp[0])) * 100, 1), round(((sv[3] - sv[1]) - (exp[3] - exp[1])) * 100, 1)]
                    else: row["saved_frac"] = None
                except Exception as e:
                    row["error"] = str(e).splitlines()[0][:160]
                try:
                    while pg.query_selector("header button[aria-label^='Close']"):
                        pg.locator("header button[aria-label^='Close']").first.click(timeout=3000); pg.wait_for_timeout(300)
                        for lbl in ("Discard", "Close without saving", "Don't save"):
                            bt = pg.query_selector(f"button:has-text(\"{lbl}\")")
                            if bt: bt.click(); pg.wait_for_timeout(300)
                except Exception: pass
                rows.append(row); print(json.dumps(row), flush=True); pg.close()
    b.close()

with sync_playwright() as pw:
    for e in engines: run(pw, e)
json.dump(rows, open(os.path.join(out, "mark_position.json"), "w"), indent=1)
