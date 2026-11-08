import glob
import os, sys, time, json, subprocess
sys.path.insert(0, "/home/claude/lx/tools/linux")
from uitest_lib import App
results=[]
OUT=os.environ.get("LT_OUT","/home/claude/evidence/lt/x"); CUPS_OUT="/root/PDF"
app=None
def bind(a):
    global app; app=a
VISIBLE = ("[...document.querySelectorAll(%s)].filter(b=>b.offsetParent!==null && !b.disabled)"
           ".map(b=>(b.getAttribute('aria-label')||b.title||b.innerText||'').trim().replace(/\\s+/g,' ').slice(0,48))")


def errors_in_log():
    return open(app.log_path, errors="replace").read().count("Chuvadi error")


def health(baseline):
    if not app.alive():
        raise AssertionError("the app exited")
    if app.error_ui_visible():
        raise AssertionError("Blazor's error bar is showing")
    if errors_in_log() != baseline:
        raise AssertionError("the app logged an error (see app.log)")


DIALOG_TITLES = ("Open", "Save", "Print", "Add ", "Choose", "Fetch")


def native_windows():
    """Open dialogs: GTK file dialogs (run by the desktop portal, another process) and the GTK print
    dialog (in the app). Matched by title, so the main window and the WM's own windows are left alone."""
    r = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "."], env=app.env, capture_output=True, text=True)
    found = []
    for w in r.stdout.split():
        n = subprocess.run(["xdotool", "getwindowname", w], env=app.env, capture_output=True, text=True).stdout.strip()
        if n.startswith(DIALOG_TITLES):
            g = subprocess.run(["xdotool", "getwindowgeometry", w], env=app.env, capture_output=True, text=True).stdout
            size = g.split("Geometry: ")[1].strip() if "Geometry: " in g else "0x0"
            wd, ht = (int(v) for v in size.split("x"))
            found.append((wd * ht, w, n))
    # the portal can map a small helper window with the same title: largest first
    return [(w, n) for _, w, n in sorted(found, reverse=True)]


def focus_main():
    w = app.windows("^Chuvadi$")
    if w:
        subprocess.run(["xdotool", "windowactivate", "--sync", w[0]], env=app.env, capture_output=True)
        time.sleep(0.3)


def dismiss():
    """Closes any dialog, card, menu or command bar a step left open (real keys to the main window)."""
    for w, _ in native_windows():
        subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
        app.key("Escape")
        time.sleep(0.6)
    focus_main()
    try:
        # Only the app's cards — never the window's own Close button (.tl-close).
        app.js("var c=[...document.querySelectorAll('.chvd-card .close, .card-close')].filter(b=>b.offsetParent!==null && !b.closest('.traffic')); c.forEach(b=>b.click()); return c.length")
    except Exception:
        pass
    app.key("Escape", "Escape")
    try:
        # A click on the status bar's empty end closes menus and popovers.
        r = app.rect(".statusbar") or app.rect(".shell")
        app.mouse_click(r[0] + r[2] * 0.6, r[1] + r[3] / 2)
    except Exception:
        pass
    time.sleep(0.3)


def ensure_reader(mode=0):
    """Back to five-pages.pdf in the reader (mode 0 Read, 1 Mark, 3 Protect)."""
    on_pdf = app.js("var t=[...document.querySelectorAll('.rtab')].find(t=>t.innerText.includes('five-pages.pdf')); if(!t) return false; t.click(); return true")
    time.sleep(1.2)
    if not on_pdf or not app.js("return location.pathname === '/reader' && !!document.querySelector('.tb-pager input') && document.querySelector('.tb-pager').innerText.includes('5')"):
        app.open(PDF)
        app.wait(lambda: app.exists(".tb-doc"), 20, "reader")
        time.sleep(1.5)
    app.click(".lb-mode", mode)
    time.sleep(1.5)


def type_into(selector, text, index=0):
    """Real typing into a field; checks the value arrived (a stray key would trigger a shortcut)."""
    focus_main()
    app.click_real(selector, index)
    app.key("ctrl+a")
    app.type(text)
    time.sleep(0.4)
    got = app.js(f"return document.querySelectorAll({json.dumps(selector)})[{index}].value")
    if got != text:
        raise AssertionError(f"typed {text!r} into {selector}, field has {got!r}")


def step(name, fn, shot=True):
    baseline = errors_in_log()
    t0 = time.time()
    try:
        detail = fn() or ""
        if shot:
            app.shot(name)
        health(baseline)
        results.append({"step": name, "ok": True, "detail": str(detail), "s": round(time.time() - t0, 1)})
        print("PASS", name, detail)
    except Exception as ex:  # record and carry on with the next step
        try:
            app.shot(name + "-FAIL")
        except Exception:
            pass
        results.append({"step": name, "ok": False, "detail": f"{type(ex).__name__}: {ex}", "s": round(time.time() - t0, 1)})
        print("FAIL", name, ex)
        traceback.print_exc(limit=2)
    if app.alive():
        dismiss()


def visible(selector):
    return app.js("return " + VISIBLE % json.dumps(selector))


def click_label(scope, label):
    ok = app.js(f"var b=[...document.querySelectorAll({json.dumps(scope + ' button')})].filter(b=>b.offsetParent!==null && (b.getAttribute('aria-label')||b.title||b.innerText||'').trim().replace(/\\s+/g,' ').startsWith({json.dumps(label)}))[0]; if(!b) return false; b.click(); return true;")
    if not ok:
        raise AssertionError(f"no button '{label}' in {scope}")
    time.sleep(0.8)


def file_dialog(title_part, path, timeout=15):
    """Answers a GTK file dialog by typing a full path (Ctrl L, path, Enter)."""
    w = app.wait(lambda: [x for x in native_windows() if title_part.lower() in x[1].lower()], timeout, "dialog " + title_part)[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(0.8)
    app.shot("dialog-" + title_part.replace(" ", "-").lower())
    app.key("ctrl+l")
    time.sleep(0.3)
    app.key("ctrl+a")
    app.type(path)
    time.sleep(0.4)
    app.key("Return")
    time.sleep(1.2)


def go_home():
    app.click(".tb-brand")
    time.sleep(1)


def open_pdf_via_rail():
    app.click(".leftbar .lb-btn", 4)  # Open
    file_dialog("Open a document", PDF)
    app.wait(lambda: app.js("return [...document.querySelectorAll('.rtab')].some(t=>t.innerText.includes('five-pages.pdf'))"), 20, "tab five-pages.pdf")
    time.sleep(2)
    return "opened through the GTK file dialog"


def window_geometry():
    w = app.windows("^Chuvadi$")[0]
    out = subprocess.run(["xdotool", "getwindowgeometry", w], env=app.env, capture_output=True, text=True).stdout
    pos = out.split("Position: ")[1].split(" ")[0]
    size = out.split("Geometry: ")[1].strip()
    return pos, size


def cups_pdfs(since=0.0):
    """PDFs the CUPS PDF queue wrote after `since` (by modification time: cups-pdf reuses the job's file name)."""
    roots = [CUPS_OUT] if CUPS_OUT else []
    roots += [os.path.expanduser("~/PDF"), app.home + "/PDF", "/var/spool/cups-pdf/ANONYMOUS"]
    roots += glob.glob("/home/*/PDF") + glob.glob("/root/PDF")
    files = set()
    for r in roots:
        files.update(f for f in glob.glob(os.path.join(r, "*.pdf")) if os.path.getmtime(f) > since)
    return files


def pdfinfo(path):
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    return {l.split(":", 1)[0].strip(): l.split(":", 1)[1].strip() for l in out.splitlines() if ":" in l}


