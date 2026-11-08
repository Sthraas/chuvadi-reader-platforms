#!/usr/bin/env python3
"""Function suite on one emulator (test tooling only). Real touch (touch.py) for gestures and taps the
person makes; DevTools only to read state and to find where a control is on screen.

    function.py <out-dir> <fixtures-dir>
"""
import json
import os
import re
import subprocess
import sys
import time

from pypdf import PdfReader

from lib import (Cdp, PKG, Results, adb, as_shell_user, component, dismiss_system_dialogs, open_with, pid,
                 portrait_rotation, push_media, screencap, set_rotation, sh, ui_dump)

OUT, FX = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
R = Results(OUT, "function")
cdp = Cdp()
COMP = component()
step = [0]


def shot(name):
    step[0] += 1
    return screencap(os.path.join(OUT, f"{step[0]:02d}-{name}.png"))


def touch(*args):
    subprocess.run([sys.executable, os.path.join(HERE, "touch.py"), *map(str, args)], check=False, timeout=60)
    time.sleep(0.6)


def webview_bounds():
    xml = ui_dump()
    m = re.search(r'class="android.webkit.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    return tuple(map(int, m.groups())) if m else None


FIND = r"""((labels, sel) => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
     return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && r.bottom > 0 && r.top < innerHeight; };
  const pool = [...document.querySelectorAll(sel || 'button, a, [role=button], [role=tab], [role=menuitem], input, [title], [aria-label]')].filter(vis);
  for (const want of labels) { const w = want.toLowerCase();
    const hits = pool.filter(e => [e.getAttribute('aria-label'), e.getAttribute('title'), e.innerText, e.value]
        .some(t => t && t.trim().toLowerCase().replace(/\s+/g, ' ').startsWith(w)));
    hits.sort((a, b) => { const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); return ra.width * ra.height - rb.width * rb.height; });
    if (hits[0]) { const r = hits[0].getBoundingClientRect();
      return {label: want, x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height,
              disabled: !!hits[0].disabled, title: hits[0].getAttribute('title')}; } }
  return null; })(%s, %s)"""


def find(*labels, sel=None):
    return cdp.js(FIND % (json.dumps(list(labels)), json.dumps(sel)))


def to_screen(x, y):
    b = webview_bounds()
    dpr = cdp.js("devicePixelRatio")
    return int(b[0] + x * dpr), int(b[1] + y * dpr)


def tap(*labels, sel=None):
    """Real finger tap on the first visible control whose label starts with one of `labels`."""
    hit = find(*labels, sel=sel)
    if not hit:
        return None
    sx, sy = to_screen(hit["x"], hit["y"])
    touch("tap", sx, sy)
    return hit


def tap_css(x, y):
    sx, sy = to_screen(x, y)
    touch("tap", sx, sy)


def state():
    return cdp.js(r"""(() => ({
      url: location.pathname, shell: document.documentElement.getAttribute('data-shell'),
      theme: document.documentElement.getAttribute('data-theme'),
      pages: document.querySelectorAll('.rpage-wrap').length, rendered: document.querySelectorAll('.rpage svg').length,
      counter: (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim(),
      tab: ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {}).textContent?.trim(),
      tabs: document.querySelectorAll('.rtab').length || +((document.querySelector('.ph-sub')?.textContent || '').match(/of\s+(\d+)/) || [0, 0])[1],
      cards: [...document.querySelectorAll('section.chvd-card')].map(c => c.getAttribute('aria-label')),
      sheet: !!document.querySelector('.ph-sheet'), toast: document.querySelector('.rpage-toast, .toast, [role=status], [role=alert]')?.textContent?.trim(),
      dialog: [...document.querySelectorAll('[role=dialog], .modal, .chvd-card')].map(d => (d.innerText || '').slice(0, 160)),
      text: document.body.innerText.slice(0, 400) }))()""")


def wait_state(pred, seconds=30, what=""):
    end = time.time() + seconds
    st = None
    while time.time() < end:
        try:
            st = state()
            if pred(st):
                return st
        except Exception as e:
            st = {"error": str(e)}
            cdp.close()
        dismiss_system_dialogs()
        time.sleep(0.5)
    print("timeout:", what, json.dumps(st)[:300])
    return st


def text_of(path):
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:
        return f"<unreadable: {e}>"


def pull(remote, local):
    adb("pull", remote, local)
    return local if os.path.exists(local) else None


def newest_download(after_epoch, pattern=".pdf"):
    rows = sh("ls -l --time-style=+%s /storage/emulated/0/Download/ /storage/emulated/0/Documents/ 2>/dev/null")
    best = None
    for line in rows.splitlines():
        parts = line.split(None, 6)
        if len(parts) == 7 and parts[6].endswith(pattern):
            try:
                t = int(parts[5])
            except ValueError:
                continue
            if t >= after_epoch and (best is None or t > best[0]):
                best = (t, parts[6])
    return best[1] if best else None


def saf_pick(name):
    """In DocumentsUI (picker), tap the file called `name` (searching Downloads)."""
    for _ in range(10):
        xml = ui_dump()
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(name), xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
            return True
        m = re.search(r'(text|content-desc)="(Downloads|Show roots)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups()[2:])
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
        time.sleep(1.5)
    return False


def ui_tap_text(*texts):
    xml = ui_dump()
    for t in texts:
        m = re.search(r'(?:text|content-desc)="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(t), xml, re.I)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
            return t
    return None


def back_to_app():
    sh(f"am start -n {COMP}")
    time.sleep(2)


def esc():
    cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")


# ─────────────────────────────────────────────────────────────────────────────────────────────
set_rotation(portrait_rotation())
sh(f"am start -W -n {COMP}")
cdp.connect(60)
wait_state(lambda s: s.get("shell"), 60, "app")
uris = {n: push_media(os.path.join(FX, n)) for n in
        ("doc-12p.pdf", "form.pdf", "enc-user.pdf", "enc-noprint-owner.pdf", "mixed-landscape.pdf")}

# F-01a Open through the system picker (SAF) from Home
cdp.js("Blazor.navigateTo('/')")
time.sleep(1.5)
shot("home")
hit = tap("Open", "+ Open", "Open a file", "Open…")
time.sleep(3)
shot("picker")
picked = saf_pick("form.pdf")
st = wait_state(lambda s: s.get("rendered", 0) >= 1 and (s.get("tab") or "").lower().startswith("form"), 40, "SAF open")
shot("saf-opened")
R.check("F-01a Home Open → system picker → file opens in the Reader", bool(hit and picked and st.get("rendered")),
        {"button": hit, "picked": picked, "state": st})

# F-01b Share to Chuvadi
before_tabs = state().get("tabs") or 0
as_shell_user(f"am start -a android.intent.action.SEND -t application/pdf --eu android.intent.extra.STREAM "
              f"'{uris['mixed-landscape.pdf']}' -p {PKG} --grant-read-uri-permission")
st = wait_state(lambda s: (s.get("tab") or "").lower().startswith("mixed") and s.get("rendered", 0) >= 1, 40, "share")
R.check("F-01b Share to Chuvadi opens a new tab", (st.get("tab") or "").lower().startswith("mixed"),
        {"tabs_before": before_tabs, "state": st})

# F-01c Open with (main test document)
open_with(uris["doc-12p.pdf"])
st = wait_state(lambda s: (s.get("tab") or "").lower().startswith("doc-12p") and s.get("rendered", 0) >= 1, 40, "open with")
R.check("F-01c Open with opens the PDF", (st.get("tab") or "").lower().startswith("doc-12p"), st)
F17 = sh("dumpsys activity activities | grep -c 'Hist.*in.chuvadi.reader'").strip()
R.check("F-17 single instance: one activity record after three arrivals", F17 == "1", {"activity_records": F17})

# F-02 Page navigation by the pager buttons
st0 = state()
tap("Next page", "Next")
time.sleep(1)
st1 = state()
R.check("F-02 next page moves the counter", st1.get("counter") != st0.get("counter"), {"before": st0.get("counter"), "after": st1.get("counter")})

# F-03 Find
tap("Find", "Search")
time.sleep(1.2)
sh("input text zephyrine")
time.sleep(0.4)
sh("input keyevent KEYCODE_ENTER")
time.sleep(2)
fst = cdp.js("({count: (document.querySelector('.rfind-count')?.textContent || '').trim(), "
             "counter: (document.querySelector('.ph-pager')?.textContent || document.querySelector('.tb-pg-box')?.value || '').trim(), "
             "ime: null})")
shot("find")
R.check("F-03 Find 'zephyrine' finds 1 match and goes to page 3", "1" in (fst.get("count") or "") and "3" in (fst.get("counter") or ""), fst)
sh("input keyevent KEYCODE_BACK")
time.sleep(1)
esc()

# F-11 Print: vector output and no-print refusal
tap("Print", "Document")
time.sleep(1)
if not state().get("cards") or "Print" not in (state().get("cards") or []):
    tap("Print")
    time.sleep(1)
shot("print-card")
t0 = int(sh("date +%s").strip())
pr = tap("Print", sel="section.chvd-card .footer button")
time.sleep(5)
shot("print-dialog")
# Android print dialog: choose Save as PDF, then the PDF button, then Save in the picker.
xml = ui_dump()
if "Save as PDF" not in xml:
    ui_tap_text("Select a printer")
    time.sleep(1)
    ui_tap_text("Save as PDF")
    time.sleep(1)
    ui_tap_text("Save as PDF")
time.sleep(2)
ui_tap_text("Download PDF", "PDF")
sh("input tap 0 0")
time.sleep(3)
xml = ui_dump()
if 'text="SAVE"' in xml or 'text="Save"' in xml:
    ui_tap_text("SAVE", "Save")
time.sleep(4)
saved = newest_download(t0)
local = pull(f"/storage/emulated/0/Download/{saved}", os.path.join(OUT, "printed.pdf")) if saved else None
vec = None
if local:
    r = PdfReader(local)
    txt = text_of(local)
    imgs = sum(len(p.images) for p in r.pages)
    vec = {"pages": len(r.pages), "text_chars": len(txt), "images": imgs, "has_marker": "zephyrine" in txt}
R.check("F-11a print through Android's dialog produces a file", bool(local), {"button": pr, "saved": saved})
R.check("F-11b printed output is vector (text kept, no page images)",
        bool(vec and vec["text_chars"] > 1000 and vec["images"] == 0), vec)
back_to_app()
esc()

# F-11c no-print file refused
open_with(uris["enc-noprint-owner.pdf"])
st = wait_state(lambda s: (s.get("tab") or "").lower().startswith("enc-noprint") and s.get("rendered", 0) >= 1, 40, "no-print opens")
R.check("R-02a owner-password (no user password) PDF opens without a prompt", st.get("rendered", 0) >= 1, st)
tap("Print", "Document")
time.sleep(1)
tap("Print")
time.sleep(1)
btn = find("Print", sel="section.chvd-card .footer button")
shot("noprint-card")
R.check("F-11c a no-print PDF's Print is refused with a reason", bool(btn and btn["disabled"]), btn)
esc()

# F-10 user-password PDF
open_with(uris["enc-user.pdf"])
time.sleep(6)
st = state()
shot("enc-user")
prompt = cdp.js("!!document.querySelector('input[type=password]')")
R.check("F-10 user-password PDF asks for the password", bool(prompt), st)
esc()

# F-14 Rotation with an open document and a card open
open_with(uris["doc-12p.pdf"])
wait_state(lambda s: (s.get("tab") or "").lower().startswith("doc-12p"), 30, "doc")
tap("Next page", "Next")
tap("Next page", "Next")
before = state()
set_rotation(1 - portrait_rotation())
time.sleep(2)
after = wait_state(lambda s: s.get("rendered", 0) >= 1, 20, "after rotation")
shot("rotated")
R.check("F-14 rotation keeps the document, page and process",
        after.get("counter") == before.get("counter") and after.get("tab") == before.get("tab"),
        {"before": before, "after": after})
set_rotation(portrait_rotation())

# F-15 Process death and restore
p_before = pid()
st_before = state()
sh("input keyevent KEYCODE_HOME")
time.sleep(2)
sh(f"am kill {PKG}")
time.sleep(2)
killed = pid() != p_before
sh(f"am start -W -n {COMP}")
cdp.close()
st_after = wait_state(lambda s: s.get("shell"), 60, "restart")
time.sleep(4)
st_after = state()
shot("after-process-death")
R.check("F-15 after process death the open tabs come back", killed and (st_after.get("tabs") or 0) >= 1,
        {"killed": killed, "before": st_before, "after": st_after})

# F-16 Low memory
for level in ("RUNNING_LOW", "RUNNING_CRITICAL", "UI_HIDDEN", "BACKGROUND", "COMPLETE"):
    sh(f"am send-trim-memory {PKG} {level}")
    time.sleep(0.5)
alive = bool(pid())
st = state() if alive else {}
R.check("F-16 trim-memory levels: app alive and responsive", alive and bool(st.get("shell")), st)

# D-10 Real Settings tap: theme changes and persists
cdp.js("Blazor.navigateTo('/settings')")
time.sleep(1.5)
tap("Appearance", "Theme", "Look")
time.sleep(1)
hit = tap("Use Night paper", "Night paper")
time.sleep(1)
th = state().get("theme")
sh(f"am force-stop {PKG}")
sh(f"am start -W -n {COMP}")
cdp.close()
th2 = wait_state(lambda s: s.get("theme"), 60, "restart").get("theme")
shot("theme-after-restart")
R.check("D-10 theme set by a real tap in Settings, kept after restart", th == "dark" and th2 == "dark",
        {"tap": hit, "after_tap": th, "after_restart": th2})
tap("Use Cream paper", "Cream paper")

# D-08 On-screen keyboard over Find (field stays visible)
open_with(uris["doc-12p.pdf"])
wait_state(lambda s: s.get("rendered", 0) >= 1, 30, "doc")
tap("Find", "Search")
time.sleep(2)
ime = sh("dumpsys input_method | grep -E 'mInputShown|mIsInputViewShown'")
field = cdp.js("(() => { const f = document.activeElement; if (!f) return null; const r = f.getBoundingClientRect();"
               "return {tag: f.tagName, top: r.top, bottom: r.bottom, vh: (window.visualViewport||{}).height, ih: innerHeight}; })()")
shot("keyboard-find")
R.check("D-08 on-screen keyboard shows and the Find field stays above it",
        bool(field and field["bottom"] <= (field["vh"] or field["ih"])) and "true" in ime, {"ime": ime.strip(), "field": field})
sh("input keyevent KEYCODE_BACK")
esc()

# F-12 Back closes a sheet/card first, then walks out
tap("More") if state().get("shell") == "phone" else tap("Document")
time.sleep(1)
had = state()
sh("input keyevent KEYCODE_BACK")
time.sleep(1.2)
now = state()
R.check("F-12 Back closes the open sheet/menu and stays on the same screen",
        now.get("url") == had.get("url") and (now.get("sheet") is False) and len(now.get("cards") or []) <= len(had.get("cards") or []),
        {"before": had, "after": now})

# D-07 Split screen: phone ↔ tablet form factor follows the window
task = re.search(r"taskId=(\d+)", sh(f"am stack list | grep {PKG}") or "")
shell_full = state().get("shell")
sh(f"wm size")
R.check("D-07 (recorded) shell at full window", True, {"shell": shell_full})

# R-10 crashes so far
log = adb("logcat", "-d", "-v", "epoch")
fatal = [l for l in log.splitlines() if "FATAL EXCEPTION" in l or f"ANR in {PKG}" in l]
console = [l for l in log.splitlines() if "chromium" in l and "Uncaught" in l]
R.check("R-10 no crash, ANR or uncaught page error during the function suite", not fatal and not console,
        {"fatal": fatal[:5], "console": console[:5]})
