#!/usr/bin/env python3
"""Save suite (test tooling only): every case opens a WRITABLE file through the system picker (the
grant a person's own pick gives), changes it by touch, saves, and reads the saved file back.

  SV-1 text box → Save (in place where offered) and Save as new PDF; text present; original untouched by Save as
  SV-2 rectangle → Save as; the saved page carries the new mark
  SV-3 a filled form: values shown stay in the saved file (the Reader has no "Fill form" tool yet — greyed on Windows too)
  SV-4 redaction box → Save redacted copy; the covered text is gone from the file, the rest stays
  SV-5 Arrange: long-press drag two pages to a desk, reorder, bind; saved pages in the desk's order
  SV-6 print → Android dialog → PDF: vector

    saves.py <out-dir> <fixtures-dir>
"""
import json
import os
import re
import subprocess
import sys
import time

from pypdf import PdfReader

from lib import Cdp, PKG, Results, adb, component, dismiss_system_dialogs, portrait_rotation, screencap, set_rotation, sh, ui_dump

OUT, FX = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
R = Results(OUT, "saves")
cdp = Cdp()
COMP = component()
n = [0]
_wv = [None]


def shot(name):
    n[0] += 1
    dismiss_system_dialogs()
    return screencap(os.path.join(OUT, f"{n[0]:02d}-{name}.png"))


def wv(fresh=False):
    if _wv[0] and not fresh:
        return _wv[0]
    for _ in range(4):
        m = re.search(r'class="android.webkit.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', ui_dump())
        if m:
            _wv[0] = tuple(map(int, m.groups()))
            return _wv[0]
        time.sleep(1)
    return _wv[0] or (0, 0, 0, 0)


def to_screen(x, y):
    b = wv()
    d = cdp.js("devicePixelRatio")
    return int(b[0] + x * d), int(b[1] + y * d)


VIS = "const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && r.bottom > 0 && r.top < innerHeight; };"
FIND = "((labels, sel) => { " + VIS + r"""
  const name = e => [e.getAttribute('aria-label'), e.getAttribute('title'), e.innerText, e.value].filter(t => t).map(t => t.trim().toLowerCase().replace(/\s+/g, ' '));
  const pool = [...document.querySelectorAll(sel || 'button, a, [role=button], [role=tab], [role=menuitem]')].filter(vis);
  for (const want of labels) { const w = want.toLowerCase();
    const hits = pool.filter(e => name(e).some(t => t.startsWith(w)));
    hits.sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height);
    if (hits[0]) { const r = hits[0].getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return {label: want, text: name(hits[0])[0], x: cx, y: cy, disabled: !!hits[0].disabled, covered: !(top === hits[0] || hits[0].contains(top) || (top && top.contains(hits[0])))}; } }
  return null; })(%s, %s)"""
LABELS = "(() => { " + VIS + " return [...document.querySelectorAll('button, [role=button]')].filter(vis).map(e => (e.getAttribute('aria-label') || e.getAttribute('title') || e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 30)).filter(t => t); })()"


def find(*labels, sel=None):
    return cdp.js(FIND % (json.dumps(list(labels)), json.dumps(sel)))


def labels():
    try:
        return cdp.js(LABELS)[:60]
    except Exception:
        return None


