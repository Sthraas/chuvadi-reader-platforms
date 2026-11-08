#!/usr/bin/env python3
"""Emulator gesture test (CI only). Runs after smoke-test.sh, with the app installed and running.

1. Opens a 6-page test PDF the way another app would: pushed to Downloads, then an
   ACTION_VIEW intent with its MediaStore content:// URI ("Open with").
2. Real touch gestures (touch.py → the emulator's touchscreen), each checked against the page's
   own state (cdp.py), with a screenshot after each:
     swipe            → page counter moves on by one page
     double-tap       → zooms in; a second double-tap returns
     pinch out        → page gets wider (zoomed in)
     Arrange: long-press a page and drag it → page order changes
Writes gestures.json and screenshots to the results folder; exits 1 if any check fails.

    gestures.py <results-dir>
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cdp  # noqa: E402

OUT = sys.argv[1]
PKG = "in.chuvadi.reader"
PDF_NAME = "chuvadi-test.pdf"
os.makedirs(OUT, exist_ok=True)
results = []


def webview_version():
    """The WebView the app runs on (pages are sized with CSS zoom, whose measurement changed in
    Chromium 128: worth knowing per emulator)."""
    out = subprocess.run(["adb", "shell", "dumpsys", "webviewupdate"], capture_output=True, text=True).stdout
    m = re.search(r"Current WebView package \(name, version\): \(([^,]+), ([^)]+)\)", out)
    return {"package": m.group(1), "version": m.group(2)} if m else {"raw": out[:400]}

STATE_JS = r"""
(() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight; };
  const desk = [...document.querySelectorAll('.rdesk')].find(vis) || null;
  // The page on screen: the one under the centre of the desk (not just any page with a box — a
  // neighbour still at its unrendered placeholder size misled the double-tap check on API 35).
  const centre = (() => { const d = [...document.querySelectorAll('.rdesk')].find(vis); if (!d) return null; const r = d.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })();
  const pages = [...document.querySelectorAll('.rpage')].filter(vis);
  const page = (centre && pages.find(e => { const r = e.getBoundingClientRect(); return r.left <= centre[0] && centre[0] <= r.right && r.top <= centre[1] && centre[1] <= r.bottom; }))
    || pages.sort((a, b) => { const ar = a.getBoundingClientRect(), br = b.getBoundingClientRect();
         const area = r => Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0)) * r.width; return area(br) - area(ar); })[0] || null;
  const fitOn = t => [...document.querySelectorAll('[title^="' + t + '"]')].some(e => e.classList.contains('on') || e.classList.contains('active') || e.getAttribute('aria-pressed') === 'true');
  const ctr = (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim();
  const rect = e => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; };
  const cards = [...document.querySelectorAll('[data-bench-id]')].filter(vis);
  const shelfPages = [...document.querySelectorAll('[data-shelf]')];
  return {
    shell: document.documentElement.dataset.shell || null,
    dpr: devicePixelRatio,
    pages: document.querySelectorAll('.rpage').length,
    counter: ctr,
    fit: fitOn('Fit width') ? 'width' : fitOn('Fit page') ? 'page' : 'custom',
    zoomed: !!(desk && desk.classList.contains('zoomed')),
    page: rect(page),
    desk: rect(desk),
    overflowX: desk ? desk.scrollWidth - desk.clientWidth : null,
    order: [...document.querySelectorAll('[data-bench-id]')].map(e => e.dataset.benchId),
    cards: cards.slice(0, 6).map(rect),
    contentW: desk ? desk.scrollWidth : null,
    shelfPages: shelfPages.length,
    shelfVisible: shelfPages.filter(vis).slice(0, 3).map(rect),
    shelfHead: rect([...document.querySelectorAll('.shelf-head')].find(vis) || null),
    deskDrop: rect([...document.querySelectorAll('.desk-drop')].find(vis) || null),
    deskPages: document.querySelectorAll('.desk-drop [data-bench-id]').length,
  };
})()
"""


def adb(*args, check=True):
    return subprocess.run(["adb", *args], check=check, capture_output=True, text=True).stdout


def shot(name):
    with open(os.path.join(OUT, name + ".png"), "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True).stdout)


def dump():
    """UI tree XML, after tapping "Wait" on the emulator's own System UI ANR dialog if it shows."""
    xml = ""
    for _ in range(3):
        xml = subprocess.run(["adb", "exec-out", "uiautomator", "dump", "/dev/tty"], capture_output=True, text=True).stdout
        if not re.search(r"isn.t responding", xml):
            return xml
        m = re.search(r'text="Wait"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if not m:
            return xml
        x1, y1, x2, y2 = map(int, m.groups())
        print("System UI ANR dialog on screen (emulator); tapping Wait")
        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(2)
    return xml


def webview_origin():
    m = re.search(r'class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]', dump())
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def state():
    return cdp.evaluate(STATE_JS)


_origin = None


def to_screen(st, x, y):
    global _origin
    if _origin is None:
        _origin = webview_origin()
    ox, oy = _origin
    return round(ox + x * st["dpr"]), round(oy + y * st["dpr"])


def touch(*args):
    """Runs one gesture; returns False (and prints why) if the touch tool failed. First clears the
    emulator's own "<app> isn't responding" dialog (round 4: Pixel Launcher's sat over the app on
    phone API 35 and took the double-tap); dump() taps its "Wait"."""
    dump()
    r = subprocess.run([sys.executable, os.path.join(HERE, "touch.py"), *map(str, args)],
                       capture_output=True, text=True)
    print("  " + (r.stdout.strip() or f"touch.py {' '.join(map(str, args))}"))
    if r.returncode != 0:
        print("  touch.py failed:\n" + r.stderr.strip())
        check(f"touch input ({args[0]})", False, {"stderr": r.stderr.strip()[-600:]})
        return False
    return True


RECORDER_JS = r"""
(() => {
  if (!window.__chvdEv) {
    window.__chvdEv = [];
    const rec = e => window.__chvdEv.push({ t: Math.round(performance.now()), type: e.type,
      pt: e.pointerType || null, n: e.touches ? e.touches.length : null,
      target: (e.target && e.target.className && String(e.target.className).split(' ')[0]) || (e.target && e.target.tagName) || null });
    for (const k of ['pointerdown', 'pointerup', 'pointercancel', 'touchstart', 'touchend', 'touchcancel', 'wheel', 'click'])
      document.addEventListener(k, rec, { capture: true, passive: true });
    let lastMove = 0;
    document.addEventListener('pointermove', e => { const now = performance.now(); if (now - lastMove > 40) { lastMove = now; rec(e); } }, { capture: true, passive: true });
  }
  window.__chvdEv.length = 0;
  return true;
})()
"""


def events_since_reset():
    """Pointer / touch events the page saw since the last recorder reset (passive listeners only)."""
    try:
        return cdp.evaluate("(window.__chvdEv || []).slice(0, 200)")
    except SystemExit as e:
        return [{"error": str(e)}]


def gesture(name, *args):
    """Records the page's events around one real gesture; saves them as evidence."""
    try:
        cdp.evaluate(RECORDER_JS)
    except SystemExit as e:
        print("  (event recorder unavailable: %s)" % e)
    ok = touch(*args)
    time.sleep(2)
    evs = events_since_reset()
    with open(os.path.join(OUT, f"events-{name}.json"), "w") as f:
        json.dump(evs, f, indent=1)
    kinds = {}
    for e in evs:
        key = e.get("type", "?") + ("/" + e["pt"] if e.get("pt") else "")
        kinds[key] = kinds.get(key, 0) + 1
    print(f"  page saw: {json.dumps(kinds)}")
    return ok


def counter_number(st):
    m = re.search(r"(\d+)", st.get("counter") or "")
    return int(m.group(1)) if m else None


def check(name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " — " + json.dumps(detail))
    if not ok:
        print(f"::error::gesture check failed: {name}")


def wait_for(pred, seconds, what):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        try:
            last = state()
            if pred(last):
                return last
        except SystemExit as e:  # page not reachable yet
            last = {"error": str(e)}
        dump()  # clears a System UI ANR dialog if one appeared
        time.sleep(2)
    print(f"timed out waiting for {what}: {json.dumps(last)[:400]}")
    return last


# Input-device facts, kept as evidence for the touch tool.
with open(os.path.join(OUT, "input-devices.txt"), "w") as f:
    f.write(adb("shell", "id", check=False) + "\n" + adb("shell", "ls -l /dev/input", check=False) + "\n"
            + adb("shell", "getevent -lp", check=False) + "\n" + adb("shell", "wm size", check=False))

# ── 1. Open the test PDF through ACTION_VIEW ───────────────────────────────────
local_pdf = os.path.join(OUT, PDF_NAME)
subprocess.run([sys.executable, os.path.join(HERE, "make-test-pdf.py"), local_pdf, "6"], check=True)
adb("push", local_pdf, f"/sdcard/Download/{PDF_NAME}")
uri = None
for attempt in range(15):
    for coll in ("downloads", "file"):
        rows = adb("shell", "content", "query", "--uri", f"content://media/external/{coll}", "--projection", "_id",
                   "--where", f"\"_display_name='{PDF_NAME}'\"", check=False)
        m = re.search(r"_id=(\d+)", rows)
        if m:
            uri = f"content://media/external/{coll}/{m.group(1)}"
            break
    if uri:
        break
    if attempt == 3:
        adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d", f"file:///sdcard/Download/{PDF_NAME}", check=False)
    time.sleep(2)
print("MediaStore URI:", uri)
check("test PDF is in MediaStore", uri is not None, {"uri": uri})
if uri:
    print(adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", uri, "-t", "application/pdf",
              "-p", PKG, "--grant-read-uri-permission", check=False).strip())
