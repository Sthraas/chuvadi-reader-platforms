#!/usr/bin/env python3
"""Emulator gesture test (CI only). Runs after smoke-test.sh, with the app installed and running.

1. Opens a 6-page test PDF the way another app would: pushed to Downloads, then an
   ACTION_VIEW intent with its MediaStore content:// URI ("Open with").
2. Real touch gestures (touch.py → the emulator's touchscreen), each checked against the page's
   own state (cdp.py), with a screenshot after each:
     swipe            → page counter moves on by one page
     double-tap       → fit mode flips (Fit width ⇄ Fit page)
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

STATE_JS = r"""
(() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight; };
  const desk = [...document.querySelectorAll('.rdesk')].find(vis) || null;
  const page = [...document.querySelectorAll('.rpage')].find(vis) || null;
  const fitOn = t => [...document.querySelectorAll('[title^="' + t + '"]')].some(e => e.classList.contains('on') || e.classList.contains('active') || e.getAttribute('aria-pressed') === 'true');
  const ctr = (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim();
  const rect = e => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; };
  const cards = [...document.querySelectorAll('[data-bench-id]')].filter(vis);
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
    """Runs one gesture; returns False (and prints why) if the touch tool failed."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "touch.py"), *map(str, args)],
                       capture_output=True, text=True)
    print("  " + (r.stdout.strip() or f"touch.py {' '.join(map(str, args))}"))
    if r.returncode != 0:
        print("  touch.py failed:\n" + r.stderr.strip())
        check(f"touch input ({args[0]})", False, {"stderr": r.stderr.strip()[-600:]})
        return False
    return True


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

if st0.get("desk"):
    d = st0["desk"]
    cx, cy = d["x"] + d["w"] / 2, d["y"] + d["h"] / 2

    # ── 2. Swipe left → next page ─────────────────────────────────────────────
    x1, y1 = to_screen(st0, d["x"] + d["w"] * 0.80, cy)
    x2, y2 = to_screen(st0, d["x"] + d["w"] * 0.20, cy)
    touch("swipe", x1, y1, x2, y2, 250)
    time.sleep(2)
    st1 = state()
    shot("g2-swiped")
    check("swipe left moves to the next page", (counter_number(st1) or 0) > (counter_number(st0) or 0),
          {"before": st0.get("counter"), "after": st1.get("counter"), "overflowX": st0.get("overflowX")})

    # ── 3. Double-tap → Fit width ⇄ Fit page ──────────────────────────────────
    sx, sy = to_screen(st1, cx, cy)
    touch("doubletap", sx, sy)
    time.sleep(2)
    st2 = state()
    shot("g3-doubletapped")
    check("double-tap flips the fit mode", st2.get("fit") != st1.get("fit") and st2.get("fit") in ("width", "page"),
          {"before": st1.get("fit"), "after": st2.get("fit"), "pageW": [st1.get("page", {}).get("w"), st2.get("page", {}).get("w")]})

    # ── 4. Pinch out → zoom in ────────────────────────────────────────────────
    st2d = st2.get("desk") or d
    pcx, pcy = to_screen(st2, st2d["x"] + st2d["w"] / 2, st2d["y"] + st2d["h"] / 2)
    span = min(st2d["w"] * st2["dpr"], 900)
    touch("pinch", pcx, pcy, round(span * 0.25), round(span * 0.85), 600)
    time.sleep(2)
    st3 = state()
    shot("g4-pinched")
    w2, w3 = (st2.get("page") or {}).get("w") or 0, (st3.get("page") or {}).get("w") or 0
    check("pinch out zooms in", w3 > w2 * 1.08, {"pageW_before": w2, "pageW_after": w3, "zoomed": st3.get("zoomed")})

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
    st4 = wait_for(lambda s: len(s.get("cards") or []) >= 3, 40, "Arrange page cards")
    shot("g5-arrange")
    cards = st4.get("cards") or []
    check("Arrange shows the document's pages", len(st4.get("order") or []) >= 6, {"order": st4.get("order"), "visible": len(cards)})
    if len(cards) >= 3:
        a, c = cards[0], cards[2]
        ax, ay = to_screen(st4, a["x"] + a["w"] / 2, a["y"] + a["h"] / 2)
        tx, ty = to_screen(st4, c["x"] + c["w"] * 0.75, c["y"] + c["h"] / 2)
        touch("longdrag", ax, ay, tx, ty, 800, 700)
        time.sleep(2)
        st5 = state()
        shot("g6-dragged")
        before, after = st4.get("order") or [], st5.get("order") or []
        check("long-press drag reorders the pages", len(after) == len(before) and after != before and sorted(after) == sorted(before),
              {"before": before, "after": after})

with open(os.path.join(OUT, "gestures.json"), "w") as f:
    json.dump(results, f, indent=2)
failed = [r["check"] for r in results if not r["pass"]]
print(f"{len(results) - len(failed)}/{len(results)} gesture checks passed")
sys.exit(1 if failed else 0)
