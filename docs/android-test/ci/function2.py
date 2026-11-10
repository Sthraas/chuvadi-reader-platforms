#!/usr/bin/env python3
"""Function suite part 2 (test tooling only): markup + Save / Save as with the saved file checked,
form filling, box redaction (text really gone), tablet printing, fast typing in other fields.

    function2.py <out-dir> <fixtures-dir>
"""
import json
import os
import re
import sys
import time

from pypdf import PdfReader

from lib import Cdp, PKG, Results, adb, component, dismiss_system_dialogs, open_with, push_media, screencap, sh, ui_dump

OUT, FX = sys.argv[1], sys.argv[2]
R = Results(OUT, "function2")
cdp = Cdp()
COMP = component()
step = [0]

FIND = r"""((labels, sel) => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
     return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && r.bottom > 0 && r.top < innerHeight; };
  const pool = [...document.querySelectorAll(sel || 'button, a, [role=button], [role=tab], [role=menuitem], input, [title], [aria-label]')].filter(vis);
  for (const want of labels) { const w = want.toLowerCase();
    const hits = pool.filter(e => [e.getAttribute('aria-label'), e.getAttribute('title'), e.innerText, e.value]
        .some(t => t && t.trim().toLowerCase().replace(/\s+/g, ' ').startsWith(w)));
    hits.sort((a, b) => { const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); return ra.width * ra.height - rb.width * rb.height; });
    if (hits[0]) { const r = hits[0].getBoundingClientRect();
      return {label: want, text: (hits[0].getAttribute('aria-label') || hits[0].getAttribute('title') || hits[0].innerText || '').slice(0, 60),
              x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!hits[0].disabled}; } }
  return null; })(%s, %s)"""


def shot(name):
    step[0] += 1
    return screencap(os.path.join(OUT, f"{step[0]:02d}-{name}.png"))


def find(*labels, sel=None):
    return cdp.js(FIND % (json.dumps(list(labels)), json.dumps(sel)))


_wv = [None]


def webview_bounds():
    for _ in range(4):
        m = re.search(r'class="android.webkit.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', ui_dump())
        if m:
            _wv[0] = tuple(map(int, m.groups()))
            return _wv[0]
        time.sleep(1)
    return _wv[0] or (0, 0, 0, 0)


def to_screen(x, y):
    b = webview_bounds()
    d = cdp.js("devicePixelRatio")
    return int(b[0] + x * d), int(b[1] + y * d)


def tap(*labels, sel=None):
    hit = find(*labels, sel=sel)
    if hit:
        sx, sy = to_screen(hit["x"], hit["y"])
        sh(f"input tap {sx} {sy}")
        time.sleep(1)
    return hit


def type_slow(text):
    for ch in text:
        sh(f"input text {ch}")
        time.sleep(0.25)


PLOG = r"""(() => { if (window.__atlog) { window.__atlog.length = 0; return 'reset'; } window.__atlog = [];
  for (const t of ['pointerdown','pointermove','pointerup','pointercancel','touchstart','touchend','touchcancel','click','scroll'])
    document.addEventListener(t, e => { const l = window.__atlog; if (t.endsWith('move') && l.length && l[l.length-1].t === t) { l[l.length-1].n++; return; }
      l.push({t, n: 1, tgt: (e.target && e.target.className && e.target.className.baseVal !== undefined ? e.target.className.baseVal : (e.target.className || e.target.tagName || '')).toString().slice(0, 40),
              ta: e.target && e.target.nodeType === 1 ? getComputedStyle(e.target).touchAction : null}); }, {capture: true, passive: true});
  return 'installed'; })()"""


def plog_reset():
    cdp.js(PLOG)


def plog():
    return cdp.js("(window.__atlog || []).slice(0, 30)")


def ui_state():
    return cdp.js(r"""(() => ({ active: (() => { const a = document.activeElement; return a ? a.tagName + '.' + (a.className || '').toString().slice(0, 40) : null; })(),
      pressed: [...document.querySelectorAll('.ph-tool.on, .ph-tool[aria-pressed=true], .rb.on, .rb[aria-pressed=true], .rb.active')].map(e => e.getAttribute('aria-label') || e.title),
      boxes: (document.body.innerText.match(/(\d+) box/) || [])[1], editors: document.querySelectorAll('textarea, [contenteditable=true], input[type=text]').length,
      url: location.pathname }))()""")