st0 = wait_for(lambda s: s.get("pages", 0) >= 1 and counter_number(s) is not None and s.get("desk"), 90, "the PDF to open")
shot("g1-opened")
check("Open with (ACTION_VIEW content://) opens the PDF in the Reader",
      st0.get("pages", 0) >= 1 and counter_number(st0) == 1, {k: st0.get(k) for k in ("shell", "pages", "counter", "fit")})

WEBVIEW = webview_version()
try:
    WEBVIEW["userAgent"] = cdp.evaluate("navigator.userAgent")
except SystemExit as e:
    WEBVIEW["userAgent"] = str(e)
print(f"WebView: {WEBVIEW.get('package')} {WEBVIEW.get('version')} — {WEBVIEW.get('userAgent')}")

# ── 1b. What is wider than the desk? (phone Fit page overflow, for the Mobile UI chat) ──────────
OVERWIDE_JS = r"""
(() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const desk = [...document.querySelectorAll('.rdesk')].find(vis);
  if (!desk) return { desk: null };
  const dr = desk.getBoundingClientRect();
  const limit = dr.left + desk.clientWidth;          // the desk's visible right edge (inside its scrollbar)
  const cs = e => getComputedStyle(e);
  const describe = e => {
    const c = cs(e), r = e.getBoundingClientRect();
    return { tag: e.tagName.toLowerCase(), id: e.id || null, classes: String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className || ''),
             left: +r.left.toFixed(2), right: +r.right.toFixed(2), width: +r.width.toFixed(2), overBy: +(r.right - limit).toFixed(2),
             computed: { width: c.width, minWidth: c.minWidth, maxWidth: c.maxWidth, boxSizing: c.boxSizing,
                         marginLeft: c.marginLeft, marginRight: c.marginRight, paddingLeft: c.paddingLeft, paddingRight: c.paddingRight,
                         borderLeft: c.borderLeftWidth, borderRight: c.borderRightWidth, transform: c.transform, position: c.position },
             inlineStyle: e.getAttribute('style') };
  };
  // Clipped: an ancestor below the desk hides its overflow, so it can't widen the desk.
  const clipped = e => { for (let x = e.parentElement; x && x !== desk; x = x.parentElement) { if (cs(x).overflowX !== 'visible') return true; } return false; };
  const past = [...desk.querySelectorAll('*')].filter(e => vis(e) && e.getBoundingClientRect().right > limit + 0.5);
  const over = past.filter(e => !clipped(e));
  // The outermost over-wide elements (whose parent is not itself over-wide) are where it starts.
  const roots = over.filter(e => !over.includes(e.parentElement));
  const chain = e => { const out = []; for (let x = e; x && x !== desk; x = x.parentElement) out.unshift(describe(x)); return out; };
  return {
    fit: [...document.querySelectorAll('[title^="Fit page"]')].some(e => e.classList.contains('on')) ? 'page'
       : [...document.querySelectorAll('[title^="Fit width"]')].some(e => e.classList.contains('on')) ? 'width' : 'custom',
    viewport: { innerWidth, dpr: devicePixelRatio },
    desk: { ...describe(desk), clientWidth: desk.clientWidth, scrollWidth: desk.scrollWidth, overflowX: desk.scrollWidth - desk.clientWidth },
    overWideCount: over.length, clippedCount: past.length - over.length,
    starts: roots.slice(0, 5).map(chain),
  };
})()
"""
try:
    ow = cdp.evaluate(OVERWIDE_JS)
