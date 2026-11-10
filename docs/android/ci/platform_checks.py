#!/usr/bin/env python3
"""Emulator test of the Android platform layer (CI only). Runs after gestures.py on the same
emulator, with the app installed and running. Each check acts the way a user or another app would
(intents from the shell, real touches via touch.py, real key events via `input`) and reads the
result from the page (cdp.py), from Android itself (dumpsys, uiautomator) or from the files the
app produced. Screenshots and raw evidence go to the results folder.

  1. Open with while the app runs: .docx and .xlsx (ACTION_VIEW content://) → a NEW tab in the SAME
     activity and process (singleTask + OnNewIntent), the document's text on screen
  2. Share to Chuvadi: ACTION_SEND with a PDF stream → a new tab with that PDF
  3. Rotation with a document open → same process, same tab and page, no sideways overflow
  4. Hardware keyboard: → next page, Ctrl = zoom, Ctrl F + typing finds text, Esc closes find
  5. Soft keyboard: tap the find box → keyboard up, the box stays visible above it
  6. Printing: Print card → PrintManager dialog → "Save as PDF" → the saved file has every page;
     a custom range (2-3) gives a 2-page file; a PDF whose permissions forbid printing is locked (L-8)
  7. Back: closes an open card; on the phone closes a sheet (key and edge gesture); otherwise steps
     back through the app's screens and finally leaves the app; relaunch → same process, same tab
  8. Split screen → the app re-lays out to the half window, same process, no sideways overflow;
     back to full screen
Writes platform.json; exits 1 if any check fails.

    platform_checks.py <results-dir>

(Not named platform.py: with this folder first on sys.path, a library's `import platform` would load
this script again and run every check twice — round 3, run 42314548860.)
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
os.makedirs(OUT, exist_ok=True)
results = []
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("office", os.path.join(HERE, "make-test-office.py"))
office = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(office)

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
  const card = document.querySelector('section.chvd-card[aria-label="Print"]');
  const find = document.querySelector('.rfind-box');
  const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
  const root = document.documentElement;
  return {
    shell: root.dataset.shell || null, formFactor: root.dataset.formFactor || null,
    dpr: devicePixelRatio, innerW: innerWidth, innerH: innerHeight,
    vvH: window.visualViewport ? visualViewport.height : innerHeight,
    overflowPage: root.scrollWidth - root.clientWidth,
    tab: ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t') || {}).textContent || '').trim(),
    counter: (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim(),
    pages: document.querySelectorAll('.rpage').length,
    pageW: page ? page.getBoundingClientRect().width : null,
    desk: r(desk),
    printCard: !!card, printButton: card ? (card.querySelector('.footer .primary')?.textContent || '').trim() : null,
    sheet: !!document.querySelector('.ph-sheet'),
    tabs: (() => { const sub = (document.querySelector('.ph-sub')?.textContent || '').match(/of\s+(\d+)\s+tab/);
                   if (sub) return +sub[1];
                   // Tablet / desktop strip: one .rtab per open tab (the "+N" chip is just Tabs.Count - 1).
                   return document.querySelectorAll('.rtab').length; })(),
    route: location.pathname + location.search,
    active: document.activeElement ? (document.activeElement.tagName + '.' + String(document.activeElement.className || '').split(' ')[0]) : null,
    printReason: card ? (card.querySelector('.footer .primary')?.getAttribute('title') || card.getAttribute('title') || '') : null,
    printDisabled: card ? !!card.querySelector('.footer .primary')?.disabled : null,
    find: find ? { value: find.value, focused: document.activeElement === find, rect: r(find) } : null,
    findCount: (document.querySelector('.rfind-count')?.textContent || '').trim(),
    text: (document.body.innerText || '').slice(0, 20000),
  };
})()
"""


def adb(*args, check=False):
    return subprocess.run(["adb", *args], check=check, capture_output=True, text=True).stdout


def shot(name):
    with open(os.path.join(OUT, name + ".png"), "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True).stdout)


def save(name, text):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(text)


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
        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(2)
    return xml


def node_center(xml, pattern):
    """Centre of the first UI node whose attributes match `pattern` (a regex over the node tag)."""
    for node in re.finditer(r"<node [^>]*>", xml):
        n = node.group(0)
        if re.search(pattern, n):
            m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                if x2 > x1 and y2 > y1:
                    return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def texts(xml):
    return [t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()]


def state():
    return cdp.evaluate(STATE_JS)


def safe_state():
    """The page state, or {"error": …} while the WebView isn't reachable yet (a new process after a kill:
    DevTools refuses or resets the connection for a moment — run 42739965634)."""
    try:
        return state()
    except (SystemExit, Exception) as e:  # noqa: BLE001 — any failure to reach the page means "not yet"
        return {"error": f"{type(e).__name__}: {e}"}


def brief(st, *keys):
    return {k: st.get(k) for k in keys}


def check(name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " — " + json.dumps(detail)[:700])
    if not ok:
        print(f"::error::platform check failed: {name}")


def wait_for(pred, seconds, what):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        last = safe_state()
        try:
            if "error" not in last and pred(last):
                return last
        except (KeyError, TypeError):
            pass
        dump()
        time.sleep(2)
    print(f"timed out waiting for {what}: {json.dumps(last)[:400]}")
    return last or {}


def pid():
    return adb("shell", "pidof", PKG).strip()


def resumed():
    """The package of the resumed (top) activity."""
    out = adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"(?:topResumedActivity|mResumedActivity|ResumedActivity)[:=].*? ([\w.]+)/", out)
    return m.group(1) if m else None


