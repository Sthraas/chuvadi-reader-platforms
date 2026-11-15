# Reads what t_mark.py saved: every annotation's type and /Rect, and where new ink landed on each page (PDF points).
# Usage: t_mark_saved.py <original.pdf> <marked.pdf>
import sys, json, subprocess, pikepdf, tempfile, os
orig, out = sys.argv[1], sys.argv[2]; pdf = pikepdf.open(out)
for n, pg in enumerate(pdf.pages):
    for an in pg.get("/Annots", []):
        print("SAVED", json.dumps({"page": n + 1, "subtype": str(an.get("/Subtype")), "rect": [round(float(v)) for v in an.get("/Rect", [])]}))
    print("SAVEDPAGE", n + 1, "rotate", int(pg.get("/Rotate", 0)), "annots", len(pg.get("/Annots", [])))
d = tempfile.mkdtemp()
for tag, f in (("o", orig), ("m", out)): subprocess.run(["pdftoppm", "-r", "72", "-png", f, os.path.join(d, tag)], check=True)
import re
for n in range(len(pdf.pages)):
    r = subprocess.run(["convert", f"{d}/o-{n+1}.png", f"{d}/m-{n+1}.png", "-compose", "difference", "-composite", "-colorspace", "Gray", "-threshold", "4%", "-morphology", "Dilate", "Disk:4",
                        "-define", "connected-components:verbose=true", "-define", "connected-components:area-threshold=80", "-connected-components", "8", "null:"], capture_output=True, text=True).stdout
    boxes = sorted([int(m[3]) + 4, int(m[4]) + 4, int(m[3]) + int(m[1]) - 4, int(m[4]) + int(m[2]) - 4] for m in re.finditer(r"(\d+)x(\d+)\+(\d+)\+(\d+) [\d.,]+ \d+ (?:gray\(255\)|srgb\(255,255,255\)|white)", r))
    print("INK", json.dumps({"page": n + 1, "new ink, page points as displayed [x0,y0,x1,y1]": boxes}))