except SystemExit as e:
    ow = {"error": str(e)}
with open(os.path.join(OUT, "overwide.json"), "w") as f:
    json.dump(ow, f, indent=1)
if ow.get("desk"):
    print(f"desk overflowX {ow['desk'].get('overflowX')} px (fit {ow.get('fit')}), {ow.get('overWideCount')} element(s) past the "
          f"desk's right edge ({ow.get('clippedCount')} more, clipped inside their page)")
    for ch in ow.get("starts") or []:
        top = ch[-1] if ch else {}   # the over-wide element itself (the chain runs desk → it)
        print(f"  over-wide: <{top.get('tag')} class=\"{top.get('classes')}\"> width {top.get('width')} px, over by {top.get('overBy')} px, "
              f"computed width {top.get('computed', {}).get('width')}, margins {top.get('computed', {}).get('marginLeft')}/{top.get('computed', {}).get('marginRight')}")

# Now the gestures. The emulator's SELinux policy denies the shell user writes to /dev/input even though it is in the
# input group, so touch.py needs a root adbd. google_apis emulator images allow `adb root`; the app
# keeps running while adbd restarts. (Open with stays as the shell user above: a file pushed and an
# intent sent by root don't grant the app read access the way the shell user's do.)
print(adb("root", check=False).strip())
adb("wait-for-device")
for _ in range(20):
    if adb("shell", "id -u", check=False).strip() == "0":
        break
    time.sleep(1)