def activity_records():
    """How many of our activities exist, and in how many tasks (singleTask: one and one)."""
    out = adb("shell", "dumpsys", "activity", "activities")
    acts = set(re.findall(r"ActivityRecord\{[0-9a-f]+ u0 " + re.escape(PKG) + r"/[\w.$]+ t(\d+)", out))
    recs = re.findall(r"ActivityRecord\{([0-9a-f]+) u0 " + re.escape(PKG) + r"/", out)
    return {"records": sorted(set(recs)), "tasks": sorted(acts)}


def save_log(name):
    """Our process's log lines (tag Chuvadi, crashes, the WebView console) as evidence."""
    log = adb("logcat", "-d", "-v", "time")
    keep = [ln for ln in log.splitlines() if re.search(r"Chuvadi|AndroidRuntime|chromium.*Console|" + re.escape(PKG), ln)]
    save(name, "\n".join(keep[-400:]))


def webview_origin():
    m = re.search(r'class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]', dump())
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def touch(*args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "touch.py"), *map(str, args)], capture_output=True, text=True)
    print("  " + (r.stdout.strip() or f"touch.py {' '.join(map(str, args))}"))
    if r.returncode != 0:
        print("  touch.py failed:\n" + r.stderr.strip())
    return r.returncode == 0


RECT_JS = r"""
((sel, text) => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const els = [...document.querySelectorAll(sel)].filter(e => !text || (e.textContent || '').trim().startsWith(text)).filter(vis);
  const e = els[0];
  if (!e) return null;
  e.scrollIntoView({ block: 'center', inline: 'center' });
  const r = e.getBoundingClientRect();
  return { x: r.x + r.width / 2, y: r.y + r.height / 2, dpr: devicePixelRatio };
})(%s, %s)
"""


def tap_el(sel, text=None):
    """A real tap on the page element matching `sel` (and starting with `text`)."""
    try:
        c = cdp.evaluate(RECT_JS % (json.dumps(sel), json.dumps(text)))
    except SystemExit as e:
        print("  page not reachable: %s" % e)
        return False
    if not c:
        print(f"  no element {sel} {text or ''}")
        return False
    time.sleep(0.4)
    ox, oy = webview_origin()
    return touch("tap", round(ox + c["x"] * c["dpr"]), round(oy + c["y"] * c["dpr"]))


def tap_node(pattern, what):
    xml = dump()
    c = node_center(xml, pattern)
    if not c:
        print(f"  {what} not on screen; texts: {texts(xml)[:30]}")
        return False
    return touch("tap", *c)


def key(*codes):
    if len(codes) == 1:
        adb("shell", "input", "keyevent", codes[0])
    else:
        adb("shell", "input", "keycombination", *codes)
    time.sleep(1.2)


def am_as_shell(*args):
    """`am` as the shell user (uid 2000). gestures.py leaves adbd running as root, and a URI grant
    made by root's `am` doesn't reach the app; a real sending app is an ordinary user too."""
    root = adb("shell", "id -u").strip() == "0"
    cmd = (["su", "2000"] if root else []) + ["am", *args]
    return adb("shell", *cmd)


def media_uri(name):
    for attempt in range(15):
        for coll in ("downloads", "file"):
            rows = adb("shell", "content", "query", "--uri", f"content://media/external/{coll}", "--projection", "_id",
                       "--where", f"\"_display_name='{name}'\"")
            m = re.search(r"_id=(\d+)", rows)
            if m:
                return f"content://media/external/{coll}/{m.group(1)}"
        if attempt == 3:
            adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file:///sdcard/Download/{name}")
        time.sleep(2)
    return None


def counter_number(st):
    m = re.search(r"(\d+)", st.get("counter") or "")
    return int(m.group(1)) if m else None


def counter_total(st):
    m = re.search(r"/\s*(\d+)", st.get("counter") or "")
    return int(m.group(1)) if m else None