def is_phone():
    return cdp.js("document.documentElement.getAttribute('data-shell')") == "phone"


def page_pt_to_css(page_index, x_pt, y_pt, w_pt=595.28, h_pt=841.89):
    r = cdp.js(f"(() => {{ const s = document.querySelectorAll('.rpage-wrap .rpage')[{page_index}]; const r = s.getBoundingClientRect();"
               f" return [r.left, r.top, r.width, r.height]; }})()")
    return r[0] + x_pt / w_pt * r[2], r[1] + (h_pt - y_pt) / h_pt * r[3]


def mode(name):
    return tap(name, sel=".ph-nav-b, .lb-btn, button")


def wait(expr, secs=30):
    return cdp.wait(expr, secs, 0.5)


def mark_time():
    sh("touch /data/local/tmp/at-mark")


def newest_pdf():
    rows = sh("find /storage/emulated/0/ -type f -name '*.pdf' -newer /data/local/tmp/at-mark 2>/dev/null")
    files = [l.strip() for l in rows.splitlines() if l.strip()]
    return files[-1] if files else None


def saf_save():
    """System 'save' picker (ACTION_CREATE_DOCUMENT): accept the suggested name in the current folder."""
    for _ in range(8):
        xml = ui_dump()
        if "com.google.android.documentsui" in xml or "com.android.documentsui" in xml:
            m = re.search(r'(?:text|content-desc)="(SAVE|Save)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
            if m:
                x1, y1, x2, y2 = map(int, m.groups()[1:])
                sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
                time.sleep(3)
                return True
        time.sleep(1)
    return False


def pull_text(remote, name):
    local = os.path.join(OUT, name)
    adb("pull", remote, local)
    try:
        r = PdfReader(local)
        return local, "\n".join((p.extract_text() or "") for p in r.pages), r
    except Exception as e:
        return local, f"<unreadable {e}>", None


def open_doc(fixture, as_name):
    uri = push_media(os.path.join(FX, fixture), as_name)
    open_with(uri)
    ok = wait(f"(() => {{ const t = (document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t') || {{}}).textContent || '';"
              f" return t.trim().startsWith('{as_name.split('.')[0]}') && document.querySelectorAll('.rpage svg').length > 0; }})()", 40)
    return uri, ok


sh(f"am start -W -n {COMP}")
cdp.connect(60)
wait("document.getElementById('app') && document.getElementById('app').children.length > 0", 60)
phone = is_phone()

# ── F-04 + F-09: text box markup, then Save (tablet: in place, write-back) / Save as new PDF (phone) ──
def case_0():
    global uri, ok, saved, txt, hit, tool, picker
    uri, ok = open_doc("doc-12p.pdf", "mark-doc.pdf")
    mode("Mark")
    time.sleep(1)
    tool = tap("Mark: Text", sel=".ph-tool") if phone else tap("Text", sel=".rb")
    after_tool = ui_state()
    shot("mark-tool-selected")
    plog_reset()
    x, y = page_pt_to_css(0, 300, 420)
    sx, sy = to_screen(x, y)
    sh(f"input tap {sx} {sy}")
    time.sleep(1.5)
    after_tap = ui_state()
    events = plog()
    shot("mark-page-tapped")
    # Same place, a slow tap (finger held 400 ms): if this makes a box and the quick tap didn't, the quick
    # tap's pointerup is arriving before MkDown has finished its awaited layer-rect read.
    x2_, y2_ = page_pt_to_css(0, 300, 560)
    s2x, s2y = to_screen(x2_, y2_)
    plog_reset()
    sh(f"input swipe {s2x} {s2y} {s2x} {s2y} 400")
    time.sleep(1.5)
    after_slow = ui_state()
    slow_events = plog()
    shot("mark-page-slow-tap")
    R.check("F-04b Mark › Text: quick finger tap behaves like a slow tap (both make a box)",
            bool(after_tap.get("editors")) == bool(after_slow.get("editors")),
            {"quick_tap": after_tap, "quick_events": events, "slow_tap": after_slow, "slow_events": slow_events})
    if not after_tap.get("editors") and after_slow.get("editors"):
        after_tap = after_slow
    typed = None
    if after_tap.get("active", "").split(".")[0] in ("TEXTAREA", "INPUT") or after_tap.get("editors"):
        type_slow("chuvadimark")
        time.sleep(1)
        typed = cdp.js("(() => { const a = document.activeElement; return a ? (a.value ?? a.innerText ?? '') : null; })()")
    if not (typed and "chuvadimark" in typed):
        sh("input keyevent KEYCODE_BACK")   # leave whatever a stray shortcut opened
        time.sleep(1.5)
        bx = cdp.js("(() => { const e = document.querySelector('textarea, [contenteditable=true]'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        second = None
        if bx:
            q = to_screen(bx[0], bx[1])
            sh(f"input tap {q[0]} {q[1]}")
            time.sleep(1.5)
            second = ui_state()
            if second.get("active", "").split(".")[0] in ("TEXTAREA", "INPUT"):
                type_slow("chuvadimark")
                time.sleep(1)
                typed = cdp.js("(() => { const a = document.activeElement; return a ? (a.value ?? a.innerText ?? '') : null; })()")
        R.check("F-04d Mark › Text: a second tap on the new box puts the caret in it and typing works", bool(typed and "chuvadimark" in typed),
                {"box": bx, "after_second_tap": second, "typed": (typed or "")[:40]})
        typed_first = None
    else:
        typed_first = typed
    shot("mark-text")
    typed_keep, typed = typed, typed_first
    R.check("F-04a Mark › Text: a finger tap on the page makes a text box; typing goes into it", bool(typed and "chuvadimark" in typed),
            {"tool": tool, "after_tool": after_tool, "after_tap": after_tap, "events": events, "typed": (typed or "")[:40]})
    typed = typed_keep
    sh("input keyevent KEYCODE_BACK")  # hide the keyboard
    time.sleep(1)
    mark_time()
    if phone:
        hit = tap("Save as new PDF", sel=".ph-fab")
    else:
        hit = tap("Save (Ctrl S)", "Save", sel=".rb, button")
    time.sleep(3)
    shot("after-save")
    picker = saf_save()
    time.sleep(3)
    saved = newest_pdf()
    txt = None
    if saved:
        _, txt, _ = pull_text(saved, "marked.pdf")
    R.check("F-09a Save writes a file containing the new text box", bool(saved and txt and "chuvadimark" in txt),
            {"button": hit, "picker": picker, "saved": saved, "has_text": bool(txt and "chuvadimark" in txt)})
    if not phone:
        _, orig_txt, _ = pull_text("/sdcard/Download/mark-doc.pdf", "mark-doc-original.pdf")
        R.check("F-09b tablet Save in place writes back to the file that was opened", "chuvadimark" in orig_txt,
                {"original_has_markup": "chuvadimark" in orig_txt, "saved_file": saved})


try:
    case_0()
except Exception as e:
    R.check('case 0 ran to the end (F-04 + F-09: text box markup, then)', False, {'error': repr(e)[:300]})
    shot('case-0-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

# ── F-04c shapes by drag (AT-15 scope)
def case_shapes():
    open_doc("doc-12p.pdf", "shape-doc.pdf")
    mode("Mark")
    time.sleep(1)
    tool = tap("Mark: Rectangle", "Box", sel=".ph-tool") if phone else tap("Rectangle", "Box", sel=".rb")
    x1, y1 = page_pt_to_css(0, 100, 500)
    x2, y2 = page_pt_to_css(0, 300, 350)
    a, b = to_screen(x1, y1), to_screen(x2, y2)
    plog_reset()
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    hdr = cdp.js("document.body.innerText.match(/(\\d+) shapes?/) || (document.body.innerText.match(/Rectangle\\s+p\\s*\\d+\\s*·\\s*(\\d+) of/) )")
    ev = plog()
    shot("shape-drag")
    R.check("F-04c Mark › Rectangle: a finger drag draws a shape", bool(hdr and hdr[1] != "0"), {"tool": tool, "count": hdr, "events": ev})


try:
    case_shapes()
except Exception as e:
    R.check("case shapes ran to the end", False, {"error": repr(e)[:300]})
    cdp.close()

# ── Fast typing in the Mark text box (AT-10 scope) ──
def case_1():
    global uri, ok, saved, txt, hit, tool, picker
    mode("Mark")
    tap("Mark: Text", "Text", sel=".ph-tool, .rb, button")
    x, y = page_pt_to_css(0, 300, 300)
    sx, sy = to_screen(x, y)
    sh(f"input tap {sx} {sy}")
    time.sleep(1.5)
    if not (ui_state().get("active", "").split(".")[0] in ("TEXTAREA", "INPUT")):
        sh("input keyevent KEYCODE_ESCAPE")
    sh("input text burstwordtest")
    time.sleep(1.5)
    burst = cdp.js("(() => { const a = document.activeElement; return a ? (a.value ?? a.innerText ?? '') : null; })()")
    R.check("F-03c fast typing into a Mark text box keeps every character", burst and "burstwordtest" in burst, {"got": burst})
    sh("input keyevent KEYCODE_BACK")
    cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")


try:
    case_1()
except Exception as e:
    R.check('case 1 ran to the end (Fast typing in the Mark text box (A)', False, {'error': repr(e)[:300]})
    shot('case-1-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

# ── Library search box (AT-10 scope) ──
def case_2():
    global uri, ok, saved, txt, hit, tool, picker
    cdp.js("Blazor.navigateTo('/library')")
    time.sleep(2)
    f = cdp.js(r"""(() => { const i = [...document.querySelectorAll('input')].find(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.type !== 'checkbox'; });
      if (!i) return null; const r = i.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, ph: i.placeholder, label: i.getAttribute('aria-label')}; })()""")
    if f:
        sx, sy = to_screen(f["x"], f["y"])
        sh(f"input tap {sx} {sy}")
        time.sleep(1.2)
        sh("input text burstwordtest")
        time.sleep(1.5)
    lib = cdp.js("(() => { const a = document.activeElement; return a && a.tagName === 'INPUT' ? a.value : null; })()")
    R.check("F-03d fast typing into the Library search keeps every character", lib == "burstwordtest", {"got": lib, "field": f})
    sh("input keyevent KEYCODE_BACK")


try:
    case_2()
except Exception as e:
    R.check('case 2 ran to the end (Library search box (AT-10 scope) ──)', False, {'error': repr(e)[:300]})
    shot('case-2-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

# ── F-06 forms: fill the text field, save, value in the saved file ──
def case_3():
    global uri, ok, saved, txt, hit, tool, picker
    uri, ok = open_doc("form.pdf", "form-fill.pdf")
    mode("Read")
    x, y = page_pt_to_css(0, 285, 781)
    sx, sy = to_screen(x, y)
    sh(f"input tap {sx} {sy}")
    time.sleep(1.5)
    type_slow("Ravi")
    time.sleep(1)
    shot("form-typed")
    sh("input keyevent KEYCODE_BACK")
    time.sleep(1)
    mark_time()
    hit = tap("Save as new PDF", "Save (Ctrl S)", "Save", sel=".ph-fab, .rb, button")
    time.sleep(2)
    saf_save()
    time.sleep(3)
    saved = newest_pdf() or ("/sdcard/Download/form-fill.pdf" if not phone else None)
    val = None
    if saved:
        _, _, r = pull_text(saved, "form-filled.pdf")
        try:
            val = (r.get_fields() or {}).get("patient", {}).get("/V") if r else None
        except Exception as e:
            val = f"<{e}>"
    R.check("F-06 form text field filled by touch is saved", val == "Ravi", {"button": hit, "saved": saved, "value": val})


try:
    case_3()
except Exception as e:
    R.check('case 3 ran to the end (F-06 forms: fill the text field, sa)', False, {'error': repr(e)[:300]})
    shot('case-3-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

# ── F-07 box redaction: draw a box over page 1's heading, save the redacted copy, the text is gone ──
def case_4():
    global uri, ok, saved, txt, hit, tool, picker
    uri, ok = open_doc("doc-12p.pdf", "redact-doc.pdf")
    mode("Protect")
    time.sleep(1)
    tool = tap("Protect: Box", "Protect: Redact", "Redact box", "Box", sel=".ph-tool") if phone else tap("Redact box", sel=".rb")
    x1, y1 = page_pt_to_css(0, 50, 760)
    x2, y2 = page_pt_to_css(0, 400, 740)
    a = to_screen(x1, y1)
    b = to_screen(x2, y2)
    before = ui_state()
    plog_reset()
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    after_swipe = ui_state()
    ev1 = plog()
    shot("redact-swipe")
    plog_reset()
    if str(after_swipe.get("boxes")) in ("0", "None"):
        import subprocess
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "touch.py"), "longdrag", str(a[0]), str(a[1]), str(b[0]), str(b[1])], timeout=60)
        time.sleep(1.5)
    after_long = ui_state()
    ev2 = plog()
    shot("redact-box")
    R.check("F-07a Protect › Box: a finger drag on the page draws a redaction box",
            str(after_swipe.get("boxes")) not in ("0", "None") or str(after_long.get("boxes")) not in ("0", "None"),
            {"before": before, "after_swipe": after_swipe, "swipe_events": ev1, "after_longdrag": after_long, "longdrag_events": ev2})
    mark_time()
    hit = tap("Save redacted copy", "Apply redaction", "Redact and save", "Save as new PDF", "Save", sel=".ph-fab, .rb, button, .chvd-card button")
    time.sleep(2)
    shot("redact-save")
    xml = ui_dump()
    saf_save()
    time.sleep(4)
    saved = newest_pdf()
    gone = None
    if saved:
        _, txt, _ = pull_text(saved, "redacted.pdf")
        first = txt.split("Discharge summary - page 2")[0] if txt else ""
        gone = {"heading_page1_present": "page 1" in first.split("\n")[0:3].__str__(), "first_200": first[:200]}
    R.check("F-07 redacted copy saved and page 1's heading text is gone from it",
            bool(saved and gone and "Discharge summary - page 1" not in (txt or "")),
            {"tool": tool, "button": hit, "saved": saved, "check": gone})


try:
    case_4()
except Exception as e:
    R.check('case 4 ran to the end (F-07 box redaction: draw a box over)', False, {'error': repr(e)[:300]})
    shot('case-4-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

# ── F-11 tablet printing: Print card's own Print button ──
def case_5():
    global uri, ok, saved, txt, hit, tool, picker
    uri, ok = open_doc("doc-12p.pdf", "print-doc.pdf")
    if phone:
        tap("More", sel=".ph-ib")
        time.sleep(1)
        tap("Print", sel=".ph-sheet *")
    else:
        tap("Print", "Print (Ctrl P)", sel=".rb, .lb-btn, button")
    time.sleep(2)
    card = cdp.js("[...document.querySelectorAll('section.chvd-card button, .chvd-card button')].filter(b => b.getBoundingClientRect().width > 0)"
                  ".map(b => (b.innerText || b.getAttribute('aria-label') || '').trim())")
    shot("print-card")
    btn = None
    for sel in ("section.chvd-card .footer button", ".chvd-card footer button", ".chvd-card button.primary", ".chvd-card button"):
        btn = find("Print", sel=sel)
        if btn and not btn["disabled"]:
            break
    if btn:
        sx, sy = to_screen(btn["x"], btn["y"])
        sh(f"input tap {sx} {sy}")
    time.sleep(5)
    xml = ui_dump()
    R.check(f"F-11d print card opens Android's print dialog ({'phone' if phone else 'tablet'})", "com.android.printspooler" in xml,
            {"card_buttons": card, "button": btn})
    shot("print-dialog")
    sh("input keyevent KEYCODE_BACK")
    time.sleep(2)


try:
    case_5()
except Exception as e:
    R.check('case 5 ran to the end (F-11 tablet printing: Print card)', False, {'error': repr(e)[:300]})
    shot('case-5-error')
    cdp.close()
    sh('input keyevent KEYCODE_BACK')

log = adb("logcat", "-d", "-v", "epoch")
fatal = [l for l in log.splitlines() if "FATAL EXCEPTION" in l or f"ANR in {PKG}" in l]
R.check("R-10 no crash / ANR in function part 2", not fatal, fatal[:5])