print("adbd uid:", adb("shell", "id -u", check=False).strip())


if st0.get("desk"):
    d = st0["desk"]
    cx, cy = d["x"] + d["w"] / 2, d["y"] + d["h"] / 2

    # ── 2. Swipe left → next page ─────────────────────────────────────────────
    x1, y1 = to_screen(st0, d["x"] + d["w"] * 0.80, cy)
    x2, y2 = to_screen(st0, d["x"] + d["w"] * 0.20, cy)
    gesture("swipe", "swipe", x1, y1, x2, y2, 250)
    st1 = state()
    shot("g2-swiped")
    check("swipe left moves to the next page", (counter_number(st1) or 0) > (counter_number(st0) or 0),
          {"before": st0.get("counter"), "after": st1.get("counter"), "overflowX": st0.get("overflowX")})

    # ── 3. Double-tap → zoom in; again → back (handout: double-tap = zoom; reader.js owns it) ──
    sx, sy = to_screen(st1, cx, cy)
    gesture("doubletap", "doubletap", sx, sy)
    st2z = state()
    shot("g3-doubletapped")
    gesture("doubletap-back", "doubletap", sx, sy)
    st2 = state()
    shot("g3b-doubletapped-back")
    w0, w1, w2 = [(x.get("page") or {}).get("w") or 0 for x in (st1, st2z, st2)]
    check("double-tap zooms in, a second double-tap returns", w1 > w0 * 1.5 and abs(w2 - w0) <= 2,
          {"pageW": [w0, w1, w2]})

    # ── 4. Pinch out → zoom in ────────────────────────────────────────────────
    st2d = st2.get("desk") or d
    pcx, pcy = to_screen(st2, st2d["x"] + st2d["w"] / 2, st2d["y"] + st2d["h"] / 2)
    span = min(st2d["w"] * st2["dpr"], 900)
    gesture("pinch", "pinch", pcx, pcy, round(span * 0.25), round(span * 0.85), 600)
    st3 = state()
    shot("g4-pinched")
    w2, w3 = st2.get("contentW") or 0, st3.get("contentW") or 0
    check("pinch out zooms in", w3 > w2 * 1.08 or (st3.get("zoomed") and not st2.get("zoomed")),
          {"contentW_before": w2, "contentW_after": w3, "zoomed": [st2.get("zoomed"), st3.get("zoomed")]})

