#!/usr/bin/env python3
"""Design sweep on one emulator: every phone / tablet screen in all five themes, portrait and
landscape, with a touch-target audit and a layout record per screen (test tooling only).

Navigation and theme switching go through the page (DevTools) so the sweep is fast and repeatable;
the real Settings tap and real gestures are covered by the function suite.

    design.py <out-dir> <pdf>
"""
import json
import os
import sys
import time

from lib import Cdp, Results, component, dismiss_system_dialogs, open_with, portrait_rotation, push_media, screencap, set_rotation, sh

OUT, PDF = sys.argv[1], sys.argv[2]
R = Results(OUT, "design")
cdp = Cdp()
THEMES = ["light", "dark", "palm", "indigo", "contrast"]
COMP = component()

AUDIT = r"""(() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'
      && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth; };
  const sel = 'button, a[href], [role=button], [role=tab], [role=menuitem], [role=switch], [role=checkbox], input, select, textarea, [onclick], [tabindex="0"]';
  const z = parseFloat(getComputedStyle(document.documentElement).zoom || '1') || 1;
  const els = [...document.querySelectorAll(sel)].filter(vis);
  const label = e => (e.getAttribute('aria-label') || e.getAttribute('title') || e.innerText || e.value || e.placeholder || e.className || e.tagName).toString().trim().replace(/\s+/g, ' ').slice(0, 60);
  const items = els.map(e => { const r = e.getBoundingClientRect();
     // hit area: the element itself; CSS px are dp on Android (zoom on <html> already in the rect)
     return { label: label(e), tag: e.tagName.toLowerCase(), cls: (e.className || '').toString().slice(0, 60),
              x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 }; });
  return { url: location.pathname, shell: document.documentElement.getAttribute('data-shell'),
     theme: document.documentElement.getAttribute('data-theme'), inner: [innerWidth, innerHeight], dpr: devicePixelRatio,
     htmlZoom: z, scrollW: document.documentElement.scrollWidth, items,
     small: items.filter(i => Math.min(i.w, i.h) < 44), mid: items.filter(i => Math.min(i.w, i.h) >= 44 && Math.min(i.w, i.h) < 48) };
})()"""

CLICK = r"""((labels) => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
  const all = [...document.querySelectorAll('button, a, [role=button], [role=tab], [title], [aria-label]')].filter(vis);
  for (const want of labels) {
    const w = want.toLowerCase();
    const hit = all.filter(e => [e.getAttribute('aria-label'), e.getAttribute('title'), (e.innerText || '')]
        .some(t => t && t.trim().toLowerCase().replace(/\s+/g, ' ').startsWith(w)))
        .sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height)[0];
    if (hit) { hit.click(); return want; }
  }
  return null; })(%s)"""


def js(expr):
    return cdp.js(expr)


def click(*labels):
    return js(CLICK % json.dumps(list(labels)))


def nav(path):
    js(f"(window.Blazor && Blazor.navigateTo) ? Blazor.navigateTo('{path}') : (location.hash='')")
    time.sleep(1.2)


def theme(t):
    js(f"window.chuvadiTheme.set('{t}')")
    time.sleep(0.4)


def snap(name):
    dismiss_system_dialogs()
    p = os.path.join(OUT, name + ".png")
    screencap(p)
    a = js(AUDIT)
    json.dump(a, open(os.path.join(OUT, name + ".layout.json"), "w"), indent=1)
    return a


def reader_state():
    return js("({pages: document.querySelectorAll('.rpage svg').length, url: location.pathname, "
              "shell: document.documentElement.getAttribute('data-shell')})")


# Start clean in Read with the test document.
sh(f"am start -W -n {COMP}")
cdp.connect(60)
cdp.wait("document.getElementById('app') && document.getElementById('app').children.length > 0", 60)
uri = push_media(PDF, "design-doc.pdf")
open_with(uri)
ok = cdp.wait("document.querySelectorAll('.rpage svg').length > 0", 60)
R.check("test document opens for the design sweep", bool(ok), reader_state())

shell = js("document.documentElement.getAttribute('data-shell')")
SCREENS = [
    ("home", lambda: nav("/")),
    ("library", lambda: nav("/library")),
    ("settings", lambda: nav("/settings")),
    ("read", lambda: (nav("/reader"), click("Read"))),
    ("mark", lambda: (nav("/reader"), click("Mark"))),
    ("arrange", lambda: (nav("/reader"), click("Arrange"))),
    ("protect", lambda: (nav("/reader"), click("Protect"))),
]
if shell == "phone":
    SCREENS += [
        ("tabs-sheet", lambda: (nav("/reader"), click("Read"), js("document.querySelector('.ph-t')?.click()"))),
        ("more-sheet", lambda: (nav("/reader"), click("Read"), click("More", "Menu", "⋮"))),
        ("protect-view-sheet", lambda: (nav("/reader"), click("Protect"), click("More", "Menu"), click("View"))),
    ]

summary = []
port = portrait_rotation()
for orient, rot in (("portrait", port), ("landscape", 1 - port)):
    set_rotation(rot)
    for t in THEMES:
        for name, go in SCREENS:
            try:
                js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
                go()
                time.sleep(0.8)
                theme(t)
                a = snap(f"{shell}-{orient}-{t}-{name}")
                summary.append({"screen": name, "orient": orient, "theme": t, "shell": a.get("shell"),
                                "inner": a.get("inner"), "small": len(a["small"]), "mid": len(a["mid"]),
                                "overflow_x": a["scrollW"] - a["inner"][0]})
            except Exception as e:
                summary.append({"screen": name, "orient": orient, "theme": t, "error": str(e)[:200]})
                cdp.close()
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)

# Touch targets (light theme carries the layout; themes don't change sizes).
for row in summary:
    if row.get("theme") == "light" and "error" not in row:
        a = json.load(open(os.path.join(OUT, f"{shell}-{row['orient']}-light-{row['screen']}.layout.json")))
        R.check(f"touch targets ≥ 44 dp: {shell} {row['orient']} {row['screen']}", len(a["small"]) == 0,
                {"under44": a["small"][:12], "between44and48": len(a["mid"])})
        R.check(f"no sideways overflow: {shell} {row['orient']} {row['screen']}", row["overflow_x"] <= 0,
                {"scrollW-inner": row["overflow_x"]})
errors = [r for r in summary if "error" in r]
R.check("every screen reachable in every theme and orientation", not errors, errors[:10])

# System dark mode: the app keeps its own theme; system bars must stay legible over it.
set_rotation(port)
sh("cmd uimode night yes")
time.sleep(2)
for t in ("light", "dark"):
    nav("/reader")
    click("Read")
    theme(t)
    snap(f"{shell}-portrait-{t}-read-systemdark")
sh("cmd uimode night no")
time.sleep(1)
theme("light")
