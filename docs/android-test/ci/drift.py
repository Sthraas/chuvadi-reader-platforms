#!/usr/bin/env python3
"""Page-box drift (test tooling only): the page box must show the page that is actually on screen,
and stay there — after a cold Open with, after reopening an open file, after Next page, after rotation.

    drift.py <out-dir> <fixtures-dir>
"""
import json
import os
import sys
import time

from lib import Cdp, PKG, Results, component, open_with, portrait_rotation, push_media, screencap, set_rotation, sh

OUT, FX = sys.argv[1], sys.argv[2]
R = Results(OUT, "drift")
cdp = Cdp()

# Page box value, and the page whose box covers the middle of the visible desk (what the person sees).
STATE = r"""(() => { const box = (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim();
  const desk = [...document.querySelectorAll('.rdesk')].find(e => e.getBoundingClientRect().width > 0);
  if (!desk) return {box, shown: null};
  const d = desk.getBoundingClientRect(); const mid = d.top + d.height / 2; let shown = null;
  [...document.querySelectorAll('.rpage-wrap')].forEach((w, i) => { const r = w.getBoundingClientRect(); if (r.top <= mid && r.bottom >= mid && r.width > 0) shown = i + 1; });
  return {box, boxPage: parseInt(box, 10) || null, shown, rendered: document.querySelectorAll('.rpage svg').length,
          tab: ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {}).textContent?.trim()}; })()"""


def watch(seconds=6, every=0.5):
    out = []
    end = time.time() + seconds
    while time.time() < end:
        try:
            out.append(cdp.js(STATE))
        except Exception:
            cdp.close()
        time.sleep(every)
    return out


def steady(samples, want=None):
    """The last two-thirds of the samples: box == page on screen (== want when given), no change."""
    tail = [s for s in samples[len(samples) // 3:] if s and s.get("shown")]
    if not tail:
        return False
    return all(s["boxPage"] == s["shown"] and (want is None or s["shown"] == want) for s in tail)


def brief(samples):
    return [(s.get("boxPage"), s.get("shown")) for s in samples if s]


def wait_doc(name):
    cdp.close()
    cdp.connect(60)
    return cdp.wait(f"(() => {{ const t = ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {{}}).textContent || '';"
                    f" return t.trim().startsWith('{name}') && document.querySelectorAll('.rpage svg').length > 0; }})()", 60)


set_rotation(portrait_rotation())
sh(f"pm clear {PKG}")
uri = push_media(os.path.join(FX, "doc-12p.pdf"), "drift-doc.pdf")
uri2 = push_media(os.path.join(FX, "mixed-landscape.pdf"), "drift-wide.pdf")

# 1. Cold Open with on a fresh install: page 1, and it stays 1.
open_with(uri)
wait_doc("drift-doc")
s = watch(8)
R.check("DR-1 cold Open with: page box says 1, page 1 is on screen, and it stays", steady(s, 1), {"(box, on screen)": brief(s)})

# 2. Go to page 5 the way a person does (tablet: Next page ×4; phone: four swipes); box follows and stays.
import re, subprocess
phone = cdp.js("document.documentElement.getAttribute('data-shell')") == "phone"
def wv():
    from lib import ui_dump
    m = re.search(r'class="android.webkit.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', ui_dump())
    return tuple(map(int, m.groups()))
b = wv(); dpr = cdp.js("devicePixelRatio")
for _ in range(4):
    if phone:
        d = cdp.js("(() => { const r = [...document.querySelectorAll('.rdesk')].find(e => e.getBoundingClientRect().width > 0).getBoundingClientRect(); return [r.left, r.top + r.height / 2, r.width]; })()")
        y = int(b[1] + d[1] * dpr); x1 = int(b[0] + (d[0] + d[2] * 0.85) * dpr); x2 = int(b[0] + (d[0] + d[2] * 0.15) * dpr)
        sh(f"input swipe {x1} {y} {x2} {y} 250")
    else:
        n = cdp.js("(() => { const e = document.querySelector('[aria-label^=\"Next page\"], [title^=\"Next page\"]'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        sh(f"input tap {int(b[0] + n[0] * dpr)} {int(b[1] + n[1] * dpr)}")
    time.sleep(1.2)
s = watch(5)
R.check("DR-2 after moving on four pages: box says 5, page 5 is on screen, and it stays", steady(s, 5), {"(box, on screen)": brief(s)})

# 3. Open a second document: box 1 for the new one.
open_with(uri2)
wait_doc("drift-wide")
s = watch(6)
R.check("DR-3 second document opened: its page box says 1 and stays", steady(s, 1), {"(box, on screen)": brief(s)})

# 4. Reopen the first (already open): its tab comes back at page 5, box agrees.
open_with(uri)
wait_doc("drift-doc")
s = watch(6)
R.check("DR-4 back on the first document: box agrees with the page on screen and stays", steady(s), {"(box, on screen)": brief(s)})

# 4b. AT-16: jump by Find to the one match on page 3 — the box must say 3 with page 3 on screen.
def tap_el(js_expr):
    c = cdp.js("(() => { const e = " + js_expr + "; if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
    if c:
        bb = wv(); dp = cdp.js("devicePixelRatio")
        sh(f"input tap {int(bb[0] + c[0] * dp)} {int(bb[1] + c[1] * dp)}")
        time.sleep(1.2)
    return c
VISQ = "(sel, starts) => [...document.querySelectorAll(sel)].find(e => e.getBoundingClientRect().width > 0 && [e.getAttribute('aria-label'), e.getAttribute('title'), e.innerText].some(t => t && t.trim().toLowerCase().startsWith(starts)))"
if phone:
    tap_el("(" + VISQ + ")('.ph-ib', 'more')")
    f_ = tap_el("(" + VISQ + ")('.ph-sheet *', 'find')")
else:
    f_ = tap_el("(" + VISQ + ")('.rb, .lb-btn, .tb-cmd, button', 'find')")
time.sleep(1)
for ch in "zephyrine":
    sh(f"input text {ch}")
    time.sleep(0.25)
sh("input keyevent KEYCODE_ENTER")
time.sleep(2)
s = watch(6)
screencap(os.path.join(OUT, "after-find.png"))
R.check("DR-7 (AT-16) after Find jumps to the match on page 3: box says 3, page 3 on screen, steady", steady(s, 3), {"find_control": f_, "(box, on screen)": brief(s)})
sh("input keyevent KEYCODE_BACK")
time.sleep(1)
cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
time.sleep(1)

# 5. Rotate: box still agrees.
set_rotation(1 - portrait_rotation())
s = watch(6)
screencap(os.path.join(OUT, "rotated.png"))
R.check("DR-5 after rotation: box agrees with the page on screen and stays", steady(s), {"(box, on screen)": brief(s)})
set_rotation(portrait_rotation())

# 6. Cold restart with the session restored: box agrees once the document is back.
sh(f"am force-stop {PKG}")
sh(f"am start -W -n {component()}")
cdp.close()
cdp.connect(60)
cdp.wait("!!(window.Blazor && Blazor.navigateTo)", 40)
if not cdp.js("location.pathname.startsWith('/reader')"):
    cdp.js("Blazor.navigateTo('/reader')")   # a plain launch opens on Home; the tabs are kept
cdp.wait("document.querySelectorAll('.rpage svg').length > 0", 40)
s = watch(8)
R.check("DR-6 cold restart (session restored): box agrees with the page on screen and stays", steady(s), {"(box, on screen)": brief(s)})