# ── 5. Arrange: long-press a page and drag it ─────────────────────────────────
xml = dump()
m = None
for node in re.finditer(r'<node [^>]*>', xml):
    n = node.group(0)
    if re.search(r'(text|content-desc)="Arrange( \d)?"', n):
        m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
        if m:
            break
check("Arrange button found on screen", m is not None, {})
if m:
    x1, y1, x2, y2 = map(int, m.groups())
    touch("tap", (x1 + x2) // 2, (y1 + y2) // 2)
    st4 = wait_for(lambda s: (s.get("shelfPages") or 0) >= 6 and s.get("deskDrop"), 40, "Arrange (Shelf pages and a desk)")
    shot("g5-arrange")
    check("Arrange shows the document's pages on the Shelf", (st4.get("shelfPages") or 0) >= 6,
          {"shelfPages": st4.get("shelfPages"), "deskPages": st4.get("deskPages")})
    if not st4.get("shelfVisible") and st4.get("shelfHead"):
        # Phone: the Shelf rests as a peek; a tap on its header opens it (12j).
        h = st4["shelfHead"]
        hx, hy = to_screen(st4, h["x"] + h["w"] / 2, h["y"] + h["h"] / 2)
        gesture("shelf-open", "tap", hx, hy)
        st4 = wait_for(lambda s: len(s.get("shelfVisible") or []) >= 1, 20, "the Shelf to open")
        shot("g6-shelf-open")
        check("tap on the Shelf header opens it", len(st4.get("shelfVisible") or []) >= 1, {"visible": len(st4.get("shelfVisible") or [])})
    if st4.get("shelfVisible") and st4.get("deskDrop"):
        a, dz = st4["shelfVisible"][0], st4["deskDrop"]
        ax, ay = to_screen(st4, a["x"] + a["w"] / 2, a["y"] + a["h"] / 2)
        tx, ty = to_screen(st4, dz["x"] + dz["w"] / 2, dz["y"] + dz["h"] / 2)
        gesture("longdrag", "longdrag", ax, ay, tx, ty, 800, 900)
        st5 = state()
        shot("g7-dragged")
        check("long-press drag puts a Shelf page on the desk", (st5.get("deskPages") or 0) > (st4.get("deskPages") or 0),
              {"deskPages_before": st4.get("deskPages"), "deskPages_after": st5.get("deskPages"), "order": st5.get("order")})

with open(os.path.join(OUT, "gestures.json"), "w") as f:
    json.dump({"webview": WEBVIEW, "results": results}, f, indent=2)
failed = [r["check"] for r in results if not r["pass"]]
print(f"{len(results) - len(failed)}/{len(results)} gesture checks passed")
sys.exit(1 if failed else 0)
