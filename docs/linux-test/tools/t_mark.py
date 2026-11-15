# M-27 check on Linux: does a mark drawn with the mouse land under the pointer, at several zooms, on an unrotated
# page and a /Rotate 90 page? Compares three things with the pointer path: the mark's box in the page (DOM), the
# pixels that changed on screen (screenshot diff), and the annotation saved in the file (pikepdf, PDF points).
# The saved file is read by t_mark_saved.py (system python, pikepdf).
# Usage: t_mark.py <mark-rot.pdf> <outdir> <zoom-out clicks (negative) or zoom-in clicks from Fit page>
import helpers as h, json
from lt_base import *
F, OUT, STEPS = sys.argv[1], sys.argv[2], int(sys.argv[3]); os.makedirs(OUT, exist_ok=True)
a = App(APP, EV + f"/mark-{STEPS}", display=f":{90 + STEPS + 5}"); h.bind(a); a.start_display()
ZL = "var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)&&e.offsetParent); return z?z.innerText:''"
def btn(lab): a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')=='{lab}'&&b.offsetParent); b.click(); return 1"); time.sleep(0.6)
def goto(n): a.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{n}'; b.dispatchEvent(new Event('change')); return 1"); time.sleep(1.5)
def prect(i): return a.js(f"var p=document.querySelector('.rpage-wrap[data-page=\"{i}\"] .rpage'); var r=p.getBoundingClientRect(); return [r.left,r.top,r.width,r.height]")
def marks(i): return a.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{i}\"]'); return [...w.querySelectorAll('.mk-layer .mk-shape, .mk-layer .mk-text, .mk-layer .mk-shape-svg > *')].filter(e=>!/mk-shape-svg/.test(e.getAttribute('class')||'')).map(e=>{{var b=e.getBoundingClientRect(); return [e.tagName+'.'+(e.getAttribute('class')||'').trim().split(/\\s+/)[0],Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height)]}})")
def newest(i, before):
    now = marks(i); new = [m for m in now if m not in before]
    return new[-1] if new else None
def comps(p1, p2, region):
    """Boxes of the separate things that changed on screen inside region (screen px)."""
    x, y, w, hh = [int(v) for v in region]
    r = subprocess.run(["convert", p1, p2, "-compose", "difference", "-composite", "-crop", f"{w}x{hh}+{x}+{y}", "+repage", "-colorspace", "Gray", "-threshold", "4%",
                        "-morphology", "Dilate", "Disk:5", "-define", "connected-components:verbose=true", "-define", "connected-components:area-threshold=150", "-connected-components", "8", "null:"], capture_output=True, text=True).stdout
    out = []
    for m in re.finditer(r"(\d+)x(\d+)\+(\d+)\+(\d+) [\d.,]+ \d+ (?:gray\(255\)|srgb\(255,255,255\)|white)", r):
        out.append([int(m[3]) + x + 5, int(m[4]) + y + 5, int(m[1]) - 10, int(m[2]) - 10])
    return out
def diffbox(p1, p2, region):
    x, y, w, hh = [int(v) for v in region]
    r = subprocess.run(["convert", p1, p2, "-compose", "difference", "-composite", "-crop", f"{w}x{hh}+{x}+{y}", "+repage", "-colorspace", "Gray", "-threshold", "4%", "-format", "%@", "info:"], capture_output=True, text=True).stdout.strip()
    m = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", r)
    return [int(m[3]) + x, int(m[4]) + y, int(m[1]), int(m[2])] if m else None
import re
def disp(i, pr, sx, sy):
    W, H = (595, 842) if i == 0 else (842, 595)
    return [round((sx - pr[0]) / pr[2] * W), round((sy - pr[1]) / pr[3] * H)]
def to_pdf(i, pr, sx, sy):
    fx, fy = (sx - pr[0]) / pr[2], (sy - pr[1]) / pr[3]
    return (fx * 595, (1 - fy) * 842) if i == 0 else (fy * 595, fx * 842)   # page 2 is /Rotate 90
