#!/usr/bin/env python3
"""AT-13 repeat: a 6000 × 6000 px image page painted, N cold opens (test tooling only).   at13.py <out> <fixtures> [n=5]"""
import os
import sys
import time

from lib import Cdp, PKG, Results, component, open_with, push_media, screencap, sh

OUT, FX = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 5
R = Results(OUT, "at13")
cdp = Cdp()
uri = push_media(os.path.join(FX, "heavy-image.pdf"), "at13-heavy.pdf")
times = []
for i in range(N):
    sh(f"am force-stop {PKG}")
    time.sleep(1)
    t0 = time.time()
    open_with(uri)
    cdp.close()
    try:
        cdp.connect(60)
        ok = cdp.wait("(() => { const t = (document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t') || {}).textContent || '';"
                      " return t.trim().startsWith('at13-heavy') && document.querySelectorAll('.rpage svg').length > 0; })()", 60, 0.25)
    except Exception as e:
        ok = False
    times.append(round(time.time() - t0, 1) if ok else None)
    if not ok:
        screencap(os.path.join(OUT, f"at13-run{i + 1}-not-painted.png"))
R.check(f"AT-13 heavy image page painted within 60 s, {N} of {N} cold opens", all(times), {"seconds": times})