def tap(*names, sel=None):
    """Finger tap on a control; if a sheet or card covers it, close that by its own Close control and try again."""
    hit = None
    for attempt in range(3):
        hit = find(*names, sel=sel)
        if not hit:
            return None
        if hit["covered"] and attempt < 2:
            c = cdp.js("(() => { " + VIS + " const e = [...document.querySelectorAll('.fcard [aria-label^=Close], .fcard [title^=Close], .fcard .fcard-x, .ph-handle, .ph-sheet-a, .ph-sheet [aria-label=Close], .chvd-card [aria-label=Close], .mk-card [aria-label=Close], .ph-scrim')].find(vis);"
                       " if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
            if c:
                q = to_screen(c[0], c[1])
                sh(f"input tap {q[0]} {q[1]}")
            else:
                cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
            time.sleep(1.2)
            continue
        if hit["covered"]:
            hit["cover_controls"] = cdp.js(f"(() => {{ const t = document.elementFromPoint({hit['x']}, {hit['y']}); const c = t && t.closest('section, [role=dialog]'); return c ? [...c.querySelectorAll('button')].map(b => (b.getAttribute('aria-label') || b.title || b.innerText || '').trim().slice(0, 24)) : null; }})()")
            hit["covered_by"] = cdp.js(f"(() => {{ const t = document.elementFromPoint({hit['x']}, {hit['y']}); if (!t) return null; const c = t.closest('section, [role=dialog], .ph-sheet, .chvd-card') || t; return (c.tagName + '.' + (c.className || '')).toString().slice(0, 80) + ' / ' + (c.getAttribute('aria-label') || ''); }})()")
        sx, sy = to_screen(hit["x"], hit["y"])
        sh(f"input tap {sx} {sy}")
        time.sleep(1.2)
        return hit
    return hit


def tap_xy(x, y):
    sx, sy = to_screen(x, y)
    sh(f"input tap {sx} {sy}")
    time.sleep(1.2)


def touch(*args):
    subprocess.run([sys.executable, os.path.join(HERE, "touch.py"), *map(str, args)], check=False, timeout=60)
    time.sleep(1)


def longdrag(a, b, changed):
    """Long-press and drag a → b. Android's own `input draganddrop` first (rotation-aware); the raw
    touch script as a second way if `changed()` says nothing moved."""
    touch("longdrag", a[0], a[1], b[0], b[1], 800, 1200)     # rotation-aware since round 11 (the Android chat's fix)
    time.sleep(1)
    if changed():
        return "touch.py longdrag"
    sh(f"input draganddrop {a[0]} {a[1]} {b[0]} {b[1]} 1500")
    time.sleep(1.5)
    return "input draganddrop" if changed() else "neither moved it"


def phone():
    return cdp.js("document.documentElement.getAttribute('data-shell')") == "phone"


def page_pt(page_index, x_pt, y_pt, w_pt=595.28, h_pt=841.89):
    r = cdp.js(f"(() => {{ const s = [...document.querySelectorAll('.rpage-wrap .rpage, .rd-page, .rpage')].filter(e => e.getBoundingClientRect().width > 0)[{page_index}];"
               f" const r = s.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }})()")
    return r[0] + x_pt / w_pt * r[2], r[1] + (h_pt - y_pt) / h_pt * r[3]


def ui_tap_text(*texts):
    xml = ui_dump()
    for t in texts:
        m = re.search(r'(?:text|content-desc)="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(t), xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
            return t
    return None


def in_picker():
    return "documentsui" in ui_dump()


def picker_choose(name, tries=22):
    """In Android's picker: Downloads, list view (full names), scroll to the file, tap it."""
    seen, went = [], 0
    for _ in range(tries):
        xml = ui_dump()
        if "documentsui" not in xml:
            seen.append("not the picker")
            time.sleep(1.5)
            continue
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(name), xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
            return True, seen
        seen.append(sorted(set(re.findall(r'text="((?:sv-|at-)[^"]+)"', xml)))[:10])
        if "Files in Downloads" not in xml and went < 3:
            went += 1                                   # the picker reopens in the last folder used (e.g. at-bind)
            ui_tap_text("Show roots")
            time.sleep(1.2)
            ui_tap_text("Downloads", "Download")
        elif ui_tap_text("List view"):
            pass                                        # the grid cuts long names short
        else:
            w, h = map(int, re.findall(r"(\d+)x(\d+)", sh("wm size"))[-1])
            if h < w and portrait_rotation() == 1:
                w, h = h, w
            sh(f"input swipe {w // 2} {int(h * 0.75)} {w // 2} {int(h * 0.4)} 300")
        time.sleep(1.5)
    return False, seen


def pick_open(name):
    r = _pick_open(name)
    if not r["opened"]:
        shot("pick-retry")
        if in_picker():
            sh("input keyevent KEYCODE_BACK")
            time.sleep(1)
        r = _pick_open(name)
        r["second_try"] = True
    return r


def _pick_open(name):
    """Home › Open → system picker → the file. The picker's grant is read + write, as for a person."""
    cdp.js("Blazor.navigateTo('/')")
    time.sleep(1.5)
    hit = tap("Open a document", sel=".ph-fab") if phone() else tap("Choose a document to open", "Open (Ctrl O)", "Open")
    time.sleep(2.5)
    ok, seen = picker_choose(name)
    if not ok:
        shot("picker-file-not-found")
    if not ok and in_picker():
        sh("input keyevent KEYCODE_BACK")
    stem = name.rsplit(".", 1)[0]
    opened = cdp.wait(f"(() => {{ const t = ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {{}}).textContent || '';"
                      f" return t.trim().startsWith('{stem}') && document.querySelectorAll('.rpage svg').length > 0; }})()", 40)
    return {"button": hit, "picked": ok, "opened": bool(opened), "picker_showed": None if ok else seen[-4:]}


def push(fixture, name):
    adb("push", os.path.join(FX, fixture), f"/sdcard/Download/{name}")
    sh(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file:///sdcard/Download/{name}' >/dev/null")
    return sh(f"md5sum /sdcard/Download/{name}").split()[0]


def md5(name):
    return (sh(f"md5sum '/sdcard/Download/{name}'").split() or [None])[0]


def mark_time():
    sh("touch /data/local/tmp/at-mark")
    time.sleep(1.1)


def new_pdfs():
    rows = sh("find /storage/emulated/0/ -type f -name '*.pdf' -newer /data/local/tmp/at-mark 2>/dev/null")
    return [l.strip() for l in rows.splitlines() if l.strip()]


def save_picker(as_name=None, tries=22):
    """ACTION_CREATE_DOCUMENT picker (waits up to ~30 s for it): go to Downloads if asked, accept the suggested name."""
    for _ in range(tries):
        xml = ui_dump()
        if "documentsui" in xml:
            m = re.search(r'(?:text|content-desc)="(SAVE|Save)"[^>]*enabled="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
            if m:
                x1, y1, x2, y2 = map(int, m.groups()[1:])
                sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
                time.sleep(4)
                return True
            ui_tap_text("Downloads") or ui_tap_text("Show roots")
        time.sleep(1.2)
    return False


def read(path, local):
    lp = os.path.join(OUT, local)
    adb("pull", path, lp)
    try:
        r = PdfReader(lp)
        return r, [(p.extract_text() or "") for p in r.pages]
    except Exception as e:
        return None, [f"<unreadable: {e}>"]


def mode(name):
    return tap(name, sel=".ph-nav-b, .lb-btn")


def tool(*names):
    return tap(*names, sel=".ph-tool") if phone() else tap(*names, sel=".rb")


def save_as():
    """Save as new PDF → picker → the new file's path."""
    mark_time()
    put_away = None
    card_up = bool(cdp.js(FCARD)) if phone() else None
    pre = find("Save as new PDF", "Save as", sel=".ph-fab, .rb, .ph-row, button")
    if phone() and card_up and (not pre or pre.get("covered")):
        put_away = card_away()
    hit = tap("Save as new PDF", "Save as", sel=".ph-fab, .rb, .ph-row, button")
    if not hit and phone():
        tap("More", sel=".ph-ib")
        hit = tap("Save as new PDF", "Save as", sel=".ph-sheet *")
    time.sleep(2)
    picker = save_picker()
    time.sleep(2)
    files = new_pdfs()
    return {"button": hit, "picker": picker, "files": files, "app_says": says(), "mark_card_up": card_up, "save_reachable_with_card_up": bool(pre and not pre.get("covered")) if card_up else None, "mark_card_put_away_by": put_away}


FCARD = "(() => { " + VIS + " const e = [...document.querySelectorAll('.fcard')].find(vis); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()"


def card_away():
    """Phone: a selected mark's property card sits over the Save button. Put it away the ways a person would try."""
    c = cdp.js(FCARD)
    if not c:
        return "no card"
    a = to_screen(c[0] + c[2] / 2, c[1] + 14)
    b = to_screen(c[0] + c[2] / 2, c[1] + c[3] - 10)
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 300")
    time.sleep(1.2)
    if not cdp.js(FCARD):
        return "swipe down on the card"
    r = cdp.js("(() => { const e = [...document.querySelectorAll('.rpage-wrap .rpage')].filter(e => e.getBoundingClientRect().width > 0)[0].getBoundingClientRect(); return [e.left, e.top, e.width, e.height]; })()")
    q = to_screen(r[0] + r[2] * 0.92, max(r[1], 0) + 70)
    sh(f"input tap {q[0]} {q[1]}")
    time.sleep(1.2)
    if not cdp.js(FCARD):
        return "tap on an empty part of the page"
    return "nothing put it away (swipe down on it, tap on the page)"


def says():
    """Any message the app is showing (toast / status / alert), for the record."""
    try:
        return cdp.js("[...document.querySelectorAll('.toast, [role=status], [role=alert], .rpage-toast, .bench-status-open')].map(e => (e.innerText || '').trim()).filter(t => t).slice(0, 4)")
    except Exception:
        return None


def page_marks(reader, i=0):
    """What a saved page carries beyond the original: annotations, content bytes, form XObjects."""
    pg = reader.pages[i]
    c = pg.get("/Contents")
    c = c.get_object() if c is not None else None
    streams = [x.get_object() for x in c] if isinstance(c, list) else ([c] if c is not None else [])
    n = 0
    for st in streams:
        try:
            n += len(st.get_data())
        except Exception:
            pass
    res = pg.get("/Resources")
    xo = res.get_object().get("/XObject") if res is not None else None
    annots = pg.get("/Annots")
    return {"annots": len(annots.get_object()) if annots is not None else 0, "content_len": n,
            "xobjects": sorted(xo.get_object().keys()) if xo is not None else [], "rotate": pg.get("/Rotate")}


def differs(a, b):
    return a["annots"] != b["annots"] or a["content_len"] != b["content_len"] or a["xobjects"] != b["xobjects"]


def health(after):
    """Is the device still well? Recorded after every case: three phone runs ended with a device that stopped answering."""
    t0 = time.time()
    try:
        h = {"loadavg": adb("shell", "cat /proc/loadavg", timeout=25).strip(),
             "mem_available_kB": adb("shell", "grep MemAvailable /proc/meminfo", timeout=25).split()[1:2],
             "app_pss_kB": (re.findall(r"TOTAL PSS:\s+(\d+)", adb("shell", f"dumpsys meminfo {PKG}", timeout=40)) or [None])[0],
             "anr_or_frozen": [l.strip()[:140] for l in adb("shell", "dumpsys activity processes | grep -i -E 'notResponding=true|crashing=true'", timeout=40).splitlines()][:4],
             "input_tap_seconds": None}
        t1 = time.time()
        adb("shell", "input keyevent KEYCODE_UNKNOWN", timeout=40)
        h["input_tap_seconds"] = round(time.time() - t1, 1)
        h["seconds"] = round(time.time() - t0, 1)
        ok = h["input_tap_seconds"] < 10 and not h["anr_or_frozen"]
    except Exception as e:
        h, ok = {"error": repr(e)[:200], "seconds": round(time.time() - t0, 1)}, False
    R.check(f"device health after {after}", True if ok else False, h)
    return ok


def case(name, fn):
    try:
        fn()
        health(name)
    except Exception as e:
        shot(name + "-error")
        R.check(f"{name}: the case ran to the end", False, {"error": repr(e)[:300], "controls": labels()})
        cdp.close()
        for _ in range(2):
            if PKG not in sh("dumpsys activity activities | grep -m1 topResumedActivity"):
                sh("input keyevent KEYCODE_BACK")
                time.sleep(1)
        sh(f"am start -n {COMP}")
        time.sleep(2)


set_rotation(portrait_rotation())
sh(f"pm clear {PKG}")              # fresh app: no tabs or theme left by other suites
sh(f"am start -W -n {COMP}")
cdp.connect(60)
cdp.wait("!!(window.Blazor && Blazor.navigateTo) && document.getElementById('app').children.length > 0", 60)
ORIG = {}
for fx, nm in (("doc-12p.pdf", "sv-text.pdf"), ("doc-12p.pdf", "sv-shape.pdf"), ("form-filled.pdf", "sv-form.pdf"),
               ("doc-12p.pdf", "sv-redact.pdf"), ("doc-12p.pdf", "sv-arrange.pdf"), ("doc-12p.pdf", "sv-print.pdf"),
               ("doc-12p.pdf", "sv-pass.pdf"), ("doc-12p.pdf", "sv-compress.pdf"), ("doc-12p.pdf", "sv-flatten.pdf"), ("rotated.pdf", "sv-rotated.pdf"), ("doc-12p.pdf", "sv-zoom.pdf"), ("doc-12p.pdf", "sv-close.pdf")):
    ORIG[nm] = push(fx, nm)
time.sleep(3)


def sv1_text():
    o = pick_open("sv-text.pdf")
    R.check("SV-0 Home › Open › system picker opens the file", o["opened"], o)
    mode("Mark")
    tool("Mark: Text", "Text")
    x, y = page_pt(0, 300, 420)
    tap_xy(x, y)
    first = cdp.js("document.activeElement && document.activeElement.tagName")
    if first != "TEXTAREA":   # AT-17: the caret isn't in the new box; a second tap on it is needed
        bx = cdp.js("(() => { const e = document.querySelector('textarea.mk-ta, textarea'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        if bx:
            tap_xy(bx[0], bx[1])
    R.check("AT-17 Mark › Text: the caret is in the new box after the first tap", first == "TEXTAREA", {"focused_after_first_tap": first})
    for ch in "chuvadimark":
        sh(f"input text {ch}")
        time.sleep(0.2)
    typed = cdp.js("document.activeElement && (document.activeElement.value || '')")
    sh("input keyevent KEYCODE_BACK")   # keyboard away
    time.sleep(1.2)
    shot("sv1-typed")
    R.check("SV-1a text typed into the box", typed == "chuvadimark", {"typed": typed})
    # Save in place (where the form factor offers it)
    hit = None if phone() else tap("Save (Ctrl S)", "Save", sel=".rb")
    if hit:
        time.sleep(4)
        picker_showed = in_picker()
        if picker_showed:
            sh("input keyevent KEYCODE_BACK")
        rd, pages = read("/sdcard/Download/sv-text.pdf", "sv1-inplace.pdf")
        R.check("SV-1b Save writes the text box back into the picked file", "chuvadimark" in " ".join(pages) and md5("sv-text.pdf") != ORIG["sv-text.pdf"],
                {"button": hit, "asked_where_to_save": picker_showed, "file_changed": md5("sv-text.pdf") != ORIG["sv-text.pdf"], "has_text": "chuvadimark" in " ".join(pages)})
    before = md5("sv-text.pdf")
    s = save_as()
    shot("sv1-saved-as")
    ok = False
    if s["files"]:
        rd, pages = read(s["files"][-1], "sv1-saveas.pdf")
        ok = "chuvadimark" in " ".join(pages) and len(pages) == 12
    if s["button"] and s["button"].get("disabled") and not s["files"]:
        ok = "n/a (Save as is greyed right after Save: nothing unsaved)"
    R.check("SV-1c Save as new PDF: the new file has the text box and all 12 pages", ok, s)
    R.check("SV-1d Save as leaves the picked file as it was", md5("sv-text.pdf") == before, {"before": before, "after": md5("sv-text.pdf")})


def sv2_shape():
    pick_open("sv-shape.pdf")
    mode("Mark")
    tool("Mark: Rectangle", "Rectangle", "Box")
    a = to_screen(*page_pt(0, 100, 500))
    b = to_screen(*page_pt(0, 300, 350))
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    s = save_as()
    shot("sv2-saved")
    base, _ = read("/sdcard/Download/sv-shape.pdf", "sv2-original.pdf")
    info = None
    if s["files"]:
        rd, pages = read(s["files"][-1], "sv2-saveas.pdf")
        if rd:
            info = {"saved": page_marks(rd), "original": page_marks(base), "pages": len(pages)}
    R.check("SV-2 rectangle drawn by finger is in the saved file (page 1 carries a new mark)",
            bool(info and differs(info["saved"], info["original"]) and info["pages"] == 12),
            {"save": s, "page1": info})


def sv3_form():
    pick_open("sv-form.pdf")
    shown = cdp.js("document.querySelector('.rpage svg') ? document.querySelector('.rpage svg').textContent.includes('Ravi') : null")
    shot("sv3-form")
    R.check("SV-3a a filled form's values are shown (patient = Ravi)", bool(shown), {"ravi_in_page": shown})
    fill = find("Fill form", "Fill", sel=".ph-tool, .rb, .ph-row")
    R.check("SV-3b (recorded) Fill form tool offered", "n/a", {"control": fill, "note": "greyed until built in the Reader on every platform (PHASE1-PARITY)"})
    mode("Mark")
    tool("Mark: Rectangle", "Rectangle", "Box")
    a = to_screen(*page_pt(0, 100, 400))
    b = to_screen(*page_pt(0, 250, 300))
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    s = save_as()
    vals = None
    if s["files"]:
        rd, _ = read(s["files"][-1], "sv3-saveas.pdf")
        if rd:
            f = rd.get_fields() or {}
            vals = {k: str(v.get("/V")) for k, v in f.items()}
    R.check("SV-3c after a markup Save as, the form's values are still in the file (patient Ravi, ward Cardiac)",
            bool(vals and vals.get("patient") == "Ravi" and vals.get("ward") == "Cardiac"), {"save": s, "fields": vals})


def sv4_redact():
    pick_open("sv-redact.pdf")
    mode("Protect")
    time.sleep(1)
    t = tool("Protect: Box", "Protect: Redact box", "Redact box", "Box")
    if not t:
        R.check("SV-4 redaction tool found", False, {"controls": labels()})
        return
    time.sleep(1.5)
    a = to_screen(*page_pt(0, 50, 765))
    b = to_screen(*page_pt(0, 400, 738))
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    boxes = cdp.js("(document.body.innerText.match(/(\\d+) box/) || [])[1] || null")
    shot("sv4-box")
    R.check("SV-4a finger drag draws a redaction box", boxes not in (None, "0"), {"tool": t, "boxes": boxes})
    mark_time()
    hit = tap("Save redacted copy", "Save as new PDF", sel=".ph-fab, .rb, button")
    time.sleep(2)
    confirm = None
    if not in_picker():
        shot("sv4-after-save-tap")
        confirm = tap("Redact and save", "Save redacted copy", "Redact", "Continue", "Save", sel=".chvd-card button, [role=dialog] button, .modal button")
        time.sleep(2)
    picker = save_picker()
    time.sleep(3)
    files = new_pdfs()
    shot("sv4-saved")
    res = None
    if files:
        rd, pages = read(files[-1], "sv4-redacted.pdf")
        raw = open(os.path.join(OUT, "sv4-redacted.pdf"), "rb").read()
        res = {"pages": len(pages), "heading_p1_in_text": "Discharge summary - page 1" in pages[0], "p1_body_kept": "patient" in pages[0],
               "heading_p2_kept": len(pages) > 1 and "Discharge summary - page 2" in pages[1],
               "heading_bytes_in_file": b"Discharge summary - page 1" in raw}
    R.check("SV-4b redacted copy saved; the covered heading is gone from the text, the rest stays",
            bool(res and not res["heading_p1_in_text"] and not res["heading_bytes_in_file"] and res["p1_body_kept"] and res["heading_p2_kept"]),
            {"button": hit, "confirm": confirm, "picker": picker, "files": files, "check": res, "app_says": says()})
    R.check("SV-4c the picked original is untouched by the redacted copy", md5("sv-redact.pdf") == ORIG["sv-redact.pdf"], None)


BENCH = "(() => { " + VIS + r""" const rect = e => { if (!e) return null; const r = e.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height}; };
  const shelf = [...document.querySelectorAll('[data-shelf]')];
  return { shelf: shelf.length, shelfVisible: shelf.filter(vis).filter(e => { const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return t && (e === t || e.contains(t)); }).slice(0, 4).map(e => ({...rect(e), key: e.dataset.shelf})),
           shelfHead: rect([...document.querySelectorAll('.shelf-head')].find(vis) || null),
           desk: rect([...document.querySelectorAll('.desk-drop')].find(vis) || null),
           order: [...document.querySelectorAll('.desk-drop [data-bench-id]')].map(e => e.dataset.benchId),
           cards: [...document.querySelectorAll('.desk-drop [data-bench-id]')].filter(vis).map(rect) }; })()"""


def folder_picker(sub, tries=24):
    """ACTION_OPEN_DOCUMENT_TREE picker: Downloads › sub › USE THIS FOLDER › ALLOW."""
    inside = False
    for _ in range(tries):
        xml = ui_dump()
        if ui_tap_text("ALLOW", "Allow"):
            time.sleep(3)
            return True
        if "documentsui" in xml:
            if inside and ui_tap_text("USE THIS FOLDER", "Use this folder"):
                time.sleep(1.5)
                continue
            if not inside and ui_tap_text(sub):
                inside = True
                time.sleep(1.5)
                continue
            if not inside:
                ui_tap_text("Downloads", "Download") or ui_tap_text("Show roots")
        time.sleep(1.2)
    return False


def sv5_arrange():
    sh("mkdir -p /sdcard/Download/at-bind")
    sh(f"pm clear {PKG}")          # one tab only, so the Shelf holds just this file
    sh(f"am start -W -n {COMP}")
    cdp.close()
    cdp.connect(60)
    cdp.wait("!!(window.Blazor && Blazor.navigateTo) && document.getElementById('app').children.length > 0", 60)
    _wv[0] = None
    pick_open("sv-arrange.pdf")
    mode("Arrange")
    cdp.wait("document.querySelectorAll('[data-shelf]').length >= 6", 40)
    st = cdp.js(BENCH)
    if not st["shelfVisible"]:
        if st["shelfHead"]:
            tap_xy(st["shelfHead"]["x"], st["shelfHead"]["y"])
        else:
            tap("Shelf", sel=".rb, button")
        time.sleep(1.5)
        st = cdp.js(BENCH)
    ours = [s for s in st["shelfVisible"]]
    start = len(st["order"])
    dropped = []
    for idx in (2, 0):          # shelf page 3, then page 1
        st = cdp.js(BENCH)
        if not st["shelfVisible"]:
            tap_xy(st["shelfHead"]["x"], st["shelfHead"]["y"]) if st["shelfHead"] else tap("Shelf", sel=".rb, button")
            time.sleep(1.5)
            st = cdp.js(BENCH)
        if len(st["shelfVisible"]) <= idx:
            R.check("SV-5 shelf pages reachable", False, {"bench": st, "controls": labels()})
            return
        src = st["shelfVisible"][idx]
        a = to_screen(src["x"], src["y"])
        d = to_screen(st["desk"]["x"], st["desk"]["y"] + st["desk"]["h"] * 0.3)
        how = longdrag(a, d, lambda: cdp.js(BENCH)["order"] != st["order"])
        after = cdp.js(BENCH)
        new = [i for i in after["order"] if i not in st["order"]]
        dropped.append({"shelf": src["key"], "new_ids": new, "order": after["order"], "gesture": how})
    st = cdp.js(BENCH)
    shot("sv5-two-on-desk")
    R.check("SV-5a long-press drag puts two shelf pages on the desk", len(st["order"]) == start + 2, {"drops": dropped, "desk_before": start})
    id_p3 = dropped[0]["new_ids"][0] if dropped[0]["new_ids"] else None
    sent = None
    if len(st["order"]) == start:
        # no drag landed: use the Reader's own "Send this page to a desk" so Bind is still exercised
        mode("Read")
        time.sleep(1)
        s1 = tap("Send this page to a desk", sel="button")
        time.sleep(1.5)
        pick1 = tap("Desk 1", "New desk", sel="[role=menu] *, .menu *, .chvd-card button, button")
        tap("Next page", sel="button")
        time.sleep(1)
        s2 = tap("Send this page to a desk", sel="button")
        time.sleep(1.5)
        tap("Desk 1", "New desk", sel="[role=menu] *, .menu *, .chvd-card button, button")
        mode("Arrange")
        time.sleep(1.5)
        st = cdp.js(BENCH)
        sent = {"send": s1, "desk_choice": pick1, "second": s2, "desk_now": len(st["order"]), "controls": labels() if len(st["order"]) == start else None}
        shot("sv5-sent-from-reader")
        R.check("SV-5a2 (tablet, other way) Reader › Send this page to a desk puts pages on the desk", len(st["order"]) >= start + 1, sent)
    before = st["order"][:]
    tried = []
    for way in ("first-to-end", "last-to-front"):
        st2 = cdp.js(BENCH)
        if len(st2["cards"]) < 2 or st2["order"] != before:
            break
        c0, c1 = st2["cards"][0], st2["cards"][-1]
        if way == "first-to-end":
            a, b = to_screen(c0["x"], c0["y"]), to_screen(c1["x"] + c1["w"] * 0.6, c1["y"])
        else:
            a, b = to_screen(c1["x"], c1["y"]), to_screen(c0["x"] - c0["w"] * 0.6, c0["y"])
        how = longdrag(a, b, lambda: cdp.js(BENCH)["order"] != before)
        tried.append(way + ": " + how)
    after = cdp.js(BENCH)["order"]
    shot("sv5-reordered")
    R.check("SV-5b long-press drag reorders pages on the desk", after != before and sorted(after) == sorted(before), {"before": before, "after": after, "tried": tried})
    mark_time()
    hit = tap("Bind all", "Bind desk", "Bind", sel=".ph-fab, .ph-pager, .rb, .bt-bind, button")
    time.sleep(2)
    picker = folder_picker("at-bind")
    time.sleep(5)
    files = new_pdfs()
    shot("sv5-bound")
    got = None
    if files:
        rd, pages = read(files[-1], "sv5-bound.pdf")
        got = [int(m.group(1)) if (m := re.search(r"- page (\d+)", t)) else None for t in pages]
    msg = says()
    body = cdp.js("document.body.innerText") or ""
    leak = [l.strip()[:160] for l in body.splitlines() if "/data/" in l or "/cache/" in l]
    R.check("AT-21 after Bind all the message names the chosen folder, not an internal path", bool(files) and not leak and any("at-bind" in l for l in body.splitlines() if "Bound" in l),
            {"lines_with_Bound": [l.strip()[:160] for l in body.splitlines() if "Bound" in l], "internal_paths_on_screen": leak, "status": msg})
    want = [3 if i == id_p3 else 1 for i in after][-2:] if id_p3 else ([1, 2][:len(after)] if sent and after else None)
    R.check("SV-5c Bind all → folder chosen → bound PDF holds the desk's pages in the desk's order", bool(got and want and got[-len(want):] == want),
            {"button": hit, "picker": picker, "files": files, "saved_pages": got, "desk_order_as_pages": want, "app_says": says()})


def sv6_print():
    if not pick_open("sv-print.pdf")["opened"]:
        R.check("SV-6 file opened through the picker", False, None)
        return
    if phone():
        tap("More", sel=".ph-ib")
        tap("Print", sel=".ph-sheet *")
    else:
        tap("Print (Ctrl P)", "Print", sel=".rb, .lb-btn")
    time.sleep(2)
    btn = find("Print", sel="section.chvd-card .footer button") or find("Print", sel=".chvd-card button")
    mark_time()
    if btn:
        tap_xy(btn["x"], btn["y"])
    time.sleep(5)
    for _ in range(3):
        xml = ui_dump()
        if "Select a printer" in xml:
            ui_tap_text("Select a printer")
            time.sleep(1.5)
            ui_tap_text("Save as PDF")
            time.sleep(2)
        else:
            break
    xml = ui_dump()
    m = re.search(r'resource-id="com.android.printspooler:id/print_button"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
    time.sleep(4)
    shot("sv6-print-save")
    picker = save_picker()
    time.sleep(3)
    files = new_pdfs()
    vec = None
    if files:
        rd, pages = read(files[-1], "sv6-printed.pdf")
        if rd:
            vec = {"pages": len(pages), "text_chars": sum(len(t) for t in pages), "images": sum(len(p.images) for p in rd.pages), "marker": any("zephyrine" in t for t in pages)}
    R.check("SV-6 print → Android dialog → PDF is vector (text kept, no page images)", bool(vec and vec["text_chars"] > 1000 and vec["images"] == 0),
            {"card_button": btn, "spooler_button": bool(m), "picker": picker, "files": files, "pdf": vec})


def card_inputs():
    return cdp.js("(() => { " + VIS + " return [...document.querySelectorAll('.chvd-card input, [role=dialog] input, .ph-sheet input')].filter(vis).map(e => { const r = e.getBoundingClientRect(); return {type: e.type, ph: e.placeholder, x: r.left + r.width / 2, y: r.top + r.height / 2}; }); })()")


def card_buttons():
    return cdp.js("(() => { " + VIS + " return [...document.querySelectorAll('.chvd-card button, [role=dialog] button, .ph-sheet button')].filter(vis).map(e => (e.getAttribute('aria-label') || e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40)).filter(t => t); })()")


def doc_action(*names):
    """A whole-document action: tablet Document menu / rail; phone ⋮ sheet."""
    if phone():
        tap("More", sel=".ph-ib")
        time.sleep(1)
        return tap(*names, sel=".ph-sheet *")
    hit = tap(*names, sel=".rb, .lb-btn")
    if hit:
        return hit
    tap("Document actions", "Document", sel=".tb-doc, button")
    time.sleep(1)
    return tap(*names, sel="[role=menu] *, [role=menuitem], .tb-doc-menu *, .menu *, button")


def sv7_password():
    if not pick_open("sv-pass.pdf")["opened"]:
        R.check("SV-7 file opened through the picker", False, None)
        return
    mode("Protect")
    time.sleep(1)
    t = tool("Protect: Password", "Password", "Set a password", "Set password", "Encrypt") or doc_action("Password", "Set a password", "Protect with a password")
    time.sleep(1.5)
    ins = card_inputs()
    for n in range(2):
        now = [i for i in card_inputs() if i["type"] == "password"]
        if len(now) <= n:
            break
        tap_xy(now[n]["x"], now[n]["y"])
        time.sleep(0.8)
        sh("input text chuvadi1")
        time.sleep(0.8)
        if "mInputShown=true" in sh("dumpsys input_method | grep mInputShown"):
            sh("input keyevent KEYCODE_BACK")
            time.sleep(1)
    pw_state = cdp.js("[...document.querySelectorAll('.chvd-card input[type=password], [role=dialog] input[type=password], .ph-sheet input[type=password]')].map(e => e.value.length)")
    shot("sv7-card")
    btns = card_buttons()
    mark_time()
    hit = tap("Save protected copy", "Save a protected copy", "Protect", "Set password", "Encrypt", "Save", sel=".chvd-card button, [role=dialog] button, .ph-sheet button")
    time.sleep(2)
    picker = save_picker()
    time.sleep(3)
    files = new_pdfs()
    res = None
    if files:
        lp = os.path.join(OUT, "sv7-protected.pdf")
        adb("pull", files[-1], lp)
        try:
            r = PdfReader(lp)
            res = {"encrypted": r.is_encrypted, "opens_with_password": bool(r.decrypt("chuvadi1")) if r.is_encrypted else None, "pages": len(r.pages) if (not r.is_encrypted or r.decrypt("chuvadi1")) else None}
        except Exception as e:
            res = {"error": repr(e)[:120]}
    R.check("SV-7 password-protected copy saved: encrypted, opens with the password, 12 pages",
            bool(res and res.get("encrypted") and res.get("opens_with_password") and res.get("pages") == 12),
            {"tool": t, "fields": ins, "typed_lengths": pw_state, "card_buttons": btns, "button": hit, "picker": picker, "files": files, "pdf": res, "app_says": says()})
    R.check("SV-7b the picked original is still unencrypted", md5("sv-pass.pdf") == ORIG["sv-pass.pdf"], None)


def doc_save(case_id, name, action_labels, confirm_labels):
    if not pick_open(name)["opened"]:
        R.check(f"{case_id} file opened through the picker", False, None)
        return
    act = doc_action(*action_labels)
    time.sleep(2)
    shot(case_id.lower() + "-card")
    btns = card_buttons()
    mark_time()
    hit = None
    if not in_picker():
        hit = tap(*confirm_labels, sel=".chvd-card button, [role=dialog] button, .ph-sheet button")
        if not hit:
            hit = cdp.js("(() => { " + VIS + " const b = [...document.querySelectorAll('button')].filter(vis).find(e => /^(press|reduce|compress)\\b/i.test((e.innerText || '').trim()) && !e.closest('.rb, .lb-btn, [role=menu], .ph-row')); if (!b) return null; const r = b.getBoundingClientRect(); return {text: b.innerText.trim(), x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: b.disabled}; })()")
            if hit:
                tap_xy(hit["x"], hit["y"])
        time.sleep(2)
    picker = save_picker() if case_id != "SV-8" or in_picker() else False
    time.sleep(6)
    files = new_pdfs()
    private = None
    if case_id == "SV-8":
        private = sh("su 0 find /data/user/0/in.chuvadi.reader /sdcard/Android/data/in.chuvadi.reader -newer /data/local/tmp/at-mark -iname '*press*' 2>/dev/null | head -5").strip().splitlines()
    if not files and case_id == "SV-8":
        folder_picker("at-bind", 6) if in_picker() else None
        time.sleep(4)
        files = new_pdfs()
    res = None
    if files:
        rd, pages = read(files[-1], case_id.lower() + "-out.pdf")
        res = {"pages": len(pages), "text_p1": "Discharge summary - page 1" in pages[0], "bytes": os.path.getsize(os.path.join(OUT, case_id.lower() + "-out.pdf"))}
    R.check(f"{case_id} {action_labels[0]} → saved to a new file: readable, 12 pages, text kept",
            bool(res and res["pages"] == 12 and res["text_p1"]),
            {"action": act, "card_buttons": btns, "button": hit, "picker": picker, "files": files, "files_inside_the_app_only": private, "pdf": res, "app_says": says(), "screen_lines": [l.strip()[:140] for l in (cdp.js("document.body.innerText") or "").splitlines() if re.search(r"press|saved|smaller|compress|kB|MB", l, re.I)][:8], "controls": None if act else labels()})


def sv8_compress():
    doc_save("SV-8", "sv-compress.pdf", ("Reduce file size", "Compress", "Compress…"), ("Reduce and save", "Save smaller copy", "Save a smaller copy", "Press and save", "Press", "Reduce", "Compress and save", "Compress", "Save"))


def sv9_flatten():
    doc_save("SV-9", "sv-flatten.pdf", ("Flatten", "Flatten…"), ("Flatten and save", "Flatten", "Save"))


def sv10_rotated():
    o = pick_open("sv-rotated.pdf")
    boxes = cdp.js("[...document.querySelectorAll('.rpage-wrap .rpage')].slice(0, 2).map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
    shot("sv10-rotated")
    if phone() and len(boxes) < 2:
        boxes = boxes + [None]
    R.check("SV-10a a page with /Rotate 90 is shown turned (wider than tall), upright text",
            bool(o["opened"] and boxes and boxes[0] and boxes[0][0] > boxes[0][1]), {"open": o, "page_boxes_w_h": boxes})
    mode("Mark")
    tool("Mark: Rectangle", "Rectangle", "Box")
    r = cdp.js("(() => { const e = [...document.querySelectorAll('.rpage-wrap .rpage')].filter(e => e.getBoundingClientRect().width > 0)[0].getBoundingClientRect(); return [e.left, e.top, e.width, e.height]; })()")
    a = to_screen(r[0] + r[2] * 0.15, r[1] + r[3] * 0.2)     # top-left quarter as seen on screen
    b = to_screen(r[0] + r[2] * 0.40, r[1] + r[3] * 0.45)
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    shot("sv10-marked")
    s = save_as()
    info = None
    if s["files"]:
        rd, pages = read(s["files"][-1], "sv10-saveas.pdf")
        base, _ = read("/sdcard/Download/sv-rotated.pdf", "sv10-original.pdf")
        if rd:
            info = {"saved": page_marks(rd), "original": page_marks(base), "pages": len(pages)}
    R.check("SV-10b mark on the rotated page is saved; the page keeps /Rotate 90 (placement: see sv10 screenshots and sv10-saveas.pdf)",
            bool(info and differs(info["saved"], info["original"]) and info["saved"]["rotate"] == 90), {"save": s, "page1": info})


def stamp_rect(reader, i=0):
    """Where the saved mark sits on the page, in points: the path the newest stamp XObject draws (its `re`, or its m/l/c points)."""
    try:
        pg = reader.pages[i]
        xo = pg["/Resources"]["/XObject"]
        name = sorted(k for k in xo.keys() if "Stamp" in k)[-1]
        d = xo[name].get_object().get_data().decode("latin-1")
        pts = []
        for m in re.finditer(r"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re", d):
            x, y, w, h = map(float, m.groups())
            pts += [(x, y), (x + w, y + h)]
        for m in re.finditer(r"([-\d.]+) ([-\d.]+) [ml]\b", d):
            pts.append((float(m.group(1)), float(m.group(2))))
        if not pts:
            return {"stream": d[:200]}
        return {"x0": round(min(p[0] for p in pts), 1), "y0": round(min(p[1] for p in pts), 1), "x1": round(max(p[0] for p in pts), 1), "y1": round(max(p[1] for p in pts), 1)}
    except Exception as e:
        return {"error": repr(e)[:200]}


PAGE0 = "(() => { const e = [...document.querySelectorAll('.rpage-wrap .rpage')].filter(e => e.getBoundingClientRect().width > 0)[0].getBoundingClientRect(); return [e.left, e.top, e.width, e.height, innerWidth, innerHeight]; })()"


def sv12_zoom():
    """Pinch with two fingers, then a mark by finger at that zoom: it must be saved where it was drawn."""
    if not pick_open("sv-zoom.pdf")["opened"]:
        R.check("SV-12 file opened through the picker", False, None)
        return
    r0 = cdp.js(PAGE0)
    c = to_screen(r0[4] / 2, r0[5] / 2)
    span = min(to_screen(r0[4], 0)[0], 1000)
    touch("pinch", c[0], c[1], round(span * 0.25), round(span * 0.8), 600)
    time.sleep(2)
    r1 = cdp.js(PAGE0)
    shot("sv12-pinched-out")
    R.check("SV-12a pinch out with two fingers makes the page bigger", r1[2] > r0[2] * 1.15 or (cdp.js("visualViewport.scale") or 1) > 1.15, {"page_w_before": round(r0[2]), "page_w_after": round(r1[2]), "viewport": r0[4:], "visual_scale": cdp.js("visualViewport.scale")})
    mode("Mark")
    tool("Mark: Rectangle", "Rectangle", "Box")
    # the page that is under the upper-middle of the screen after the pinch (on the phone that is no longer page 1)
    pg = cdp.js("(() => { const ps = [...document.querySelectorAll('.rpage-wrap .rpage')]; const y = innerHeight * 0.34; const i = ps.findIndex(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.top <= y - 40 && r.bottom >= y + 110; }); if (i < 0) return null; const r = ps[i].getBoundingClientRect(); return [r.left, r.top, r.width, r.height, innerWidth, innerHeight, i]; })()")
    if not pg:
        R.check("SV-12b a page fills the upper-middle of the screen after the pinch", False, {"first_page": cdp.js(PAGE0)})
        return
    r, page_i = pg[:6], pg[6]
    x0, x1 = max(r[0], 0) + min(r[2], r[4]) * 0.22, max(r[0], 0) + min(r[2], r[4]) * 0.62
    y0, y1 = r[5] * 0.30, r[5] * 0.30 + 90
    a, b = to_screen(x0, y0), to_screen(x1, y1)
    touch("swipe", a[0], a[1], b[0], b[1], 900)       # raw touch events: the finger really ends at b
    time.sleep(1.5)
    shot("sv12-marked-at-zoom")
    r2 = cdp.js(f"(() => {{ const e = [...document.querySelectorAll('.rpage-wrap .rpage')][{page_i}].getBoundingClientRect(); return [e.left, e.top, e.width, e.height]; }})()")
    want = {"x0": round((x0 - r[0]) / r[2] * 595.28, 1), "x1": round((x1 - r[0]) / r[2] * 595.28, 1),
            "y1": round((1 - (y0 - r[1]) / r[3]) * 841.89, 1), "y0": round((1 - (y1 - r[1]) / r[3]) * 841.89, 1)}
    s = save_as()
    got = None
    if s["files"]:
        rd, pages = read(s["files"][-1], "sv12-saveas.pdf")
        got = stamp_rect(rd, page_i) if rd else None
    off = max(abs(got[k] - want[k]) for k in want) if got and "x0" in got else None
    R.check("SV-12b a rectangle drawn by finger at the pinched zoom is saved where it was drawn (within 6 pt)", off is not None and off <= 6,
            {"page": page_i + 1, "zoomed_page_css": [round(v) for v in r[:4]], "page_moved_during_draw": [round(v) for v in r2[:4]] != [round(v) for v in r[:4]], "drawn_pt": want, "saved_pt": got, "largest_offset_pt": off, "save": s})
    away = card_away() if phone() and cdp.js(FCARD) else None       # the phone's mark card lies over the middle of the screen
    c2 = to_screen(r0[4] / 2, r0[5] * 0.36)
    touch("pinch", c2[0], c2[1], round(span * 0.8), round(span * 0.25), 600)
    time.sleep(2)
    r3 = cdp.js(PAGE0)
    R.check("SV-12c pinch in makes it smaller again", r3[2] < r1[2] * 0.9, {"page_w_zoomed": round(r1[2]), "page_w_after_pinch_in": round(r3[2]), "mark_card_put_away_by": away, "mode": "Mark"})


def sv11_excel():
    adb("push", os.path.join(FX, "test.xlsx"), "/sdcard/Download/sv-sheet.xlsx")
    sh("am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file:///sdcard/Download/sv-sheet.xlsx' >/dev/null")
    global XLSX_MD5
    XLSX_MD5 = sh("md5sum /sdcard/Download/sv-sheet.xlsx").split()[0]
    time.sleep(2)
    cdp.js("Blazor.navigateTo('/')")
    time.sleep(1.5)
    tap("Open a document", sel=".ph-fab") if phone() else tap("Choose a document to open", "Open (Ctrl O)", "Open")
    time.sleep(2.5)
    picked, seen = picker_choose("sv-sheet.xlsx")
    if not picked:
        shot("picker-file-not-found")
        if in_picker():
            sh("input keyevent KEYCODE_BACK")
    ok = cdp.wait("document.querySelectorAll('.xv-cell').length > 0", 40)
    shot("sv11-grid")
    cells = cdp.js("(() => { " + VIS + " const c = [...document.querySelectorAll('.xv-cell')]; const withv = c.filter(e => (e.dataset.v || e.textContent || '').trim());"
                   " return {cells: c.length, filled: withv.length, sample: withv.slice(0, 6).map(e => [e.dataset.a, (e.dataset.v || e.textContent || '').trim().slice(0, 30)]),"
                   " hdr: document.querySelectorAll('.xv-colhdr, .xv-rowhdr').length, tabs: [...document.querySelectorAll('.xv-tab')].map(e => e.textContent.trim()), overflowX: document.documentElement.scrollWidth - innerWidth}; })()") if ok else None
    R.check("SV-11a Excel file opens as a grid with headers, sheet tabs and the cell text", bool(cells and cells["filled"] > 0 and cells["hdr"] > 0 and any("Chuvadi XLSX test cell" in v for _, v in cells["sample"])), cells)
    t = cdp.js("(() => { " + VIS + " const e = [...document.querySelectorAll('.xv-cell')].filter(vis).find(e => (e.dataset.v || e.textContent || '').includes('Chuvadi XLSX test cell')); if (!e) return null;"
               " const r = e.getBoundingClientRect(); return {a: e.dataset.a, x: r.left + Math.min(r.width / 2, 30), y: r.top + r.height / 2}; })()") if ok else None
    bar = None
    if t:
        tap_xy(t["x"], t["y"])
        bar = cdp.js("(() => { const b = document.querySelector('.xv-valbar'); if (!b) return null; const r = b.getBoundingClientRect();"
                     " return {shown: r.width > 0 && r.height > 0, addr: (document.querySelector('.xv-val-addr') || {}).textContent, text: (document.querySelector('.xv-val-text') || {}).textContent, h: Math.round(r.height)}; })()")
    shot("sv11-valuebar")
    R.check("SV-11b tapping a cell shows its address and full value in the value bar (H-23)",
            bool(bar and bar["shown"] and bar.get("text") and "Chuvadi XLSX test cell" in bar["text"] and (bar.get("addr") or "").strip() == (t or {}).get("a")),
            {"cell": t, "value_bar": bar})



RECT = lambda sel: cdp.js("(() => { " + VIS + f" const e = [...document.querySelectorAll({sel!r})].filter(vis)[0]; if (!e) return null; const r = e.getBoundingClientRect(); return {{x: r.left + r.width / 2, y: r.top + r.height / 2, w: Math.round(r.width), h: Math.round(r.height), left: r.left, top: r.top, right: r.right, bottom: r.bottom, text: (e.innerText || '').trim().slice(0, 60)}}; }})()")
CLOSEQ = ("(() => { " + VIS + " const q = [...document.querySelectorAll('.closeq')].filter(vis)[0]; if (!q) return null; const r = q.getBoundingClientRect();"
          " return {title: (q.querySelector('.closeq-title') || {}).innerText, text: (q.querySelector('.closeq-text') || {}).innerText, inside_screen: r.left >= 0 && r.top >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1,"
          " buttons: [...q.querySelectorAll('button')].map(b => { const k = b.getBoundingClientRect(); return {t: b.innerText.trim(), x: k.left + k.width / 2, y: k.top + k.height / 2, w: Math.round(k.width), h: Math.round(k.height), top_el: (document.elementFromPoint(k.left + k.width / 2, k.top + k.height / 2) || {}) === b}; })}; })()")


def close_tab_by_touch(name):
    if phone():
        t = RECT(".ph-t")
        if t:
            tap_xy(t["x"], t["y"])
            time.sleep(1.2)
        x = RECT(f".ph-tab-x[aria-label='Close {name}']")
    else:
        # 12d: on the tablet Close lives in Document ▾ (the tab's own × is hidden there)
        tap("Document actions", "Document", sel=".tb-doc, button")
        time.sleep(1.2)
        x = cdp.js("(() => { " + VIS + " const b = [...document.querySelectorAll('button, [role=menuitem]')].filter(vis).find(e => (e.innerText || '').trim() === 'Close' && e.parentElement && /Properties/.test(e.parentElement.innerText || '')); if (!b) return null; const r = b.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, w: Math.round(r.width), h: Math.round(r.height), text: 'Document ▾ › Close'}; })()")
        if x:
            tap_xy(x["x"], x["y"])
            time.sleep(1.5)
        return x or {"close_item": None, "menu_items": labels()}
    if x:
        tap_xy(x["x"], x["y"])
        time.sleep(1.5)
    return x


def sv13_close_card():
    """D-190: closing a tab with unsaved marks asks first. All by touch."""
    name = "sv-close.pdf"
    if not pick_open(name)["opened"]:
        R.check("SV-13 file opened through the picker", False, None)
        return
    mode("Mark")
    tool("Mark: Rectangle", "Rectangle", "Box")
    r = cdp.js(PAGE0)
    a, b = to_screen(max(r[0], 0) + min(r[2], r[4]) * 0.25, max(r[1], 0) + 150), to_screen(max(r[0], 0) + min(r[2], r[4]) * 0.6, max(r[1], 0) + 250)
    sh(f"input swipe {a[0]} {a[1]} {b[0]} {b[1]} 600")
    time.sleep(1.5)
    marks = "document.querySelectorAll('.mk-layer > *, .mk-layer svg > *').length"
    n0 = cdp.js(marks)
    if phone() and cdp.js(FCARD):
        card_away()
    x = close_tab_by_touch(name)
    q = cdp.js(CLOSEQ)
    shot("sv13-close-card")
    small = [b for b in (q or {}).get("buttons", []) if b["h"] < 44 or b["w"] < 44]
    R.check("SV-13a closing a tab with an unsaved mark asks first (card names the file; Save as…, Discard, Cancel)",
            bool(q and name in (q.get("title") or "") and {"Discard", "Cancel"} <= {b["t"] for b in q["buttons"]} and any(b["t"].startswith("Save") for b in q["buttons"])),
            {"close_control": x, "marks_on_page": n0, "card": q})
    if not q:
        R.check("SV-13 close card shown", False, {"controls": labels()})
        return
    R.check("SV-13b the card is whole on screen, its buttons are on top and each is at least 44 px", bool(q["inside_screen"] and not small and all(b["top_el"] for b in q["buttons"])),
            {"inside_screen": q["inside_screen"], "smaller_than_44": small, "buttons": [(b["t"], b["w"], b["h"], b["top_el"]) for b in q["buttons"]]})
    c = next(b for b in q["buttons"] if b["t"] == "Cancel")
    tap_xy(c["x"], c["y"])
    time.sleep(1.5)
    still = cdp.js("(() => { const t = [...document.querySelectorAll('.rtab-name, .ph-t, .ph-row-l')].map(e => e.textContent.trim()); return t; })()")
    R.check("SV-13c Cancel: the card goes, the tab and its mark stay", cdp.js(CLOSEQ) is None and any(name in t for t in still or []) and cdp.js(marks) >= n0,
            {"card_gone": cdp.js(CLOSEQ) is None, "tabs": still, "marks_before": n0, "marks_after": cdp.js(marks)})
    if phone():
        h = RECT(".ph-sheet .ph-sheet-a, .ph-handle")
        if h and not RECT(f".ph-tab-x[aria-label='Close {name}']"):
            pass
    # second time: Save as…
    mark_time()
    if not cdp.js(CLOSEQ):
        if phone() and RECT(f".ph-tab-x[aria-label='Close {name}']"):
            k = RECT(f".ph-tab-x[aria-label='Close {name}']")
            tap_xy(k["x"], k["y"])
            time.sleep(1.5)
        else:
            close_tab_by_touch(name)
    q2 = cdp.js(CLOSEQ)
    sa = next((b for b in (q2 or {}).get("buttons", []) if b["t"].startswith("Save as")), None)
    picker, files, pages = False, [], None
    if sa:
        tap_xy(sa["x"], sa["y"])
        picker = save_picker()
        time.sleep(4)
        files = new_pdfs()
    got = None
    if files:
        rd, pages = read(files[-1], "sv13-closed-saveas.pdf")
        got = page_marks(rd) if rd else None
    time.sleep(1.5)
    tabs = cdp.js("[...document.querySelectorAll('.rtab-name, .ph-row-l, .ph-t')].map(e => e.textContent.trim())")
    R.check("SV-13d Save as… from the card: Android's picker, the new file has the mark, then the tab closes",
            bool(files and got and (got["annots"] or got["xobjects"]) and pages and len(pages) == 12 and cdp.js(CLOSEQ) is None and not any(t == name for t in tabs or [])),
            {"card_again": bool(q2), "picker": picker, "files": files, "pdf": got, "pages": len(pages) if pages else None, "tabs_after": tabs, "card_still_up": cdp.js(CLOSEQ)})
    shot("sv13-after-saveas")


def sv14_excel_resize():
    """D-190: Excel columns and rows resized on screen by finger (viewing only). Runs on the sheet SV-11 left open."""
    if not cdp.js("document.querySelectorAll('.xv-colhdr').length > 0"):
        R.check("SV-14 Excel sheet on screen", False, {"controls": labels()})
        return
    COL = "(() => { const e = [...document.querySelectorAll('.xv-colhdr')].find(e => e.textContent.trim() === 'A'); if (!e) return null; const r = e.getBoundingClientRect(); return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height, own: e.classList.contains('own')}; })()"
    ROW = "(() => { const e = [...document.querySelectorAll('.xv-rowhdr')].find(e => e.textContent.trim() === '2'); if (!e) return null; const r = e.getBoundingClientRect(); return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height, own: e.classList.contains('own')}; })()"
    c0 = cdp.js(COL)
    a, b = to_screen(c0["right"] - 1, (c0["top"] + c0["bottom"]) / 2), to_screen(c0["right"] + 70, (c0["top"] + c0["bottom"]) / 2)
    touch("swipe", a[0], a[1], b[0], b[1], 700)
    time.sleep(1.5)
    c1 = cdp.js(COL)
    shot("sv14-column-wider")
    R.check("SV-14a dragging column A's right edge with a finger makes it wider (about 70 px)", bool(c1 and c1["w"] - c0["w"] > 40), {"width_before": round(c0["w"]), "width_after": round(c1["w"]) if c1 else None, "marked_own": c1 and c1["own"], "header_h": round(c0["h"])})
    r0 = cdp.js(ROW)
    a, b = to_screen((r0["left"] + r0["right"]) / 2, r0["bottom"] - 1), to_screen((r0["left"] + r0["right"]) / 2, r0["bottom"] + 40)
    touch("swipe", a[0], a[1], b[0], b[1], 700)
    time.sleep(1.5)
    r1 = cdp.js(ROW)
    R.check("SV-14b dragging row 2's lower edge with a finger makes it taller (about 40 px)", bool(r1 and r1["h"] - r0["h"] > 20), {"height_before": round(r0["h"]), "height_after": round(r1["h"]) if r1 else None, "marked_own": r1 and r1["own"], "header_w": round(r0["w"])})
    rs = RECT(".xv-resetsizes")
    R.check("SV-14c the reset-sizes control is offered and is a touch-sized target (44 px)", bool(rs and rs["h"] >= 44 and rs["w"] >= 44), {"reset": rs})
    cell = cdp.js("(() => { const e = [...document.querySelectorAll('.xv-cell')].find(e => (e.dataset.v || e.textContent || '').includes('Chuvadi XLSX test cell')); if (!e) return null; const r = e.getBoundingClientRect(); return {w: Math.round(r.width), text_w: Math.round((e.querySelector('.xv-s') || e).getBoundingClientRect().width)}; })()")
    if rs:
        tap_xy(rs["x"], rs["y"])
        time.sleep(1.2)
        c2 = cdp.js(COL)
        R.check("SV-14d reset puts the sizes back", bool(c2 and abs(c2["w"] - c0["w"]) < 2), {"width_start": round(c0["w"]), "width_after_reset": round(c2["w"]) if c2 else None, "cell_while_wide": cell})
    md = sh("md5sum /sdcard/Download/sv-sheet.xlsx").split()[0]
    R.check("SV-14e the workbook file is not changed by resizing (viewing only)", md == XLSX_MD5, {"md5_before": XLSX_MD5, "md5_after": md})



XLSX_MD5 = None
CASES = [("SV-1", sv1_text), ("SV-2", sv2_shape), ("SV-3", sv3_form), ("SV-4", sv4_redact), ("SV-7", sv7_password), ("SV-8", sv8_compress),
         ("SV-9", sv9_flatten), ("SV-10", sv10_rotated), ("SV-12", sv12_zoom), ("SV-11", sv11_excel), ("SV-14", sv14_excel_resize), ("SV-13", sv13_close_card), ("SV-6", sv6_print), ("SV-5", sv5_arrange)]
if phone():
    # Round 11: the phone stopped answering after the third Mark › Save as. Everything else first, so it is covered whatever happens.
    first = ["SV-11", "SV-14", "SV-12", "SV-10", "SV-1", "SV-2", "SV-3", "SV-13"]     # what round 12 did not reach on the phone
    CASES = [c for c in CASES if c[0] in first] + [c for c in CASES if c[0] not in first]
only = [x for x in os.environ.get("AT_SAVES_ONLY", "").split(",") if x]
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.json")):
    only = only or [x for x in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.json"))).get("saves_only", "").split(",") if x]
if only:
    CASES = [c for c in CASES if c[0] in only]
health("start")
for name, fn in CASES:
    case(name, fn)

log = adb("logcat", "-d", "-v", "epoch")
fatal = [l for l in log.splitlines() if "FATAL EXCEPTION" in l or f"ANR in {PKG}" in l]
R.check("R-10 no crash / ANR in the save suite", not fatal, fatal[:5])
