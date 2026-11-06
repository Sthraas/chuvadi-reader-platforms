#!/usr/bin/env python3
# TESTING ONLY. Pixel comparison of "before" and "after" screenshots (same file names in two
# folders). Masks nothing: the preview's status-bar clock is the only live text and the desktop
# shots are taken within the same minute… so a clock difference is reported separately.
import sys, glob, os
from PIL import Image, ImageChops
before, after = sys.argv[1], sys.argv[2]
ok = True
for a in sorted(glob.glob(os.path.join(after, "*.png"))):
    b = os.path.join(before, os.path.basename(a))
    if not os.path.exists(b):
        print("missing before:", os.path.basename(a)); ok = False; continue
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        print("size differs:", os.path.basename(a)); ok = False; continue
    diff = ImageChops.difference(ia, ib)
    box = diff.getbbox()
    if box is None:
        print("IDENTICAL", os.path.basename(a)); continue
    # The live clock (HH:MM:SS) sits at the far right of the status bar.
    w, h = ia.size
    clock = box[0] >= w - 110 and box[1] >= h - 30
    print(("CLOCK ONLY " if clock else "DIFFERS ") + os.path.basename(a), box)
    ok = ok and clock
sys.exit(0 if ok else 1)