def pdf_pages(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page(?![a-z])", data))


def phone():
    return (safe_state().get("shell") or "") == "phone"


def go_read():
    """Read mode via a tap on the Read button (bottom bar / rail). Plain `input tap` works as the shell user."""
    xml = dump()
    c = node_center(xml, r'(text|content-desc)="Read( 1)?"')
    if c:
        adb("shell", "input", "tap", str(c[0]), str(c[1]))
    return wait_for(lambda s: s.get("desk") is not None, 20, "Read mode")


# Gboard treats the test touchscreen as a stylus and shows "Try out your stylus" over the app,
# which swallows typing. Android setting, not the app's: turn stylus handwriting off.
adb("shell", "settings", "put", "secure", "stylus_handwriting_enabled", "0")


def dismiss_ime_dialogs():
    xml = dump()
    if re.search(r'text="Try out your stylus"', xml):
        tap_node(r'text="(Cancel|CANCEL|Skip|SKIP)"', "the stylus tutorial's Cancel")
        time.sleep(1)


TYPE_JS = "(() => { const e = document.activeElement; return e && 'value' in e ? e.value : null; })()"


def type_slowly(text):
    """One key at a time, through the on-screen keyboard (IME), reading the field after each key."""
    seen = []
    for ch in text:
        adb("shell", "input", "text", ch)
        time.sleep(0.5)
        try:
            seen.append(cdp.evaluate(TYPE_JS))
        except SystemExit:
            seen.append(None)
    return seen


# ── 0. Read mode ─────────────────────────────────────────────────────────────
# gestures.py ends in Arrange, where a file opened from another app goes onto the Shelf (by design,
# like a desktop drop: PLATFORM-INTERFACE §4). Open with / Share are tested from Read.
r = go_read()
check("start in Read mode", r.get("desk") is not None, brief(r, "tab", "counter"))

# ── 1. Open with: .docx and .xlsx ────────────────────────────────────────────
DOCX, XLSX, SHARE_PDF = "chuvadi-test.docx", "chuvadi-test.xlsx", "chuvadi-share.pdf"
office.docx(os.path.join(OUT, DOCX))
office.xlsx(os.path.join(OUT, XLSX))
subprocess.run([sys.executable, os.path.join(HERE, "make-test-pdf.py"), os.path.join(OUT, SHARE_PDF), "4"], check=True)
for name in (DOCX, XLSX, SHARE_PDF):
    adb("push", os.path.join(OUT, name), f"/sdcard/Download/{name}")

for name, mime, marker, shotname in (
        (DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", office.DOCX_MARKER, "p1-docx"),
        (XLSX, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", office.XLSX_MARKER, "p2-xlsx")):
    uri = media_uri(name)
    before, pid_before, acts_before = safe_state(), pid(), activity_records()
    out = am_as_shell("start", "-W", "-a", "android.intent.action.VIEW", "-d", str(uri), "-t", mime,
                      "-p", PKG, "--grant-read-uri-permission").strip()
    print(out)
    st = wait_for(lambda s: marker in (s.get("text") or ""), 60, f"{name} to show")
    acts = activity_records()
    shot(shotname)
    check(f"Open with {name} while running: a new tab in the same activity and process",
          uri is not None and marker in (st.get("text") or "") and pid() == pid_before
          and (st.get("tabs") or 0) == (before.get("tabs") or 0) + 1 and len(acts["records"]) == 1 and acts == acts_before,
          {"uri": uri, "tab": st.get("tab"), "tabs": [before.get("tabs"), st.get("tabs")], "pid": [pid_before, pid()],
           "activities": [acts_before, acts], "am": out.splitlines()[-3:] if out else None, "marker": marker})

# AT-12: Open with on a document that is already open brings its tab forward (as Windows does), no duplicate.
uri = media_uri(DOCX)
before = safe_state()
am_as_shell("start", "-W", "-a", "android.intent.action.VIEW", "-d", str(uri), "-t",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "-p", PKG, "--grant-read-uri-permission")
again = wait_for(lambda s: s.get("tab") == DOCX and office.DOCX_MARKER in (s.get("text") or ""), 30, f"{DOCX} in front")
time.sleep(3)   # a duplicate would arrive after the copy and first render
again = safe_state()
shot("p2b-docx-again")
check("Open with on a document that is already open focuses its tab, no duplicate (AT-12)",
      again.get("tab") == DOCX and (again.get("tabs") or 0) == (before.get("tabs") or 0) and before.get("tab") == XLSX,
      {"tab": [before.get("tab"), again.get("tab")], "tabs": [before.get("tabs"), again.get("tabs")]})
save_log("log-open-with.txt")

# ── 2. Share to Chuvadi: ACTION_SEND with a PDF stream ────────────────────────
# The URI goes in both EXTRA_STREAM (what a sharing app sets) and the data field, because `am`
# grants --grant-read-uri-permission on the data URI; DocumentImport reads EXTRA_STREAM.
uri = media_uri(SHARE_PDF)
tabs_before = safe_state().get("tabs") or 0   # before the intent: the tab can be there before the next read
print(am_as_shell("start", "-a", "android.intent.action.SEND", "-t", "application/pdf", "-d", str(uri),
                  "--eu", "android.intent.extra.STREAM", str(uri), "-p", PKG, "--grant-read-uri-permission").strip())
# Pages from the page elements: the tablet's counter is a box with the page number only (no "/ 4").
st = wait_for(lambda s: SHARE_PDF.split(".")[0] in (s.get("tab") or "") and s.get("pages", 0) == 4,
              60, "the shared PDF to open")
shot("p3-shared")
check("Share to Chuvadi (ACTION_SEND, EXTRA_STREAM) opens the PDF in a new tab",
      SHARE_PDF.split(".")[0] in (st.get("tab") or "") and st.get("pages") == 4 and (st.get("tabs") or 0) == tabs_before + 1,
      {**brief(st, "tab", "counter", "pages"), "tabs": [tabs_before, st.get("tabs")]})
save_log("log-share.txt")

# The L-8 fixture: a PDF whose own permissions forbid printing (opened now, as the shell user).
NOPRINT = "chuvadi-no-print.pdf"
adb("push", os.path.join(HERE, "fixtures", "no-print.pdf"), f"/sdcard/Download/{NOPRINT}")
noprint_uri = media_uri(NOPRINT)

# Touch input (touch.py) needs a root adbd; the intents above ran as the shell user on purpose
# (a grant from root's `am` doesn't reach the app the same way).
print(adb("root").strip())
adb("wait-for-device")
for _ in range(20):
    if adb("shell", "id -u").strip() == "0":
        break
    time.sleep(1)
time.sleep(2)

# ── 3. Rotation with a document open ─────────────────────────────────────────
base = wait_for(lambda s: s.get("pages") == 4, 30, "the shared PDF")
pid0 = pid()
wide0 = base.get("innerW", 0) > base.get("innerH", 0)
adb("shell", "cmd", "window", "user-rotation", "lock", "1")
land = wait_for(lambda s: (s["innerW"] > s["innerH"]) != wide0, 20, "the other orientation")
time.sleep(1.5)
land = safe_state()
shot("p4-rotated")
check("rotation keeps the process, tab and page; no sideways overflow",
      pid() == pid0 and (land.get("innerW", 0) > land.get("innerH", 0)) != wide0 and land.get("tab") == base.get("tab")
      and land.get("counter") == base.get("counter") and (land.get("overflowPage") or 0) <= 1,
      {"pid": [pid0, pid()], "size": [land.get("innerW"), land.get("innerH")], "tab": land.get("tab"),
       "counter": [base.get("counter"), land.get("counter")], "overflowPage": land.get("overflowPage"), "shell": land.get("shell")})
adb("shell", "cmd", "window", "user-rotation", "lock", "0")
port = wait_for(lambda s: (s["innerW"] > s["innerH"]) == wide0, 20, "the natural orientation")
time.sleep(1.5)
port = safe_state()
check("rotation back keeps the process and tab",
      pid() == pid0 and port.get("tab") == base.get("tab") and (port.get("overflowPage") or 0) <= 1,
      {"pid": pid(), "size": [port.get("innerW"), port.get("innerH")], "tab": port.get("tab"), "overflowPage": port.get("overflowPage")})

# ── 4. Hardware keyboard ─────────────────────────────────────────────────────
# Focus the page with a tap on the desk margin (not a button), then real key events.
st = safe_state()
if st.get("desk"):
    d = st["desk"]
    ox, oy = webview_origin()
    # Beside the page (the desk's own margin): focuses the page without showing the page strip.
    touch("tap", round(ox + (d["x"] + 6) * st["dpr"]), round(oy + (d["y"] + d["h"] / 2) * st["dpr"]))
    time.sleep(1)
k0 = safe_state()
key("KEYCODE_DPAD_RIGHT")
k1 = wait_for(lambda s: (counter_number(s) or 0) > (counter_number(k0) or 0), 6, "→ to change the page")
check("keyboard → goes to the next page", (counter_number(k1) or 0) > (counter_number(k0) or 0),
      {"before": k0.get("counter"), "after": k1.get("counter"), "focus": k0.get("active")})
key("KEYCODE_CTRL_LEFT", "KEYCODE_EQUALS")
k2 = wait_for(lambda s: (s.get("pageW") or 0) > (k1.get("pageW") or 0) * 1.05, 6, "Ctrl = to zoom in")
check("keyboard Ctrl = zooms in", (k2.get("pageW") or 0) > (k1.get("pageW") or 0) * 1.05,
      {"pageW": [k1.get("pageW"), k2.get("pageW")]})
key("KEYCODE_CTRL_LEFT", "KEYCODE_0")
key("KEYCODE_CTRL_LEFT", "KEYCODE_F")
kf = wait_for(lambda s: s.get("find") is not None, 6, "Ctrl F to open find")
dismiss_ime_dialogs()
adb("shell", "input", "keycombination", "KEYCODE_CTRL_LEFT", "KEYCODE_A")   # clear what a previous search left
adb("shell", "input", "keyevent", "KEYCODE_DEL")
typed_find = type_slowly("test")
adb("shell", "input", "keyevent", "KEYCODE_ENTER")
# Gboard's autocorrect capitalises the first letter when Enter commits ("Test"): the keyboard's own
# behaviour (the control field below gets no Enter, so stays lower-case); the search is case-insensitive.
kf = wait_for(lambda s: ((s.get("find") or {}).get("value") or "").lower() == "test" and re.search(r"[1-9]", s.get("findCount") or ""), 10, "find results")
shot("p5-find")
check("keyboard Ctrl F opens find; typed text finds matches",
      ((kf.get("find") or {}).get("value") or "").lower() == "test" and bool(re.search(r"[1-9]", kf.get("findCount") or "")),
      {"find": kf.get("find"), "count": kf.get("findCount"), "afterEachKey": typed_find})

# Control for typing: the same keys into a plain <input> with no Blazor binding (test-only, added
# through DevTools and removed after). Garbled here too → the input path (IME/WebView/host);
# clean here but garbled in Find → the page's own field handling.
key("KEYCODE_ESCAPE")
cdp.evaluate("""(() => { const i = document.createElement('input'); i.id = 'chvd-probe';
  i.style.cssText = 'position:fixed;top:120px;left:20px;width:240px;height:40px;z-index:99999;font-size:18px';
  document.body.appendChild(i); return true; })()""")
tap_el("#chvd-probe")
time.sleep(1.5)
dismiss_ime_dialogs()
typed_probe = type_slowly("test")
probe_value = cdp.evaluate("document.getElementById('chvd-probe').value")
check("typing control: the same keys into a plain field arrive exactly",
      probe_value == "test", {"value": probe_value, "afterEachKey": typed_probe})
cdp.evaluate("document.getElementById('chvd-probe').remove()")
adb("shell", "input", "keyevent", "KEYCODE_BACK") if "imeVisible=true" in adb("shell", "dumpsys", "window", "InputMethod") else None
time.sleep(1)

# ── 5. Soft keyboard ─────────────────────────────────────────────────────────
# The emulator may report a hardware keyboard; ask Android to show the on-screen one anyway.
adb("shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "1")
key("KEYCODE_ESCAPE")  # close find from step 4
h_pre = safe_state()  # window height with no keyboard
key("KEYCODE_CTRL_LEFT", "KEYCODE_F")
h0 = wait_for(lambda s: s.get("find") is not None, 6, "find to open")
wv_before = re.search(r'class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', dump())
tap_el(".rfind-box")
time.sleep(2.5)
dismiss_ime_dialogs()
ime = adb("shell", "dumpsys", "input_method")
win_ime = adb("shell", "dumpsys", "window", "InputMethod")
save("ime.txt", ime + "\n\n" + win_ime)
shown = bool(re.search(r"(mInputShown|mIsInputViewShown|isInputViewShown)\S*=true", ime)) or "imeVisible=true" in win_ime
h1 = safe_state()
shot("p6-soft-keyboard")
wv_after = re.search(r'class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', dump())
ime_win = re.search(r"Window\{[^}]*InputMethod\}.*?(?:mFrame|frame)=\[(\d+),(\d+)\]\[(\d+),(\d+)\]", win_ime, re.S)
ime_top = int(ime_win.group(2)) if ime_win else None
f = (h1.get("find") or {}).get("rect") or {}
visible = f and f.get("y", -1) >= 0 and f.get("y", 0) + f.get("h", 0) <= (h1.get("vvH") or 0) + 1
check("soft keyboard opens for the find box and the box stays visible above it",
      shown and (h1.get("find") or {}).get("focused") and visible and (h1.get("innerH") or 0) < (h_pre.get("innerH") or 0),
      {"imeShown": shown, "imeTopPx": ime_top,
       "webViewBottomPx": [int(wv_before.group(4)) if wv_before else None, int(wv_after.group(4)) if wv_after else None],
       "focused": (h1.get("find") or {}).get("focused"), "findRect": f,
       "innerH": [h_pre.get("innerH"), h1.get("innerH")], "visualViewportH": h1.get("vvH")})
key("KEYCODE_BACK")   # hides the keyboard (Android's own first back)
key("KEYCODE_ESCAPE")  # closes find
time.sleep(1)


# ── 6. Printing through PrintManager ─────────────────────────────────────────
def open_print_card():
    if phone():
        for _ in range(2):
            tap_el('.ph-bar button[aria-label="More"]')
            if wait_for(lambda s: s.get("sheet"), 6, "the ⋮ menu").get("sheet"):
                break
        shot("p7-menu")
        tap_el(".ph-row", "Print")
    else:
        key("KEYCODE_CTRL_LEFT", "KEYCODE_P")
    return wait_for(lambda s: s.get("printCard"), 10, "the Print card")


def leave_spooler():
    """Back out of the print dialog / file picker until the app is on top again."""
    for _ in range(4):
        if resumed() == PKG:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.5)


def print_and_save(tag):
    """Taps the card's Print button, then saves through the system "Save as PDF" printer.
    Returns (dialog_seen, saved_pdf_path_or_None, evidence)."""
    adb("shell", "touch", "/data/local/tmp/chvd-print-mark")
    time.sleep(1.1)
    tap_el('section.chvd-card[aria-label="Print"] .footer .primary')
    seen, xml = False, ""
    for _ in range(15):
        time.sleep(2)
        if (resumed() or "").startswith("com.android.printspooler"):
            seen = True
            break
    time.sleep(3)  # preview renders
    xml = dump()
    shot(f"p7-print-dialog-{tag}")
    ev = {"resumed": resumed(), "dialogTexts": texts(xml)[:40]}
    if not seen:
        return False, None, ev
    # Pick the system "Save as PDF" printer if none is selected; its button saves through the file picker.
    if node_center(xml, r'text="Select a printer"'):
        tap_node(r'text="Select a printer"', "the printer list")
        time.sleep(2)
        tap_node(r'text="Save as PDF"', "Save as PDF")
        time.sleep(3)
        xml = dump()
        shot(f"p7-print-dialog-{tag}-pdf")
        ev["dialogTexts"] = texts(xml)[:40]
    if not tap_node(r'resource-id="com\.android\.printspooler:id/print_button"', "the PDF button"):
        leave_spooler()
        return True, None, ev
    time.sleep(4)
    xml = dump()
    shot(f"p8-save-{tag}")
    ev["pickerTexts"] = texts(xml)[:40]
    tap_node(r'(text="(SAVE|Save)"|resource-id="android:id/button1")', "Save")
    time.sleep(2)
    xml = dump()
    if node_center(xml, r'text="(OK|Replace|REPLACE)"'):
        tap_node(r'text="(OK|Replace|REPLACE)"', "Replace")
    path = None
    for _ in range(15):
        time.sleep(2)
        # /storage/emulated/0, not /sdcard: `find` doesn't follow the /sdcard symlink.
        found = [ln.strip() for ln in adb("shell", "find", "/storage/emulated/0/", "-name", "'*.pdf'", "-newer",
                                          "/data/local/tmp/chvd-print-mark").splitlines() if ln.strip()]
        if found:
            path = found[0]
            break
    ev["savedAs"] = path
    leave_spooler()
    if path:
        local = os.path.join(OUT, f"printed-{tag}.pdf")
        adb("pull", path, local)   # one argv item each: names like "chuvadi-share (1).pdf" have spaces
        adb("shell", "rm", "-f", f"'{path}'")
        ev["saved"] = path
        return True, local, ev
    return True, None, ev


doc_pages = safe_state().get("pages")
pc = open_print_card()
shot("p7-print-card")
check("Print opens the Print card", pc.get("printCard"), brief(pc, "printButton", "shell"))
if pc.get("printCard"):
    seen, local, ev = print_and_save("all")
    check("Print hands the document to Android's print dialog (PrintManager)", seen, ev)
    n = pdf_pages(local) if local else None
    check(f"Save as PDF from the print dialog gives every page ({doc_pages})", n is not None and n == doc_pages, {"pages": n, **{k: ev.get(k) for k in ("saved", "pickerTexts")}})
    # Back in the app: the card is still open after printing; a custom range goes through
    # PageOperations.Assemble into a temporary PDF.
    wait_for(lambda s: True, 5, "the app")
    pc = safe_state() if safe_state().get("printCard") else open_print_card()
    tap_el('section.chvd-card[aria-label="Print"] .seg button', "Custom")
    time.sleep(1)
    tap_el('section.chvd-card[aria-label="Print"] input')
    time.sleep(1)
    adb("shell", "input", "text", "2-3")
    if "imeVisible=true" in adb("shell", "dumpsys", "window", "InputMethod"):
        key("KEYCODE_BACK")  # hide the keyboard so it doesn't cover the Print button
    pr = wait_for(lambda s: "2" in (s.get("printButton") or ""), 6, "the custom range")
    seen2, local2, ev2 = print_and_save("range")
    n2 = pdf_pages(local2) if local2 else None
    check("Printing a custom range (2-3) gives a 2-page PDF", seen2 and n2 == 2,
          {"button": pr.get("printButton"), "pages": n2, "saved": ev2.get("saved"), "resumed": ev2.get("resumed")})

# L-8: a PDF whose own permissions forbid printing — the Print card is locked with the reason.
leave_spooler()
if noprint_uri:
        am_as_shell("start", "-a", "android.intent.action.VIEW", "-d", noprint_uri, "-t", "application/pdf",
                "-p", PKG, "--grant-read-uri-permission")
npst = wait_for(lambda s: "no-print" in (s.get("tab") or "") and (s.get("pages") or 0) >= 1, 40, "the no-print PDF")
npc = open_print_card()
shot("p8-no-print-card")
check("a PDF whose permissions forbid printing: the Print card is locked with the reason (L-8)",
      npc.get("printCard") and npc.get("printDisabled") and "permissions don't allow printing" in (npc.get("printReason") or ""),
      {"tab": npst.get("tab"), "printDisabled": npc.get("printDisabled"), "reason": npc.get("printReason"), "uri": noprint_uri})
if npc.get("printCard"):
    tap_el('section.chvd-card[aria-label="Print"] button.close')
    time.sleep(1)

# ── 7. Back ──────────────────────────────────────────────────────────────────
wait_for(lambda s: True, 5, "the app")
if not safe_state().get("printCard"):
    open_print_card()
b0 = safe_state()
key("KEYCODE_BACK")
b1 = safe_state()
check("back closes an open card (Print) and stays on the same screen",
      b0.get("printCard") and not b1.get("printCard") and resumed() == PKG and b1.get("route") == b0.get("route")
      and b1.get("tab") == b0.get("tab"),
      {"cardBefore": b0.get("printCard"), "cardAfter": b1.get("printCard"), "resumed": resumed(),
       "route": [b0.get("route"), b1.get("route")], "tab": [b0.get("tab"), b1.get("tab")]})
if b1.get("printCard"):
    tap_el('section.chvd-card[aria-label="Print"] button.close')
    time.sleep(1)

if phone():
    tap_el('.ph-bar button[aria-label="More"]')
    s0 = wait_for(lambda s: s.get("sheet"), 8, "the ⋮ menu")
    key("KEYCODE_BACK")
    s1 = safe_state()
    check("phone: back (key) closes the ⋮ sheet and stays in the app",
          s0.get("sheet") and not s1.get("sheet") and resumed() == PKG,
          {"sheetBefore": s0.get("sheet"), "sheetAfter": s1.get("sheet"), "resumed": resumed()})
    tap_el('.ph-bar button[aria-label="More"]')
    s0 = wait_for(lambda s: s.get("sheet"), 8, "the ⋮ menu")
    wm = re.search(r"(\d+)x(\d+)", adb("shell", "wm", "size"))
    sw, sh = int(wm.group(1)), int(wm.group(2))
    touch("swipe", 2, sh // 2, sw // 2, sh // 2, 250)   # the back gesture: from the left edge inwards
    time.sleep(1.5)
    s1 = safe_state()
    shot("p9-back-gesture")
    check("phone: back (edge gesture) closes the ⋮ sheet and stays in the app",
          s0.get("sheet") and not s1.get("sheet") and resumed() == PKG,
          {"sheetBefore": s0.get("sheet"), "sheetAfter": s1.get("sheet"), "resumed": resumed()})

r0 = safe_state()
pid0 = pid()
steps = []
for _ in range(12):   # back steps through the app's own screens (WebView history), then leaves
    before = safe_state() if resumed() == PKG else {}
    key("KEYCODE_BACK")
    time.sleep(0.8)
    now = resumed()
    steps.append({"from": before.get("route"), "to": safe_state().get("route") if now == PKG else None, "resumed": now})
    if now != PKG:
        break
left = steps[-1]["resumed"] if steps else None
dead = [st_ for st_ in steps if st_["resumed"] == PKG and st_["from"] == st_["to"]]
check("back steps back through the app's screens, then leaves the app; the process stays",
      left not in (PKG, None) and pid() == pid0 and not dead,
      {"steps": steps, "pid": [pid0, pid()], "deadPresses": len(dead)})
adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
r1 = wait_for(lambda s: s.get("route"), 20, "the app to come back")
shot("p10-relaunched")
last_route = steps[-1]["from"] if steps else None
r1 = wait_for(lambda s: s.get("route") == last_route, 10, "the screen it left from")
check("relaunch returns to the same process and the screen it left from", pid() == pid0 and r1.get("route") == last_route and resumed() == PKG,
      {"pid": [pid0, pid()], "route": [last_route, r1.get("route")]})

# D-89 B: Android can't take drops (DropFiles false), so Home says "open", never "drop".
if r1.get("route") != "/":
    adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
home = wait_for(lambda s: s.get("route") == "/", 10, "Home")
home_text = home.get("text") or ""
drop_words = sorted(set(re.findall(r"[^\n]*\b[Dd]rop(?:ped|ping|s)?\b[^\n]*", home_text)))
shot("p10b-home-wording")
check("Home wording says open, not drop (D-89 B, DropFiles false)",
      home.get("route") == "/" and not drop_words and bool(re.search(r"\bOpen\b", home_text)),
      {"route": home.get("route"), "dropLines": drop_words[:5],
       "openLines": re.findall(r"[^\n]*\bOpen\b[^\n]*", home_text)[:5]})


# ── 7b. AT-07: no private cache path in anything shown or read aloud ───────
# Home is showing, with the documents opened above as tabs, cards and recent rows. Every title,
# accessible name and visible text must name the document, never the working copy in the app's cache.
LABELS_JS = r"""
(() => {
  const leak = v => /\/data\/|\/cache\/work|in\.chuvadi\.reader/.test(v || '');
  const sel = '.rtab, .rcard, .rrow, .prow, .ph-tab, .lib-path, .libp-folder, .w-path, [title], [aria-label]';
  const all = [...document.querySelectorAll(sel)];
  const leaks = all.flatMap(e => [e.getAttribute('title'), e.getAttribute('aria-label')].filter(leak)
                                   .map(v => e.className + ': ' + v));
  if (leak(document.body.innerText)) leaks.push('text: ' + document.body.innerText.match(/[^\n]*(\/data\/|cache\/work)[^\n]*/)[0]);
  const named = [...document.querySelectorAll('.rcard, .rrow, .rtab')].map(e => e.getAttribute('title')).filter(Boolean);
  return { leaks: leaks.slice(0, 8), named: named.slice(0, 6), count: named.length };
})()
"""
try:
    labels = cdp.evaluate(LABELS_JS) or {}
except SystemExit as e:
    labels = {"error": str(e)}
check("no private cache path in tab, card or row titles, accessible names or text (AT-07)",
      "error" not in labels and labels.get("count", 0) > 0 and not labels.get("leaks")
      and all(re.search(r"\.(pdf|docx|xlsx)$", n, re.I) for n in labels.get("named", [])), labels)


# ── 7c. AT-08: the status and navigation bar areas follow the theme ──────────
def screen_rgba():
    """Raw screencap: a 12- or 16-byte header (width, height, format[, colour space]) then RGBA rows."""
    raw = subprocess.run(["adb", "exec-out", "screencap"], capture_output=True).stdout
    w, h = int.from_bytes(raw[0:4], "little"), int.from_bytes(raw[4:8], "little")
    return w, h, raw[len(raw) - w * h * 4:]


def row_colour(img, y):
    """The most common colour along one pixel row (icons, the camera cut-out and the gesture handle are small)."""
    w, h, px = img
    counts = {}
    for x in range(0, w, 3):
        i = (y * w + x) * 4
        c = (px[i], px[i + 1], px[i + 2])
        counts[c] = counts.get(c, 0) + 1
    return max(counts, key=counts.get)


def icons_are_light(img, bar):
    """Status-bar icons (clock, signal, battery) seen in the top 3.5 % of the screen: True if they are
    lighter than the bar, False if darker, None if none found. (The window manager's dump doesn't show the
    requested appearance on API 36, run 42541330985, so the pixels decide.)"""
    w, h, px = img
    lum = lambda r, g, b: 0.299 * r + 0.587 * g + 0.114 * b
    base = lum(*bar)
    far = []
    for y in range(int(h * 0.035)):
        for x in range(0, w, 2):
            i = (y * w + x) * 4
            v = lum(px[i], px[i + 1], px[i + 2])
            if abs(v - base) > 60:
                far.append(v)
    return None if len(far) < 50 else sum(far) / len(far) > base


# tokens.css --chvd-surface-hi: the Ui's bars that meet the screen edges.
BAR = {"Cream paper": (0xFB, 0xF7, 0xEC), "Night paper": (0x24, 0x1B, 0x15), "Palm leaf": (0xF6, 0xF2, 0xE1),
       "Indigo ink": (0xF8, 0xF9, 0xFC), "High contrast": (0xFF, 0xFF, 0xFF)}
tap_el('button[title="Settings"]')
wait_for(lambda s: (s.get("route") or "").startswith("/settings"), 15, "Settings")
tap_el(".snav-item", "Appearance")  # the phone shows the section list first (D-45); the tablet already shows it
time.sleep(1.5)
bars = {}
for name in ["Night paper", "Palm leaf", "Indigo ink", "High contrast", "Cream paper"]:
    tap_el(f'button.tc[title="Use {name}"]')
    time.sleep(1.5)
    img = screen_rgba()
    top, bottom = row_colour(img, 4), row_colour(img, img[1] - 3)
    shot("p10c-theme-" + name.split()[0].lower())
    ok = all(abs(a - b) <= 6 for c in (top, bottom) for a, b in zip(c, BAR[name]))
    light = icons_are_light(img, top)
    icons_ok = light == (name == "Night paper")
    bars[name] = {"top": "#%02x%02x%02x" % top, "bottom": "#%02x%02x%02x" % bottom,
                  "want": "#%02x%02x%02x" % BAR[name], "lightIcons": light, "pass": ok and icons_ok}
check("status and navigation bar areas take each theme's bar colour, light icons on Night paper (AT-08)",
      all(v["pass"] for v in bars.values()), bars)


# ── 7d. AT-11: Android ends the app in the background; coming back lands on the same document ──
tap_el('button[title="Home"]')
wait_for(lambda s: s.get("route") == "/", 15, "Home")
tap_el(".rcard")   # "Pick up where you left off" opens the Reader on that tab
# The page counter is filled once the pages are measured: wait for it on both sides (run 42799399331 read it empty).
k0 = wait_for(lambda s: s.get("route") == "/reader" and s.get("pages", 0) > 0 and s.get("tab") and s.get("counter"), 30, "the Reader")
key("KEYCODE_HOME")
time.sleep(2)
pid_before = pid()
adb("shell", "am", "kill", PKG)          # what Android does to a background app under memory pressure
time.sleep(2)
killed = pid() in ("", None) or pid() != pid_before
adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
k1 = wait_for(lambda s: s.get("route") == "/reader" and s.get("pages", 0) > 0 and s.get("tab") and s.get("counter"), 45, "the Reader after the kill")
shot("p10d-after-background-kill")
keep = ("route", "tab", "tabs", "counter")
check("after Android ends the app in the background, it comes back on the same document, page and tabs (AT-11)",
      killed and pid() not in ("", pid_before) and all(k0.get(k) == k1.get(k) for k in keep),
      {"killed": killed, "pid": [pid_before, pid()], "before": {k: k0.get(k) for k in keep}, "after": {k: k1.get(k) for k in keep}})


# ── 8. Split screen ──────────────────────────────────────────────────────────
def task_id():
    out = adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"Task\{[0-9a-f]+ #(\d+)[^}]*?(?:A=|I=)[^ }]*" + re.escape(PKG), out)
    return m.group(1) if m else None


def wmshell(*args):
    return adb("shell", "dumpsys", "activity", "service", "SystemUIService", "WMShell", *args)


full = safe_state()
pid0 = pid()
adb("shell", "am", "start", "-a", "android.settings.SETTINGS")
time.sleep(3)
adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
time.sleep(3)
tid = task_id()
out = wmshell("splitscreen", "moveToSideStage", str(tid), "1") if tid else "no task id"
save("split-command.txt", f"task {tid}\n{out}\n" + adb("shell", "dumpsys", "activity", "activities")[:20000])
split = wait_for(lambda s: s["innerW"] * s["innerH"] < full["innerW"] * full["innerH"] * 0.75, 20, "the split window")
time.sleep(2)
split = safe_state()
shot("p11-split")
in_split = split.get("innerW", 0) * split.get("innerH", 0) < full.get("innerW", 1) * full.get("innerH", 1) * 0.75
check("split screen: the app re-lays out to the half window (same process, no sideways overflow)",
      in_split and pid() == pid0 and (split.get("overflowPage") or 0) <= 1 and split.get("tab") == full.get("tab"),
      {"size": [[full.get("innerW"), full.get("innerH")], [split.get("innerW"), split.get("innerH")]],
       "formFactor": [full.get("formFactor"), split.get("formFactor")], "shell": [full.get("shell"), split.get("shell")],
       "overflowPage": split.get("overflowPage"), "pid": [pid0, pid()], "command": out.strip()[:200]})
component = adb("shell", "cmd", "package", "resolve-activity", "--brief", PKG).split()[-1]
full_again = lambda s: abs(s["innerW"] - full["innerW"]) <= 2 and abs(s["innerH"] - full["innerH"]) <= 60
# Ways out of split screen, tried in turn until the window is full size again (WMShell's command set
# differs between Android versions); the one that worked is recorded.
exits = [
    ("WMShell exitSplitScreen", lambda: wmshell("splitscreen", "exitSplitScreen", str(tid))),
    ("WMShell removeFromSideStage", lambda: wmshell("splitscreen", "removeFromSideStage", str(tid))),
    ("am start --windowingMode 1", lambda: adb("shell", "am", "start", "--windowingMode", "1", "-n", component)),
    ("home, then am start --windowingMode 1", lambda: (adb("shell", "input", "keyevent", "KEYCODE_HOME"), time.sleep(2),
                                                       adb("shell", "am", "start", "--windowingMode", "1", "-n", component))),
]
how, back = None, {}
for name, run in exits:
    run()
    back = wait_for(full_again, 10, f"full screen ({name})")
    if back and "error" not in back and full_again(back):
        how = name
        break
time.sleep(2)  # let the exit-split animation finish before the picture (round 4's was mid-transition)
shot("p12-full-again")
check("leaving split screen returns to the full window (same process)",
      how is not None and pid() == pid0,
      {"size": [back.get("innerW"), back.get("innerH")], "full": [full.get("innerW"), full.get("innerH")],
       "formFactor": back.get("formFactor"), "pid": pid(), "how": how})

# ── No crash in our process during all of this ──────────────────────────────
log = adb("logcat", "-d")
crash = [ln for ln in log.splitlines() if re.search(rf"AndroidRuntime: Process: {re.escape(PKG)}|Fatal signal .*\({re.escape(PKG)}\)|ANR in {re.escape(PKG)}", ln)]
check("no crash or ANR in the app", not crash, {"lines": crash[:5]})

with open(os.path.join(OUT, "platform.json"), "w") as f:
    json.dump(results, f, indent=2)
failed = [r["check"] for r in results if not r["pass"]]
print(f"{len(results) - len(failed)}/{len(results)} platform checks passed")
sys.exit(1 if failed else 0)
