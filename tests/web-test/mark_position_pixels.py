"""M-27, measured from pixels only (no DOM geometry): for engines whose getBoundingClientRect is not in
pointer units under CSS zoom (WebKit 17 and earlier). Web Test chat; test tooling only.
python3 mark_position_pixels.py <dev base> <out> <engine>

page box  = the white page in a screenshot; pointer box = where the mouse pressed/released (true client px);
drawn box = pixels that changed between the screenshot before and after the drag;
saved box = non-white pixels of page 1 of the saved PDF (72 dpi), as a fraction of the page."""
import io, json, os, subprocess, sys
sys.path.insert(0, "/home/claude/wt-verify/tests/web-e2e")
from pdfs import sign_in_as
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

base, out, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
DOCS = {"unrotated": "/tmp/m27/plain.pdf", "rot90": "/tmp/m27/rot90.pdf"}
ZOOMS = [("fit", {"unrotated": 900, "rot90": 900}, 0), ("54", {"unrotated": 716, "rot90": 538}, 0),
         ("100", {"unrotated": 671, "rot90": 507}, 2), ("150", {"unrotated": 671, "rot90": 507}, 4)]

def shot(pg): return Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
def page_box(img):
    """The white page: the bounding box of pure-white pixels in the middle band (between the side bars)."""
    w, h = img.size; m = img.crop((230, 50, w - 150, h - 30)).convert("L").point(lambda v: 255 if v >= 254 else 0)
    bb = m.getbbox(); return (bb[0] + 230, bb[1] + 50, bb[2] + 230, bb[3] + 50)

with sync_playwright() as pw:
    b = getattr(pw, engine).launch(); ver = b.version
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); sign_in_as(ctx, base, f"m27px-{engine}")
    for zl, vhs, steps in ZOOMS:
        for dl, doc in DOCS.items():
            for tool in ("Rectangle", "Text"):
                pg = ctx.new_page(); pg.set_viewport_size({"width": 1440, "height": vhs[dl]})
                row = {"engine": f"{engine} {ver}", "zoom": zl, "page": dl, "tool": tool}
                try:
                    pg.goto(base + "/"); pg.wait_for_selector("nav.leftbar")
                    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
                    fc.value.set_files(doc); pg.wait_for_selector(".rpage", timeout=60000); pg.wait_for_timeout(1000)
                    pg.locator("body").press("2"); pg.wait_for_selector(".mk-layer[data-page='0']"); pg.wait_for_timeout(400)
                    pg.click("button[title='Fit page']"); pg.wait_for_timeout(500)
                    for _ in range(steps): pg.click("button[title^='Zoom in']"); pg.wait_for_timeout(250)
                    pg.mouse.move(330, 20); pg.wait_for_timeout(500)
                    pg.click(f"button[aria-label='{tool}']"); pg.mouse.move(330, 20); pg.wait_for_timeout(700)
                    row["zoom_actual"] = round(float(pg.evaluate("document.querySelector('[style*=\"--rpage-zoom\"]').style.getPropertyValue('--rpage-zoom')")), 3)
                    before = shot(pg); X0, Y0, X1, Y1 = page_box(before); row["page_on_screen"] = [X0, Y0, X1 - X0, Y1 - Y0]
                    px0, py0 = X0 + 0.20 * (X1 - X0), Y0 + 0.20 * (Y1 - Y0); px1, py1 = X0 + 0.55 * (X1 - X0), Y0 + 0.50 * (Y1 - Y0)
                    pg.mouse.move(px0, py0); pg.mouse.down(); pg.mouse.move((px0 + px1) / 2, (py0 + py1) / 2, steps=6)
                    pg.mouse.move(px1, py1, steps=6); pg.mouse.up(); pg.wait_for_timeout(700)
                    if tool == "Text": pg.keyboard.type("HHHH"); pg.wait_for_timeout(300)
                    pg.mouse.move(330, 20); pg.wait_for_timeout(500)
                    after = shot(pg); after.save(os.path.join(out, f"{zl}-{dl}-{tool}.png"))
                    diff = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v > 24 else 0)
                    bb = diff.crop((230, 50, after.width - 150, after.height - 30)).getbbox()
                    row["pointer"] = [round(px0), round(py0), round(px1 - px0), round(py1 - py0)]
                    if bb:
                        d = (bb[0] + 230, bb[1] + 50, bb[2] + 230, bb[3] + 50)
                        row["drawn"] = [d[0], d[1], d[2] - d[0], d[3] - d[1]]
                        row["screen_offset_px"] = [round(d[0] - px0), round(d[1] - py0)]
                    else: row["drawn"] = None
                    exp = [(px0 - X0) / (X1 - X0), (py0 - Y0) / (Y1 - Y0), (px1 - X0) / (X1 - X0), (py1 - Y0) / (Y1 - Y0)]
                    row["expected_frac"] = [round(v, 3) for v in exp]
                    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
                    with pg.expect_download(timeout=30000) as dlw: pg.click("button[aria-label='Save as new PDF']")
                    pdf = os.path.join(out, f"{zl}-{dl}-{tool}.pdf"); dlw.value.save_as(pdf)
                    subprocess.run(["pdftoppm", "-r", "72", "-f", "1", "-l", "1", "-png", pdf, pdf[:-4] + "-saved"], check=True)
                    png = [f for f in os.listdir(out) if f.startswith(f"{zl}-{dl}-{tool}-saved")][0]
                    im = Image.open(os.path.join(out, png)); sb = im.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox()
                    if sb:
                        sv = [sb[0] / im.width, sb[1] / im.height, sb[2] / im.width, sb[3] / im.height]
                        row["saved_frac"] = [round(v, 3) for v in sv]
                        row["saved_offset_pct_of_page"] = [round((sv[0] - exp[0]) * 100, 1), round((sv[1] - exp[1]) * 100, 1)]
                    else: row["saved_frac"] = None
                except Exception as e: row["error"] = str(e).splitlines()[0][:160]
                try:
                    while pg.query_selector("header button[aria-label^='Close']"):
                        pg.locator("header button[aria-label^='Close']").first.click(timeout=3000); pg.wait_for_timeout(300)
                        for lbl in ("Discard", "Close without saving", "Don't save"):
                            bt = pg.query_selector(f"button:has-text(\"{lbl}\")")
                            if bt: bt.click(); pg.wait_for_timeout(300)
                except Exception: pass
                print(json.dumps(row), flush=True); pg.close()
    b.close()
