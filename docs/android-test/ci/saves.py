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
            c = cdp.js("(() => { " + VIS + " const e = [...document.querySelectorAll('.ph-handle, .ph-sheet-a, .ph-sheet [aria-label=Close], .chvd-card [aria-label=Close], .mk-card [aria-label=Close], .ph-scrim')].find(vis);"
                       " if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
            if c:
                q = to_screen(c[0], c[1])
                sh(f"input tap {q[0]} {q[1]}")
            else:
                cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
            time.sleep(1.2)
            continue
        if hit["covered"]:
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
    sh(f"input draganddrop {a[0]} {a[1]} {b[0]} {b[1]} 1500")
    time.sleep(1.5)
    if changed():
        return "input draganddrop"
    touch("longdrag", a[0], a[1], b[0], b[1], 800, 1200)
    return "touch.py longdrag" if changed() else "neither moved it"


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
    ok = False
    for _ in range(10):
        xml = ui_dump()
        m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(name), xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            sh(f"input tap {(x1 + x2) // 2} {(y1 + y2) // 2}")
            ok = True
            break
        if not (ui_tap_text("Download") or ui_tap_text("Downloads")):
            ui_tap_text("Show roots")
        time.sleep(1.5)
    if not ok and in_picker():
        sh("input keyevent KEYCODE_BACK")
    stem = name.rsplit(".", 1)[0]
    opened = cdp.wait(f"(() => {{ const t = ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {{}}).textContent || '';"
                      f" return t.trim().startsWith('{stem}') && document.querySelectorAll('.rpage svg').length > 0; }})()", 40)
    return {"button": hit, "picked": ok, "opened": bool(opened)}


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
    hit = tap("Save as new PDF", "Save as", sel=".ph-fab, .rb, .ph-row, button")
    if not hit and phone():
        tap("More", sel=".ph-ib")
        hit = tap("Save as new PDF", "Save as", sel=".ph-sheet *")
    time.sleep(2)
    picker = save_picker()
    time.sleep(2)
    files = new_pdfs()
    return {"button": hit, "picker": picker, "files": files, "app_says": says()}


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


def case(name, fn):
    try:
        fn()
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
               ("doc-12p.pdf", "sv-pass.pdf"), ("doc-12p.pdf", "sv-compress.pdf"), ("doc-12p.pdf", "sv-flatten.pdf"), ("rotated.pdf", "sv-rotated.pdf")):
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


def sv5_arrange():
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
    if not st["shelfVisible"] and st["shelfHead"]:
        tap_xy(st["shelfHead"]["x"], st["shelfHead"]["y"])
        time.sleep(1.5)
        st = cdp.js(BENCH)
    ours = [s for s in st["shelfVisible"]]
    start = len(st["order"])
    dropped = []
    for idx in (2, 0):          # shelf page 3, then page 1
        st = cdp.js(BENCH)
        if not st["shelfVisible"] and st["shelfHead"]:
            tap_xy(st["shelfHead"]["x"], st["shelfHead"]["y"])
            st = cdp.js(BENCH)
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
    picker = save_picker()
    time.sleep(3)
    files = new_pdfs()
    got = None
    if files:
        rd, pages = read(files[-1], "sv5-bound.pdf")
        got = [int(m.group(1)) if (m := re.search(r"- page (\d+)", t)) else None for t in pages]
    want = [3 if i == id_p3 else 1 for i in after][-2:] if id_p3 else None
    R.check("SV-5c bound PDF holds the desk's pages in the desk's order", bool(got and want and got[-len(want):] == want),
            {"button": hit, "picker": picker, "files": files, "saved_pages": got, "desk_order_as_pages": want, "app_says": says()})


def sv6_print():
    pick_open("sv-print.pdf")
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
    pick_open("sv-pass.pdf")
    mode("Protect")
    time.sleep(1)
    t = tool("Protect: Password", "Password", "Set a password", "Set password", "Encrypt") or doc_action("Password", "Set a password", "Protect with a password")
    time.sleep(1.5)
    ins = card_inputs()
    for f in [i for i in ins if i["type"] == "password"][:2]:
        tap_xy(f["x"], f["y"])
        sh("input text chuvadi1")
        time.sleep(0.6)
    sh("input keyevent KEYCODE_BACK")
    time.sleep(1)
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
            {"tool": t, "fields": ins, "card_buttons": btns, "button": hit, "picker": picker, "files": files, "pdf": res, "app_says": says()})
    R.check("SV-7b the picked original is still unencrypted", md5("sv-pass.pdf") == ORIG["sv-pass.pdf"], None)


def doc_save(case_id, name, action_labels, confirm_labels):
    pick_open(name)
    act = doc_action(*action_labels)
    time.sleep(2)
    shot(case_id.lower() + "-card")
    btns = card_buttons()
    mark_time()
    hit = None
    if not in_picker():
        hit = tap(*confirm_labels, sel=".chvd-card button, [role=dialog] button, .ph-sheet button")
        time.sleep(2)
    picker = save_picker()
    time.sleep(4)
    files = new_pdfs()
    res = None
    if files:
        rd, pages = read(files[-1], case_id.lower() + "-out.pdf")
        res = {"pages": len(pages), "text_p1": "Discharge summary - page 1" in pages[0], "bytes": os.path.getsize(os.path.join(OUT, case_id.lower() + "-out.pdf"))}
    R.check(f"{case_id} {action_labels[0]} → saved to a new file: readable, 12 pages, text kept",
            bool(res and res["pages"] == 12 and res["text_p1"]),
            {"action": act, "card_buttons": btns, "button": hit, "picker": picker, "files": files, "pdf": res, "app_says": says(), "controls": None if act else labels()})


def sv8_compress():
    doc_save("SV-8", "sv-compress.pdf", ("Compress", "Compress…"), ("Compress and save", "Compress", "Save"))


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


def sv11_excel():
    adb("push", os.path.join(FX, "test.xlsx"), "/sdcard/Download/sv-sheet.xlsx")
    sh("am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file:///sdcard/Download/sv-sheet.xlsx' >/dev/null")
    time.sleep(2)
    cdp.js("Blazor.navigateTo('/')")
    time.sleep(1.5)
    tap("Open a document", sel=".ph-fab") if phone() else tap("Choose a document to open", "Open (Ctrl O)", "Open")
    time.sleep(2.5)
    for _ in range(8):
        if ui_tap_text("sv-sheet.xlsx"):
            break
        if not (ui_tap_text("Download") or ui_tap_text("Downloads")):
            ui_tap_text("Show roots")
        time.sleep(1.5)
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



for name, fn in (("SV-1", sv1_text), ("SV-2", sv2_shape), ("SV-3", sv3_form), ("SV-4", sv4_redact), ("SV-7", sv7_password), ("SV-8", sv8_compress),
                 ("SV-9", sv9_flatten), ("SV-10", sv10_rotated), ("SV-11", sv11_excel), ("SV-6", sv6_print), ("SV-5", sv5_arrange)):
    case(name, fn)

log = adb("logcat", "-d", "-v", "epoch")
fatal = [l for l in log.splitlines() if "FATAL EXCEPTION" in l or f"ANR in {PKG}" in l]
R.check("R-10 no crash / ANR in the save suite", not fatal, fatal[:5])
