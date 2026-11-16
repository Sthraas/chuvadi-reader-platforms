# Patch 29 on Linux: marks kept with their tab; the ask-before-closing card (Save / Save as / Discard / Cancel) on a
# tab's x, Close all tabs, Close inactive tabs and the window; Excel resize by dragging; the title bar's sheet pager.
# Usage: t_patch29.py <work dir> <mark-rot.pdf> <layout.xlsx> <part: tabs|close|window|excel>
import helpers as h, json, hashlib, shutil
from lt_base import *
WORK, SRC, XLSX, PART = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(WORK, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def fresh(*names):
    out = []
    for n in names:
        p = os.path.join(WORK, n); shutil.copyfile(SRC, p); out.append(p)
    return out
a = App(APP, EV + f"/patch29-{PART}", display=f":{ {'tabs': 91, 'close': 92, 'window': 93, 'excel': 94}[PART] }"); h.bind(a); a.start_display()
shapes = lambda: a.js("return [...document.querySelectorAll('.mk-layer .mk-shape')].map(e=>{var b=e.getBoundingClientRect(), p=e.closest('.rpage-wrap').querySelector('.rpage').getBoundingClientRect(); return [Math.round(b.left-p.left), Math.round(b.top-p.top), Math.round(b.width), Math.round(b.height)]})")
tabs = lambda: a.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())")
card = lambda: a.js("var c=document.querySelector('.closeq'); return c ? {title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\\s+/g,' ').trim(), buttons: [...c.querySelectorAll('button')].map(b => b.textContent.trim())} : null")
def open_tab(path):
    n = os.path.basename(path); a.send("open " + path, timeout=15)
    a.wait(lambda: a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{n}')"), 30, n); time.sleep(2)
def show(name):
    a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.click(); return 1"); time.sleep(1.8)
def mark_mode():
    if not a.js("return [...document.querySelectorAll('.srail button')].some(b => b.offsetParent && (b.getAttribute('aria-label')||'').startsWith('Rectangle'))"):
        a.click(".lb-mode", 1); time.sleep(1.3)
def draw(dx=0):
    mark_mode(); h.click_label(".srail", "Rectangle"); h.focus_main()
    pr = a.js("var r=document.querySelector('.rpage-wrap[data-page=\"0\"] .rpage').getBoundingClientRect(); return [r.left,r.top,r.width,r.height]")
    x, y = int(pr[0] + 120 + dx), int(pr[1] + 140); n = len(shapes())
    a.xdo("mousemove", str(x), str(y)); a.xdo("mousedown", "1")
    for i in range(1, 9): a.xdo("mousemove", str(x + 14 * i), str(y + 9 * i)); time.sleep(0.04)
    a.xdo("mouseup", "1"); time.sleep(0.7); a.key("Escape"); time.sleep(0.3)
    assert len(shapes()) == n + 1, "rectangle not drawn"
    return [x - int(pr[0]), y - int(pr[1]), 112, 72], pr
def close_x(name):
    a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.querySelector('.rtab-x').click(); return 1"); time.sleep(1.2)
def answer(label):
    ok = a.js(f"var b=[...document.querySelectorAll('.closeq button')].find(b => b.textContent.trim() === '{label}'); if (!b) return false; b.click(); return true"); time.sleep(1.5); return ok
def alive(): return a.proc.poll() is None
def P(*x): print(*x, flush=True)
try:
    a.launch(); time.sleep(3)
    if PART == "tabs":
        fa, fb = fresh("tab-a.pdf", "tab-b.pdf"); open_tab(fa); open_tab(fb); show("tab-a.pdf")
        exp, pr = draw(); sa = shapes(); show("tab-b.pdf"); mark_mode(); sb0 = shapes(); draw(200); draw(330); sb = shapes()
        show("tab-a.pdf"); sa2 = shapes(); show("tab-b.pdf"); sb2 = shapes()
        P("TABS a: drawn at", exp, "-> shown", sa, "| b before drawing:", sb0, "| b after two:", sb)
        P("TABS back on a:", sa2, "same as before:", sa2 == sa, "| back on b:", sb2, "same:", sb2 == sb)
        a.click(".lb-mode", 0); time.sleep(1.2); a.click(".lb-mode", 1); time.sleep(1.2); P("TABS b after Read and back to Mark:", shapes() == sb)
        btnz = lambda lab: (a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')=='{lab}'&&b.offsetParent); b.click(); return 1"), time.sleep(1))
        show("tab-a.pdf"); btnz("Zoom in"); z = shapes(); show("tab-b.pdf"); show("tab-a.pdf")
        P("TABS a zoomed in, then away and back:", z, "->", shapes(), "same:", shapes() == z, "| zoom", a.js("var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)&&e.offsetParent); return z?z.innerText:''"))
        P("TABS files untouched:", sha(fa) == sha(SRC), sha(fb) == sha(SRC))
    if PART == "close":
        fa, fb, fc, fd, fe = fresh("c-cancel.pdf", "c-discard.pdf", "c-save.pdf", "c-saveas.pdf", "c-clean.pdf")
        open_tab(fe); n = len(tabs()); close_x("c-clean.pdf"); P("CLEAN tab (no marks) closes without asking:", card() is None and len(tabs()) == n - 1)
        open_tab(fa); draw(); close_x("c-cancel.pdf"); c = card(); P("CARD on a tab's x:", json.dumps(c))
        answer("Cancel"); P("Cancel -> tab kept:", "c-cancel.pdf" in tabs(), "| mark kept:", len(shapes()) == 1, "| card gone:", card() is None)
        close_x("c-cancel.pdf"); a.key("Escape"); time.sleep(1); P("Escape -> tab kept:", "c-cancel.pdf" in tabs(), "| mark kept:", len(shapes()) == 1, "| card gone:", card() is None)
        open_tab(fb); draw(); close_x("c-discard.pdf"); answer("Discard"); P("Discard -> tab closed:", "c-discard.pdf" not in tabs(), "| file byte-identical:", sha(fb) == sha(SRC))
        open_tab(fb); mark_mode(); P("Discard -> reopened: marks shown:", len(shapes()))
        close_x("c-discard.pdf"); P("  reopened tab closes without asking:", card() is None)
        open_tab(fc); exp, pr = draw(); close_x("c-save.pdf"); answer("Save"); time.sleep(2)
        P("Save -> tab closed:", "c-save.pdf" not in tabs(), "| file changed:", sha(fc) != sha(SRC), "| card:", card(), "| expected page pts", [round(exp[0] / pr[2] * 595), round(exp[1] / pr[3] * 842), round((exp[0] + exp[2]) / pr[2] * 595), round((exp[1] + exp[3]) / pr[3] * 842)], "| OUTFILE", fc)
        open_tab(fd); exp, pr = draw(60); close_x("c-saveas.pdf"); answer("Save as…"); out = os.path.join(WORK, "c-saveas-copy.pdf")
        if os.path.exists(out): os.remove(out)
        try: h.file_dialog("Save", out); time.sleep(2.5)
        except Exception as e: P("Save as: dialog problem", str(e)[:120])
        P("Save as -> copy written:", os.path.exists(out) and sha(out) != sha(SRC), "| original untouched:", sha(fd) == sha(SRC), "| tab closed:", "c-saveas.pdf" not in tabs(), "| tabs", tabs(), "| card:", card(), "| OUTFILE2", out)
        # Close all / Close inactive with one dirty tab
        open_tab(fe); show("c-cancel.pdf"); h.focus_main(); a.xdo("key", "ctrl+shift+w"); time.sleep(1.5); c = card()
        P("CLOSE ALL (Ctrl Shift W) asks:", json.dumps(c)); answer("Cancel"); P("  Cancel -> tabs kept:", tabs())
        show("c-clean.pdf"); h.focus_main(); a.xdo("key", "ctrl+alt+w"); time.sleep(1.5); c = card()
        P("CLOSE INACTIVE (Ctrl Alt W) asks:", json.dumps(c), "| page shows marks:", len(shapes())); answer("Cancel"); P("  Cancel -> tabs kept:", tabs(), "| tab now shown:", a.js("return document.querySelector('.rtab.active .rtab-name').textContent.trim()"))
        show("c-clean.pdf"); h.focus_main(); a.xdo("key", "ctrl+alt+w"); time.sleep(1.5); answer("Discard"); c = card(); P("  Discard on file 1 -> next question:", json.dumps(c)); answer("Discard"); P("  Discard on file 2 -> tabs:", tabs(), "| both files byte-identical:", sha(fa) == sha(SRC), sha(fd) == sha(SRC))
    if PART == "window":
        fa, fb, fc = fresh("w-one.pdf", "w-two.pdf", "w-clean.pdf"); open_tab(fc); open_tab(fa); draw(); open_tab(fb); draw(80); show("w-clean.pdf")
        h.focus_main(); a.xdo("key", "alt+F4"); time.sleep(2); c = card(); P("WINDOW Alt F4 asks:", json.dumps(c), "| app alive:", alive())
        a.xdo("key", "alt+F4"); time.sleep(1.5); P("  second Alt F4 while asked: alive", alive(), "| cards:", a.js("return document.querySelectorAll('.closeq').length"))
        answer("Cancel"); P("  Cancel -> alive:", alive(), "| tabs:", tabs())
        a.click(".tl-close") if a.js("return !!document.querySelector('.tl-close')") else None; time.sleep(2); c = card(); P("WINDOW title-bar close asks:", json.dumps(c), "| alive:", alive())
        first = c["title"] if c else ""; answer("Save"); time.sleep(1.5); c2 = card(); P("  Save on the first -> next question:", json.dumps(c2), "| alive:", alive())
        answer("Discard"); time.sleep(3); P("  Discard on the second -> app exited:", not alive(), "code", a.proc.poll())
        P("  files: w-one changed", sha(fa) != sha(SRC), "| w-two changed", sha(fb) != sha(SRC), "| w-clean untouched", sha(fc) == sha(SRC), "| first asked:", first, "| OUTFILE", fa, "| OUTFILE", fb)
    if PART == "excel":
        fx = os.path.join(WORK, "resize.xlsx"); shutil.copyfile(XLSX, fx); a.send("open " + fx, timeout=20); time.sleep(4)
        hdr = lambda sel: a.js(f"var e=document.querySelector('{sel}'); if(!e) return null; var b=e.getBoundingClientRect(); return [Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height), e.className]")
        cells = lambda: a.js("return [...document.querySelectorAll('.xv-cell[data-a]')].map(c=>c.getAttribute('data-a')+'='+c.innerText.trim()).join('|')")
        def drag(x, y, dx, dy):
            a.xdo("mousemove", str(x), str(y)); time.sleep(0.2); a.xdo("mousedown", "1")
            for i in range(1, 9): a.xdo("mousemove", str(int(x + dx * i / 8)), str(int(y + dy * i / 8))); time.sleep(0.04)
            a.xdo("mouseup", "1"); time.sleep(1)
        c0 = cells(); b = hdr('.xv-colhdr[data-c="4"]'); P("EXCEL col D header before:", b, "| reset button:", a.js("return document.querySelectorAll('.xv-resetsizes').length"))
        drag(b[0] + b[2] - 1, b[1] + b[3] // 2, 60, 0); b2 = hdr('.xv-colhdr[data-c="4"]'); P("EXCEL col D after dragging its right edge +60:", b2[2], "(was", b[2], ")", b2[4], "| reset button:", a.js("var e=document.querySelector('.xv-resetsizes'); return e?e.innerText.trim():null"))
        r = hdr('.xv-rowhdr[data-r="8"]'); drag(r[0] + r[2] // 2, r[1] + r[3] - 1, 0, 30); r2 = hdr('.xv-rowhdr[data-r="8"]'); P("EXCEL row 8 after dragging its bottom edge +30:", r2[3], "(was", r[3], ")", r2[4])
        P("EXCEL cell texts unchanged:", cells() == c0, "| file byte-identical:", sha(fx) == sha(XLSX))
        a.js("document.querySelectorAll('.xv-tab')[1].click(); return 1"); time.sleep(1.2); P("EXCEL other sheet: reset button:", a.js("return document.querySelectorAll('.xv-resetsizes').length"))
        a.js("document.querySelectorAll('.xv-tab')[0].click(); return 1"); time.sleep(1.2); P("EXCEL back on sheet 1: col D", hdr('.xv-colhdr[data-c="4"]')[2], "row 8", hdr('.xv-rowhdr[data-r="8"]')[3])
        n = len(tabs()); close_x("resize.xlsx"); P("EXCEL closing after a resize asks nothing:", card() is None and len(tabs()) == n - 1)
        a.send("open " + fx, timeout=20); time.sleep(4); P("EXCEL reopened: col D", hdr('.xv-colhdr[data-c="4"]')[2], "row 8", hdr('.xv-rowhdr[data-r="8"]')[3], "| reset button:", a.js("return document.querySelectorAll('.xv-resetsizes').length"))
        if a.js("return document.querySelectorAll('.xv-resetsizes').length"):
            a.js("document.querySelector('.xv-resetsizes').click(); return 1"); time.sleep(1); P("EXCEL after File's own sizes: col D", hdr('.xv-colhdr[data-c="4"]')[2], "row 8", hdr('.xv-rowhdr[data-r="8"]')[3])
        st = lambda: a.js("return [document.querySelector('.tb-pg-box').value, (document.querySelector('.tb-pg-total')||{}).textContent, [...document.querySelectorAll('.xv-tab')].filter(t=>t.classList.contains('on')||t.classList.contains('active')||t.getAttribute('aria-selected')=='true').map(t=>t.innerText.trim().split(/\\s+/)[0]), (document.querySelector('.xv-cell[data-a=\"A1\"]')||{innerText:''}).innerText.trim()]")
        P("PAGER start:", st())
        for lab in ("Next", "Next", "Previous"):
            a.js(f"var b=document.querySelector('.tb-pager button[aria-label^=\"{lab}\"]'); b.click(); return 1"); time.sleep(1.2); P(f"PAGER {lab}:", st())
        a.js("var b=document.querySelector('.tb-pg-box'); b.value='1'; b.dispatchEvent(new Event('change')); return 1"); time.sleep(1.2); P("PAGER box = 1:", st())
finally:
    try: a.stop()
    except Exception: pass