rows = []
try:
    a.launch(); time.sleep(4); a.send("open " + F, timeout=15); time.sleep(4)
    a.click(".lb-mode", 1); time.sleep(1.5); btn("Fit page")
    for _ in range(abs(STEPS)): btn("Zoom in" if STEPS > 0 else "Zoom out")
    if os.environ.get("WHEEL"):   # Ctrl+scroll over the page instead of the buttons: WHEEL=+4 or -3 notches
        n = int(os.environ["WHEEL"]); pr0 = prect(0); h.focus_main(); a.xdo("mousemove", str(int(pr0[0] + pr0[2] / 2)), str(int(pr0[1] + 300)))
        a.xdo("keydown", "ctrl")
        for _ in range(abs(n)): a.xdo("click", "4" if n > 0 else "5"); time.sleep(0.25)
        a.xdo("keyup", "ctrl"); time.sleep(1)
    zoom = a.js(ZL); desk = a.rect(".rdesk")
    for i in (0, 1):
        goto(i + 1); pr = prect(i)
        vx0, vy0 = max(pr[0], desk[0]) + 12, max(pr[1], desk[1]) + 12
        vx1, vy1 = min(pr[0] + pr[2], desk[0] + desk[2] - 150) - 12, min(pr[1] + pr[3], desk[1] + desk[3]) - 12
        P = lambda u, v: (int(vx0 + (vx1 - vx0) * u), int(vy0 + (vy1 - vy0) * v))
        # Rectangle: drag A -> B
        (ax, ay), (bx, by) = P(0.15, 0.12), P(0.45, 0.32)
        h.click_label(".srail", "Rectangle"); h.focus_main(); n0 = marks(i); park = (str(int(desk[0] + 5)), str(int(desk[1] + desk[3] - 5)))
        a.xdo("mousemove", *park); time.sleep(0.4); s0 = a.shot(f"m{i}-0")
        a.xdo("mousemove", str(ax), str(ay)); a.xdo("mousedown", "1")
        for k in range(1, 11): a.xdo("mousemove", str(int(ax + (bx - ax) * k / 10)), str(int(ay + (by - ay) * k / 10))); time.sleep(0.04)
        a.xdo("mouseup", "1"); time.sleep(0.8); a.xdo("mousemove", str(int(desk[0] + 5)), str(int(desk[1] + desk[3] - 5))); time.sleep(0.3)
        dom = newest(i, n0)
        rows.append({"zoom": zoom, "page": i + 1, "tool": "Rectangle", "pointer": [ax, ay, bx - ax, by - ay], "dom": dom, "page_pts": disp(i, pr, ax, ay) + disp(i, pr, bx, by)})
        # Text: click at C, type
        cx, cy = P(0.2, 0.55); h.click_label(".srail", "Text"); h.focus_main(); n0 = marks(i)
        a.xdo("mousemove", str(cx), str(cy)); a.xdo("click", "1"); time.sleep(0.8); a.type("MARK"); time.sleep(0.4)
        dom = newest(i, n0)
        rows.append({"zoom": zoom, "page": i + 1, "tool": "Text", "pointer": [cx, cy], "dom": dom, "page_pts": disp(i, pr, cx, cy)})
        # Draw: a diagonal stroke D -> E
        (dx, dy), (ex, ey) = P(0.55, 0.6), P(0.8, 0.85); h.click_label(".srail", "Draw"); h.focus_main(); n0 = marks(i)
        a.xdo("mousemove", str(dx), str(dy)); a.xdo("mousedown", "1")
        for k in range(1, 11): a.xdo("mousemove", str(int(dx + (ex - dx) * k / 10)), str(int(dy + (ey - dy) * k / 10))); time.sleep(0.04)
        a.xdo("mouseup", "1"); time.sleep(0.8); dom = newest(i, n0)
        rows.append({"zoom": zoom, "page": i + 1, "tool": "Draw", "pointer": [dx, dy, ex - dx, ey - dy], "dom": dom, "page_pts": disp(i, pr, dx, dy) + disp(i, pr, ex, ey)})
        a.key("Escape"); a.xdo("mousemove", *park); a.xdo("click", "1"); time.sleep(0.6); s1 = a.shot(f"m{i}-1")
        print("SCREEN", json.dumps({"zoom": zoom, "page": i + 1, "changed": sorted(comps(s0, s1, [vx0 - 12, vy0 - 12, vx1 - vx0 + 24, vy1 - vy0 + 24]))}), flush=True)
    for r in rows: print("MARK", json.dumps(r), flush=True)
    out = os.path.join(OUT, f"marked-{zoom.strip('%')}.pdf")
    if os.path.exists(out): os.remove(out)
    h.click_label(".srail", "Save as new PDF"); h.file_dialog("Save", out)
    a.wait(lambda: os.path.exists(out) and os.path.getsize(out) > 0, 20, "saved"); time.sleep(1)
    print("OUTFILE", out, flush=True)
finally: a.stop()
