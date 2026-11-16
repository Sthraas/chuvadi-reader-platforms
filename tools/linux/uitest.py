#!/usr/bin/env python3
"""Full Linux UI test pass for Chuvadi Reader (test-only, never shipped).

  tools/linux/uitest.py <ui-test publish dir> <out dir> [--cups-out DIR]

Needs: Xvfb, mutter, xdotool, xclip, ImageMagick (import), poppler-utils (pdfinfo, pdffonts,
pdfimages), a CUPS queue that is the default destination and writes PDFs (cups-pdf), all test tools.
Writes <out>/report.md, <out>/results.json and one screenshot per step.
Every step also checks: the app is running, Blazor's error bar is hidden, and no new "Chuvadi error"
is in the app log.
"""
import glob, json, os, re, subprocess, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, OUT = sys.argv[1], sys.argv[2]
CUPS_OUT = sys.argv[sys.argv.index("--cups-out") + 1] if "--cups-out" in sys.argv else None
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(OUT, "fixtures")
subprocess.run([sys.executable, "-I", os.path.join(HERE, "make-fixtures.py"), FIX], check=True, stdout=subprocess.DEVNULL)
PDF = os.path.join(FIX, "five-pages.pdf")

app = App(APP_DIR, OUT)
results = []
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


# UITEST_ONLY="34e,34f": run only steps whose names start with one of these (re-checking a fix quickly);
# the app's start-up steps (01-…) always run. Unset in CI: every step runs.
ONLY = [p for p in os.environ.get("UITEST_ONLY", "").split(",") if p]


def step(name, fn, shot=True):
    if ONLY and not name.startswith("01") and not any(name.startswith(p) for p in ONLY):
        return
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


# ─────────────────────────────────────────────────────────────────────────────
app.start_display()
t_launch = time.time()
app.launch()
results.append({"step": "launch", "ok": True, "detail": f"first render after {time.time() - t_launch:.1f} s (cold, fresh profile)", "s": 0})
app.shot("01-home")


def start_mark_gone():
    """The start-up mark covers the page from the window's first frame to the app's first render, then goes:
    it must never be left over the app."""
    app.wait(lambda: app.send("start-mark") is False, 3, "the start-up mark to go after the first render")
    return "gone after the first render"


step("01b-start-mark-gone", start_mark_gone, shot=False)

# ── chrome ───────────────────────────────────────────────────────────────────
step("02-theme-toggle", lambda: (app.click(".tb-icon"), time.sleep(1),
                                 f"data-theme={app.js('return document.documentElement.dataset.theme')}")[-1])
step("03-theme-back", lambda: (app.click(".tb-icon"), time.sleep(1),
                               f"data-theme={app.js('return document.documentElement.dataset.theme')}")[-1])


def restore_and_maximise():
    before = window_geometry()
    app.click(".tl-max")
    time.sleep(1.5)
    restored = window_geometry()
    if restored == before:
        raise AssertionError(f"window did not restore ({before})")
    app.shot("04-restored")
    label = app.js("return document.querySelector('.tl-max').getAttribute('aria-label')")
    # drag the top bar with a real pointer: the window must move
    r = app.rect(".topbar")
    x0, y0 = int(r[0] + 700), int(r[1] + 12)
    w = app.windows("^Chuvadi$")[0]
    wx, wy = map(int, restored[0].split(","))
    sx, sy = wx + x0, wy + y0
    app.xdo("mousemove", str(sx), str(sy))
    app.xdo("mousedown", "1")
    for i in range(1, 11):
        app.xdo("mousemove", str(sx + i * 15), str(sy + i * 8))
        time.sleep(0.05)
    app.xdo("mouseup", "1")
    time.sleep(1)
    moved = window_geometry()
    if moved[0] == restored[0]:
        raise AssertionError(f"dragging the top bar did not move the window ({restored[0]})")
    # double-click the top bar: maximise
    app.mouse_click(sx + 150, sy + 80, double=True)
    time.sleep(1.5)
    maxed = window_geometry()
    return f"maximised {before} → restored {restored} (button says '{label}') → dragged to {moved[0]} → double-click → {maxed}"


step("04-window-restore-drag-maximise", restore_and_maximise)


def wm_state():
    w = subprocess.run(["xdotool", "search", "--name", "^Chuvadi$"], env=app.env, capture_output=True, text=True).stdout.split()[0]
    return w, subprocess.run(["xprop", "-id", w, "WM_STATE", "_NET_WM_STATE"], env=app.env, capture_output=True, text=True).stdout


def minimise():
    app.click(".tl-min")
    time.sleep(1.5)
    w, state = wm_state()
    # A compositing WM (mutter) keeps minimised windows mapped; the WM state says what happened.
    if "Iconic" not in state or "_NET_WM_STATE_HIDDEN" not in state:
        raise AssertionError("window not minimised: " + state.replace("\n", " "))
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(1.5)
    _, after = wm_state()
    if "Iconic" in after:
        raise AssertionError("window didn't come back")
    return "Minimize → WM state Iconic + _NET_WM_STATE_HIDDEN; raised again → Normal"


step("05-window-minimise", minimise)

# ── left rail and pages ─────────────────────────────────────────────────────
for i, name in [(6, "library"), (8, "settings"), (7, "home")]:
    step(f"06-rail-{name}", lambda i=i: (app.click(".leftbar .lb-btn", i), time.sleep(1.5), app.js("return location.pathname"))[-1])
step("07-rail-collapse", lambda: (app.click(".lb-toggle"), time.sleep(1), app.shot("07-collapsed"), app.click(".lb-toggle"), time.sleep(1), "collapsed and expanded")[-1], shot=False)


def settings_pages():
    app.click(".leftbar .lb-btn", 8)
    time.sleep(1.5)
    labels = app.js("return [...document.querySelectorAll('.snav-item')].map(b=>b.innerText.trim().replace(/\\s+/g,' '))")
    for idx in range(len(labels)):
        app.click(".snav-item", idx)
        time.sleep(0.8)
        app.shot(f"08-settings-{idx:02d}")
    return f"{len(labels)} sections: " + ", ".join(labels)


step("08-settings-sections", settings_pages, shot=False)


def themes():
    app.click(".leftbar .lb-btn", 8)
    time.sleep(1)
    app.click(".snav-item", 0)
    names = app.js("return [...document.querySelectorAll('.tc')].map(b=>b.innerText.trim().split('\\n')[0])")
    seen = []
    for idx, name in enumerate(names):
        app.click(".tc", idx)
        time.sleep(1)
        app.shot(f"09-theme-{idx}")
        seen.append(f"{name}={app.js('return document.documentElement.dataset.theme')}")
    app.click(".tc", 0)
    return ", ".join(seen)


step("09-themes", themes, shot=False)


def interface_size():
    app.click(".leftbar .lb-btn", 8)
    time.sleep(1)
    app.click(".snav-item", 0)
    out = []
    for size in ("125%", "150%", "100%"):
        idx = app.js(f"return [...document.querySelectorAll('.seg-opt')].findIndex(b=>b.innerText.trim()==='{size}')")
        if idx < 0:
            raise AssertionError(size + " option not found")
        app.click(".seg-opt", idx)
        time.sleep(1.2)
        app.shot(f"09-scale-{size[:-1]}")
        out.append(f"{size}: topbar height {app.rect('.topbar')[3]:.0f} px")
    return ", ".join(out)


step("09-interface-size", interface_size, shot=False)
go_home()

# ── open through the native dialog ──────────────────────────────────────────
step("10-open-pdf-gtk-dialog", open_pdf_via_rail)
step("11-pager-next", lambda: (app.click(".tb-pg-btn", 1), time.sleep(1),
                              f"page box = {app.js('return document.querySelector(\".tb-pager input\").value')}")[-1])
step("12-pager-prev", lambda: (app.click(".tb-pg-btn", 0), time.sleep(1),
                              f"page box = {app.js('return document.querySelector(\".tb-pager input\").value')}")[-1])


def rail_buttons(prefix, skip=()):
    labels = visible(".srail button")
    for idx, label in enumerate(labels):
        if any(label.startswith(s) for s in skip):
            continue
        step(f"{prefix}-{idx:02d}-{label[:24].replace(' ', '-').replace('/', '-').lower()}",
             lambda label=label: (click_label(".srail", label), time.sleep(0.6), label)[-1])
    return labels


rail_buttons("13-read", skip=("Print", "Immersive"))
for idx, label in enumerate(["Rotate this page", "Snapshot a region", "Bookmark this page"]):
    step(f"14-pagestrip-{idx}", lambda label=label: (click_label(".pstrip", label), label)[-1])


def doc_menu_item(label):
    ensure_reader()
    app.click(".tb-doc")
    time.sleep(0.5)
    click_label(".pop", label)
    time.sleep(1)
    return label


for label in ["Properties", "Export pages as images", "Reduce file size (Press)", "Flatten forms & marks",
              "Password-protect a copy", "Merge files", "Split pages", "Tags"]:
    step(f"15-docmenu-{label[:20].replace(' ', '-').lower()}", lambda label=label: doc_menu_item(label))


def copy_path():
    doc_menu_item("Copy file path")
    time.sleep(0.5)
    got = subprocess.run(["xclip", "-o", "-selection", "clipboard"], env=app.env, capture_output=True, text=True, timeout=5).stdout
    if got.strip() != PDF:
        raise AssertionError(f"clipboard has {got!r}, expected the file path")
    return "clipboard = " + got.strip()


step("16-copy-file-path-clipboard", copy_path)
step("17-show-in-folder", lambda: (doc_menu_item("Show in folder"), "no file manager in the test session: fallback ran, no crash")[-1])
step("18-tab-menu", lambda: (app.click(".rtabs-menu"), time.sleep(0.6), app.shot("18-tab-menu-open"), "; ".join(visible(".pop button")))[-1], shot=False)

# ── command bar: every command the app offers ───────────────────────────────
step("19-command-bar-ctrl-k", lambda: (app.key("ctrl+k"), time.sleep(1), app.shot("19-command-bar"),
                                       f"{app.js('return document.querySelectorAll(\".cmdk *[role=option], .cmd-item, .cb-item\").length')} items")[-1], shot=False)


def every_command():
    done, skipped = [], []
    ensure_reader()
    for c in app.commands():
        cid = c["Id"]
        if cid in ("doc.close", "r.print", "r.immersive", "doc.reveal", "doc.copypath") or not c["Enabled"]:
            skipped.append(cid)
            continue
        baseline = errors_in_log()
        ok = app.invoke(cid)
        time.sleep(1.0)
        app.shot("20-cmd-" + cid.replace(".", "-"))
        health(baseline)
        dismiss()
        ensure_reader()
        done.append(f"{cid}:{'dialog' if ok == 'pending' else ('ran' if ok else 'refused')}")
    return f"{len(done)} run ({', '.join(done)}); skipped here (tested on their own or disabled): {', '.join(skipped)}"


step("20-every-command", every_command, shot=False)

# ── functional checks on a fresh process: the sweep above toggled every View tool ──
app.restart()
results.append({"step": "restart", "ok": True, "detail": "fresh process and profile for the functional checks", "s": 0})
MARKED_DIR = app.home

# ── Mark: draw a rectangle, Save as new PDF through the GTK dialog, then Save ──
MARKED = os.path.join(MARKED_DIR, "Documents", "marked.pdf")


def mark_and_save_as():
    ensure_reader(1)
    rail_labels = visible(".srail button")
    click_label(".srail", "Rectangle")
    focus_main()
    r = app.rect(".rpage-wrap", 0)
    x, y = r[0] + r[2] * 0.3, r[1] + r[3] * 0.25
    app.xdo("mousemove", str(int(x)), str(int(y)))
    app.xdo("mousedown", "1")
    for i in range(1, 12):
        app.xdo("mousemove", str(int(x + i * 18)), str(int(y + i * 10)))
        time.sleep(0.04)
    app.xdo("mouseup", "1")
    time.sleep(1)
    app.shot("21-mark-rectangle")
    status = app.text(".statusbar")
    if "1 shape" not in status:
        raise AssertionError("rectangle not drawn; status bar: " + status.replace("\n", " "))
    click_label(".srail", "Save as new PDF")
    file_dialog("Save", MARKED)
    app.wait(lambda: os.path.exists(MARKED) and os.path.getsize(MARKED) > 0, 20, "marked.pdf written")
    info = pdfinfo(MARKED)
    annots = open(MARKED, "rb").read().count(b"/Annot")
    return f"Mark rail: {len(rail_labels)} tools; saved {os.path.getsize(MARKED)} bytes, {info.get('Pages')} pages, /Annot x{annots}"


step("21-mark-rectangle-save-as", mark_and_save_as)
rail_buttons("22-mark", skip=("Save", "Clear all marks", "Image", "Signature"))

# ── Protect: password-protect a copy, open it again with the password ───────
PROTECTED = os.path.join(MARKED_DIR, "Documents", "protected.pdf")


def protect_copy():
    ensure_reader(3)
    click_label(".srail", "Password")
    time.sleep(1)
    app.shot("23-password-card")
    field = ".chvd-card input[autocomplete=new-password]"
    pw = app.js(f"return document.querySelectorAll({json.dumps(field)}).length")
    if pw < 2:
        raise AssertionError(f"expected the password and confirm fields, found {pw}")
    for idx in range(pw):
        type_into(field, "Chuvadi-Linux-1", idx)
    time.sleep(0.5)
    app.shot("23-password-filled")
    btn = app.js("var b=[...document.querySelectorAll('.chvd-card button.primary, .card button.primary')].filter(b=>b.offsetParent!==null)[0]; if(!b) return null; var t=b.innerText; b.click(); return t")
    file_dialog("Save", PROTECTED)
    app.wait(lambda: os.path.exists(PROTECTED) and os.path.getsize(PROTECTED) > 0, 20, "protected.pdf written")
    no_pw = subprocess.run(["pdfinfo", PROTECTED], capture_output=True, text=True)
    with_pw = subprocess.run(["pdfinfo", "-upw", "Chuvadi-Linux-1", PROTECTED], capture_output=True, text=True).stdout
    enc = next((l.split(":", 1)[1].strip() for l in with_pw.splitlines() if l.startswith("Encrypted")), "?")
    if no_pw.returncode == 0 or not enc.startswith("yes"):
        raise AssertionError(f"expected a file that needs the password; without it rc={no_pw.returncode}, with it Encrypted: {enc}")
    return f"'{btn}' → protected.pdf: won't open without the password; with it: Encrypted: {enc}"


step("23-protect-password-copy", protect_copy)
rail_buttons("24-protect", skip=("Password", "Save redacted copy", "Sign with certificate"))

# ── Arrange (bench) ─────────────────────────────────────────────────────────
step("25-arrange", lambda: (app.click(".lb-mode", 2), time.sleep(2.5), "; ".join(visible(".srail button")))[-1])


def bench_fetch():
    click_label(".srail", "Fetch file")
    file_dialog("Add PDF documents", PDF)
    app.wait(lambda: "five-pages.pdf" in (app.text(".bench-shelf") or ""), 15, "file on the shelf")
    time.sleep(1.5)
    thumbs = app.js("return [...document.querySelectorAll('.bench-shelf .shelf-pg')].filter(e=>e.offsetParent!==null).length")
    if thumbs < 5:
        raise AssertionError(f"shelf shows {thumbs} page thumbnails, expected 5")
    return f"five-pages.pdf on the shelf with {thumbs} page thumbnails"


step("26-arrange-fetch-gtk-dialog", bench_fetch)
rail_buttons("27-arrange", skip=("Fetch file", "Reset bench", "Session", "Bind all", "Combine into one"))

# ── Word and Excel viewers ──────────────────────────────────────────────────
go_home()


def open_and_check(path, needle, name):
    app.click(".leftbar .lb-btn", 4)
    file_dialog("Open a document", path)
    app.wait(lambda: app.js(f"return document.body.innerText.includes({json.dumps(needle)}) || [...document.querySelectorAll('iframe')].some(f=>{{try{{return f.contentDocument.body.innerText.includes({json.dumps(needle)})}}catch(e){{return false}}}})"), 25, needle)
    time.sleep(1.5)
    return f"{name} shows '{needle}'"


step("28-open-docx", lambda: open_and_check(os.path.join(FIX, "sample.docx"), "Chuvadi Linux test document", "Word viewer"))
step("29-open-xlsx", lambda: open_and_check(os.path.join(FIX, "sample.xlsx"), "Copies", "Excel viewer"))

# ── print: Print card → GTK print dialog → CUPS (the PDF as-is) ─────────────


def print_pages():
    started = time.time()
    ensure_reader(0)
    focus_main()
    app.key("ctrl+p")
    time.sleep(1.2)
    app.shot("30-print-card")
    # pages 2-4, two copies
    card = "section[aria-label=Print]"
    app.click(card + " .seg button", 2)  # Custom
    type_into(card + " input[type=text]", "2-4")
    app.click(card + " [aria-label='More copies']")
    copies = app.text(card + " .count")
    if copies != "2":
        raise AssertionError("copies shows " + str(copies))
    app.shot("30-print-card-filled")
    app.click(card + " button.primary")
    w = app.wait(lambda: [x for x in native_windows() if x[1].startswith("Print")], 15, "GTK print dialog")[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(3)  # printers load asynchronously
    app.shot("30-gtk-print-dialog")
    app.key("Return")
    new = app.wait(lambda: cups_pdfs(started), 60, "cups-pdf output")
    out = sorted(new, key=os.path.getmtime)[-1]
    time.sleep(1)
    info = pdfinfo(out)
    fonts = subprocess.run(["pdffonts", out], capture_output=True, text=True).stdout.strip().splitlines()[2:]
    images = subprocess.run(["pdfimages", "-list", out], capture_output=True, text=True).stdout.strip().splitlines()[2:]
    text = subprocess.run(["pdftotext", "-layout", out, "-"], capture_output=True, text=True).stdout
    pages_seen = [n for n in range(1, 6) if f"Page {n}" in text]
    status = app.wait(lambda: app.js("var t=document.body.innerText; var m=t.match(/Sent \\d+ pages? to the printer/); return m ? m[0] : null"), 10, "toast")
    if images:
        raise AssertionError("printed output contains images — not vector: " + "; ".join(images))
    if pages_seen != [2, 3, 4]:
        raise AssertionError(f"printed pages {pages_seen}, expected [2, 3, 4]")
    # B-14: page 4 is landscape. With the dialog's orientation left as it is, CUPS must turn it to fill the
    # portrait sheet (rotation 90), not print it at half size unturned.
    rotations = []
    for n in range(1, int(info.get("Pages", "0")) + 1):
        page_text = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), out, "-"], capture_output=True, text=True).stdout
        if "Page 4" in page_text:
            rot = subprocess.run(["pdfinfo", "-f", str(n), "-l", str(n), out], capture_output=True, text=True).stdout
            rotations.append(int(re.search(rf"Page\s+{n} rot:\s+(\d+)", rot).group(1)))
    if not rotations or any(r not in (90, 270) for r in rotations):
        raise AssertionError(f"landscape page 4 not turned to fill the sheet: rotations {rotations}")
    return (f"app says '{status}'; CUPS wrote {os.path.basename(out)}: {info.get('Pages')} pages ({info.get('Page size')}), "
            f"pages with text {pages_seen}, landscape page 4 turned {rotations}, fonts {[f.split()[0] for f in fonts]}, "
            "images: none (vector)")


step("30-print-pages-2-4-two-copies", print_pages)


def print_cancel():
    ensure_reader(0)
    focus_main()
    app.key("ctrl+p")
    time.sleep(1)
    app.click("section[aria-label=Print] button.primary")
    w = app.wait(lambda: [x for x in native_windows() if x[1].startswith("Print")], 15, "GTK print dialog")[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(1.5)
    app.key("Escape")
    time.sleep(1)
    return "dialog cancelled; " + str(app.js("return document.body.innerText.includes('Printing cancelled') ? 'no job, card stays' : 'no job'"))


step("31-print-cancel", print_cancel)


def print_not_allowed():
    """A file whose permissions forbid printing (D-66): the Print card is locked with the reason (Foundation's
    shared card), no dialog opens and nothing reaches CUPS. The Linux print service refuses as well."""
    started = time.time()
    app.open(os.path.join(FIX, "no-print.pdf"))
    app.wait(lambda: app.js("var t=[...document.querySelectorAll('.rtab')].find(t=>t.innerText.includes('no-print.pdf')); if(!t) return false; t.click(); return true"), 20, "tab no-print.pdf")
    time.sleep(1.5)
    focus_main()
    app.key("ctrl+p")
    time.sleep(1.2)
    card = "section[aria-label=Print]"
    # The locked card gives the reason as its tooltip (title), on the card and on the Print button.
    reason = app.wait(lambda: app.js(f"var c=document.querySelector({json.dumps(card)}); return c && (c.title || '').includes(\"permissions don't allow printing\") ? c.title : null"), 10, "the reason on the card")
    disabled = app.js(f"var b=document.querySelector({json.dumps(card + ' button.primary')}); return !!b && b.disabled")
    if not disabled:
        raise AssertionError("the Print button is enabled for a no-printing file")
    app.click(card + " button.primary")  # a disabled button: nothing may happen
    time.sleep(3)
    if [x for x in native_windows() if x[1].startswith("Print")]:
        raise AssertionError("the GTK print dialog opened for a no-printing file")
    if cups_pdfs(started):
        raise AssertionError("a job reached CUPS for a no-printing file")
    app.shot("31-print-not-allowed")
    dismiss()
    return f"card locked: '{reason}'; Print disabled; no print dialog; nothing sent to CUPS"


step("31-print-not-allowed", print_not_allowed)


def unlock(path, password):
    app.open(path)
    name = os.path.basename(path)
    app.wait(lambda: app.js(f"var t=[...document.querySelectorAll('.rtab')].find(t=>t.innerText.includes('{name}')); if(!t) return false; t.click(); return true"), 20, "tab " + name)
    app.wait(lambda: app.js("var i=document.querySelector('.uc-pw'); return !!i && !!i.offsetParent"), 15, "the password card")
    type_into(".uc-pw", password)
    app.key("Return")
    app.wait(lambda: app.js("return !document.querySelector('.uc-pw')") and app.js("return document.querySelectorAll('.rpage').length > 0"), 20, "the unlocked pages")
    time.sleep(1.5)


def print_with_owner_password():
    """D-139 (chuvadi-pdf 3.32.0; ends D-102's refusal): the owner password lifts a file's "no printing";
    the user password doesn't. Same file twice (two copies, two tabs), print forbidden, both passwords set."""
    src = os.path.join(FIX, "five-pages.pdf")
    files = {}
    for who in ("user", "owner"):
        files[who] = os.path.join(FIX, f"no-print-{who}-opens.pdf")
        subprocess.run(["qpdf", "--encrypt", "--user-password=chuvadi-user", "--owner-password=chuvadi-owner", "--bits=256",
                        "--print=none", "--", src, files[who]], check=True)
    card = "section[aria-label=Print]"
    # The user password: still refused.
    unlock(files["user"], "chuvadi-user")
    focus_main()
    app.key("ctrl+p")
    time.sleep(1.2)
    locked = app.wait(lambda: app.js(f"var c=document.querySelector({json.dumps(card)}); return c && (c.title || '').includes(\"permissions don't allow printing\") ? c.title : null"), 10, "the reason on the card (user password)")
    dismiss()
    # The owner password: printing works, and the job reaches CUPS.
    started = time.time()
    unlock(files["owner"], "chuvadi-owner")
    focus_main()
    app.key("ctrl+p")
    time.sleep(1.2)
    title = app.js(f"var c=document.querySelector({json.dumps(card)}); return c ? (c.title || '') : null")
    if "permissions" in (title or ""):
        raise AssertionError("the Print card is locked after opening with the owner password: " + title)
    app.click(card + " button.primary")
    w = app.wait(lambda: [x for x in native_windows() if x[1].startswith("Print")], 15, "GTK print dialog")[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(3)
    app.key("Return")
    out = sorted(app.wait(lambda: cups_pdfs(started), 60, "cups-pdf output"), key=os.path.getmtime)[-1]
    time.sleep(1)
    pages = pdfinfo(out).get("Pages")
    app.shot("31b-owner-password-prints")
    return f"user password: locked ('{locked}'); owner password: printed, CUPS wrote {pages} pages"


step("31b-owner-password-lifts-no-print", print_with_owner_password)

# ── keyboard ────────────────────────────────────────────────────────────────


def shortcuts():
    ensure_reader(0)
    focus_main()
    seen = []
    app.key("ctrl+plus")
    seen.append("Ctrl+")
    app.key("ctrl+minus")
    seen.append("Ctrl−")
    app.key("ctrl+0")
    seen.append("Ctrl0")
    app.key("ctrl+f")
    time.sleep(0.6)
    seen.append("CtrlF:" + str(app.js("return !!document.activeElement && document.activeElement.tagName")))
    app.key("Escape")
    app.key("ctrl+Tab")
    seen.append("CtrlTab")
    app.key("ctrl+o")
    time.sleep(1.5)
    dlg = [n for _, n in native_windows()]
    seen.append("CtrlO:" + (",".join(dlg) or "no dialog"))
    return "; ".join(seen)


step("32-shortcuts", shortcuts)


def immersive():
    focus_main()
    app.key("F11")
    time.sleep(1.5)
    app.shot("33-immersive")
    app.key("F11")
    time.sleep(1)
    return "F11 in and out"


step("33-immersive", immersive, shot=False)


def close_tabs():
    focus_main()
    n = app.js("return document.querySelectorAll('.rtab').length")
    app.key("ctrl+shift+w")
    time.sleep(1.5)
    return f"{n} tabs → {app.js('return document.querySelectorAll(\".rtab\").length')}"


step("34-close-all-tabs", close_tabs)


def tab_names():
    return app.js("return [...document.querySelectorAll('.rtab')].map(t=>t.innerText.trim().split('\\n')[0])")


def open_several_from_command_line():
    """B-04: chuvadi-reader a b c (the desktop entry's %F for a multi-file Open with) — each in its own tab."""
    files = ["five-pages.pdf", "sample.docx", "sample.xlsx"]
    app.restart(log_name="app-several.log", args=[os.path.join(FIX, f) for f in files])
    app.wait(lambda: len(tab_names()) == 3, 30, "three tabs")
    names = tab_names()
    if [n for n in names] != files:
        raise AssertionError(f"tabs {names}, expected {files} in order")
    app.shot("34b-three-files-three-tabs")
    return "tabs: " + ", ".join(names)


step("34b-open-several-from-command-line", open_several_from_command_line)


def render_choice():
    """B-12: without a GPU, WebKit's GL compositing is off (else Mesa compiles its shaders on the CPU on a
    person's first launch: seconds of blank window). With a GPU, WebKit's default stays."""
    info = app.send("render-info")
    gpu = bool(glob.glob("/dev/dri/renderD*"))
    if info["noGpu"] == gpu:
        raise AssertionError(f"host's GPU check {info} disagrees with /dev/dri ({'GPU' if gpu else 'no GPU'})")
    if info["noGpu"] and not info["compositingOff"]:
        raise AssertionError("no GPU, but WebKit compositing is on")
    if not info["noGpu"] and info["compositingOff"] and "WEBKIT_DISABLE_COMPOSITING_MODE" not in os.environ:
        raise AssertionError("GPU present, but compositing was turned off")
    return f"{'no GPU' if info['noGpu'] else 'GPU'}: WebKit compositing {'off' if info['compositingOff'] else 'on (default)'}"


step("34b2-render-choice-without-gpu", render_choice)


def tab_order():
    """B-23: Tab doesn't walk through a "Send page N to a desk" button per page before anything else."""
    ensure_reader(0)
    stops = app.js("return [...document.querySelectorAll('button, [href], input, select, textarea, [tabindex]')]"
                   ".filter(e => e.tabIndex >= 0 && !e.disabled && e.offsetParent !== null)"
                   ".slice(0, 12).map(e => e.className || e.tagName)")
    sends = [c for c in stops if "rpage-send" in str(c)]
    if sends:
        raise AssertionError(f"per-page buttons in the first Tab stops: {stops}")
    return "first Tab stops: " + ", ".join(str(c).split()[0] for c in stops[:6])


step("34b3-tab-order-skips-per-page-buttons", tab_order)


def focus_ring():
    """B-22: keyboard focus draws the theme's accent ring (--chvd-binding) in every theme; a mouse click draws none."""
    ensure_reader(0)
    ring = ("var e=document.activeElement, c=getComputedStyle(e), r=getComputedStyle(document.documentElement);"
            "return [e.className || e.tagName, c.outlineStyle, c.outlineWidth, c.outlineColor,"
            " (function(){var d=document.createElement('i'); d.style.color=r.getPropertyValue('--chvd-binding');"
            " document.body.appendChild(d); var v=getComputedStyle(d).color; d.remove(); return v;})()]")
    seen = []
    try:
        for theme in ("light", "dark", "palm", "indigo", "contrast"):
            app.js(f"document.documentElement.setAttribute('data-theme','{theme}'); document.activeElement.blur(); return 1")
            app.key("Tab")
            time.sleep(0.3)
            el, style, width, colour, accent = app.js(ring)
            if style != "solid" or width != "2px" or colour != accent:
                raise AssertionError(f"{theme}: Tab focus on {el} drew {style} {width} {colour}, accent is {accent}")
            seen.append(f"{theme} {colour}")
        app.click_real(".tb-pg-btn", 1)  # next page with a real pointer click
        time.sleep(0.4)
        clicked = app.js("var e=document.activeElement; return [e.className || e.tagName, getComputedStyle(e).outlineStyle]")
        app.click(".tb-pg-btn", 0)  # back to page 1
        if clicked[1] != "none":
            raise AssertionError(f"a mouse click drew a focus ring: {clicked}")
    finally:
        app.js("document.documentElement.setAttribute('data-theme','light'); return 1")
    return "accent ring on Tab: " + "; ".join(seen) + f"; none on a mouse click (focus on {str(clicked[0]).split()[0]})"


step("34b4-focus-ring-theme-accent", focus_ring)


def drop_several():
    """B-06: several files dropped on the window — each in its own tab (the window's drop handler, as GTK
    calls it; a real drag from a file manager is checked by hand)."""
    before = tab_names()
    # Two files not open yet (a file that is already open goes to its tab, as with a single file).
    with open(os.path.join(FIX, "five-pages.pdf"), "rb") as src, open(os.path.join(FIX, "second-copy.pdf"), "wb") as dst:
        dst.write(src.read())
    dropped = ["no-print.pdf", "second-copy.pdf"]
    app.send("drop " + "\t".join(os.path.join(FIX, f) for f in dropped))
    app.wait(lambda: len(tab_names()) == len(before) + 2, 30, "two more tabs")
    names = tab_names()
    if names[-2:] != dropped:
        raise AssertionError(f"after the drop: {names}")
    return f"{len(before)} tabs → {len(names)}: {', '.join(names[-2:])} added in order"


step("34c-drop-several-files", drop_several)


def second_launch():
    """B-05 (D-83): a second launch hands its files to the running copy — a new tab there, the window comes
    forward — and ends without a window of its own."""
    before = tab_names()
    handed = os.path.join(FIX, "handed-over.pdf")
    with open(os.path.join(FIX, "five-pages.pdf"), "rb") as src, open(handed, "wb") as dst:
        dst.write(src.read())
    started = time.time()
    second = subprocess.run([os.path.join(app.app_dir, "chuvadi-reader"), handed], env=app.env,
                            capture_output=True, text=True, timeout=30)
    took = time.time() - started
    if second.returncode != 0:
        raise AssertionError(f"second launch exited {second.returncode}: {second.stderr[-300:]}")
    windows = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^Chuvadi$"], env=app.env,
                             capture_output=True, text=True).stdout.split()
    if len(windows) != 1:
        raise AssertionError(f"{len(windows)} Chuvadi windows after the second launch")
    app.wait(lambda: "handed-over.pdf" in tab_names(), 20, "the handed-over file's tab")
    app.shot("34c2-second-launch")
    return (f"second launch handed over and exited 0 in {took:.2f} s; one window; tabs {len(before)} → "
            f"{len(tab_names())} (handed-over.pdf added)")


step("34c2-second-launch-opens-in-running-window", second_launch)


def error_message_is_a_sentence():
    """B-17: .NET's own error messages reach the user, not resource keys. A PDF without read permission
    (chmod 000) shows the plain sentence, and Details says "Access to the path … is denied". Root can read any file, so as root this step only
    reports; check-deb.py checks the cause (the runtime setting) in every run."""
    if os.geteuid() == 0:
        return "skipped as root (root reads chmod-000 files); the runtime setting is checked by check-deb.py"
    locked = os.path.join(FIX, "locked.pdf")
    with open(os.path.join(FIX, "five-pages.pdf"), "rb") as src, open(locked, "wb") as dst:
        dst.write(src.read())
    os.chmod(locked, 0)
    try:
        app.send("open " + locked)
        # WT-10 (Foundation's eighth patch): a plain sentence, with the system's own text under Details.
        msg = app.wait(lambda: app.js("var t=document.body.innerText; var i=t.indexOf(\"couldn't read this file\"); "
                                      "return i < 0 ? null : t.slice(i, i + 160)"), 20, "error shown")
        detail = app.js("var d=[...document.querySelectorAll('details.rempty-sub')].pop(); return d ? d.textContent : null")
    finally:
        os.chmod(locked, 0o644)
    if not detail:
        raise AssertionError("no Details under: " + msg)
    if "UnauthorizedAccess_" in detail or "IODenied" in detail:
        raise AssertionError("resource key under Details: " + detail)
    if "denied" not in detail:
        raise AssertionError("Details doesn't carry the system's message: " + detail)
    app.shot("34d-error-message")
    return " ".join(msg.split())[:90] + " | Details: " + " ".join(detail.split())[:110]


step("34d-error-message-not-a-resource-key", error_message_is_a_sentence)


def unblock(fifo):
    """Ends a stalled read: open the pipe for writing without blocking, then close it (the reader sees the end)."""
    try:
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    try:
        os.remove(fifo)
    except OSError:
        pass


def stalled_source_never_blocks():
    """B-24: a source that never delivers data (a hung network mount, an unplugged drive; here a named pipe)
    shows "Opening…" and a way to stop at once, and never holds up the next open — for a PDF and for Excel."""
    stall = os.path.join(FIX, "stall")
    os.makedirs(stall, exist_ok=True)
    out = []
    for name in ("slow.pdf", "slow.xlsx"):
        fifo = os.path.join(stall, name)
        if os.path.exists(fifo):
            os.remove(fifo)
        os.mkfifo(fifo)
        try:
            t0 = time.time()
            app.send("open " + fifo, timeout=5)  # before the fix the page's thread waited on the pipe here
            opening = app.wait(lambda: "Opening" in (app.js("return document.body.innerText") or "") and round(time.time() - t0, 1),
                               5, f"'Opening…' for {name}")
            stop = app.wait(lambda: app.js("return [...document.querySelectorAll('button')].some(b => b.offsetParent && "
                                           "/^(Stop opening|Cancel)/.test(b.innerText.trim()))") and round(time.time() - t0, 1),
                            15, f"a Stop button for {name}")
            app.send("open " + os.path.join(FIX, "five-pages.pdf"), timeout=5)
            app.wait(lambda: app.js("return [...document.querySelectorAll('.rtab')].some(t => t.innerText.includes('five-pages'))"),
                     10, "the next file's tab while the first still waits")
            out.append(f"{name}: Opening… {opening} s, Stop {stop} s, next file opened")
        finally:
            unblock(fifo)
        time.sleep(1)
        focus_main()
        app.key("ctrl+shift+w")
        time.sleep(1.5)
    return "; ".join(out)


step("34e-stalled-source-never-blocks", stalled_source_never_blocks)


def viewer_errors_follow_wt10():
    """B-25: a Word or Excel file that can't be read says so in a plain sentence; the library's own text
    (here a zip error) is under a collapsed Details, as for PDFs (WT-10)."""
    out = []
    for name, what in (("notzip.xlsx", "an Excel workbook"), ("notzip.docx", "a Word document")):
        path = os.path.join(FIX, name)
        with open(path, "wb") as f:
            f.write(b"These bytes are not a zip package." * 20)
        app.send("open " + path)
        app.wait(lambda: app.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{name}')"),
                 10, f"{name}'s tab in front")
        kind = "Word" if "Word" in what else "Excel"
        # This file's message: visible, and naming its own kind (both viewers can stay in the page).
        shown = f"[...document.querySelectorAll('.vm-err')].filter(e => e.offsetParent && e.innerText.includes('{kind}')).pop()"
        sentence = app.wait(lambda: app.js(f"var e={shown}; var b=e && e.querySelector('.vm-body > span'); return b ? b.innerText : null"),
                            15, f"the error for {name}")
        detail = app.js(f"var e={shown}; var d=e && e.querySelector('details.vm-detail'); return d ? [d.open, d.textContent] : null")
        if not detail:
            raise AssertionError(f"{name}: no Details under '{sentence}'")
        if detail[0]:
            raise AssertionError(f"{name}: Details is open; WT-10 keeps it collapsed")
        if ":" in sentence or "Central Directory" in sentence or "zip" in sentence.lower():
            raise AssertionError(f"{name}: technical text in the sentence: '{sentence}'")
        app.shot("34f-" + name.replace(".", "-"))
        out.append(f"{name}: '{sentence}' | Details: {' '.join(detail[1].split())[7:80]}")
    focus_main()
    app.key("ctrl+shift+w")
    time.sleep(1.5)
    return "; ".join(out)


step("34f-viewer-errors-follow-wt10", viewer_errors_follow_wt10)


# ── rendering off the page's thread (D-152, AT-13) ─────────────────────────
HEAVY = os.path.join(FIX, "heavy")
subprocess.run([sys.executable, "-I", os.path.join(HERE, "make-heavy-pdfs.py"), HEAVY], check=True, stdout=subprocess.DEVNULL)


def ping():
    """Seconds for the page to answer a trivial script: the page's thread is free."""
    t0 = time.time()
    app.js("return 1")
    return time.time() - t0


def rendered(page_index):
    """The page's own drawing is there: a page-sized svg (viewBox wider than 100), not the 24 x 24 loading icon
    that the page holds while it draws (B-28)."""
    return app.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{page_index}\"]'); "
                  "return !!w && [...w.querySelectorAll('svg')].some(s => s.viewBox && s.viewBox.baseVal && s.viewBox.baseVal.width > 100)")


def current_page():
    return int(app.js("var b=document.querySelector('.tb-pg-box'); return b ? b.value : 0") or 0)


def memory_mb():
    """Resident memory of the app and of its WebKit processes, in MB."""
    procs = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            stat = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
            procs[int(pid)] = int(stat[1])
        except OSError:
            pass
    tree, todo = set(), [app.proc.pid]
    while todo:
        p = todo.pop()
        tree.add(p)
        todo += [c for c, parent in procs.items() if parent == p and c not in tree]
    def rss(pid):
        try:
            return int(next(l for l in open(f"/proc/{pid}/status") if l.startswith("VmRSS")).split()[1]) // 1024
        except (OSError, StopIteration):
            return 0
    return rss(app.proc.pid), sum(rss(p) for p in tree if p != app.proc.pid)


def open_tab(path):
    name = os.path.basename(path)
    app.send("open " + path, timeout=10)
    app.wait(lambda: app.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{name}')"), 20, name + "'s tab in front")


def close_active_tab():
    app.js("var x=document.querySelector('.rtab.active .rtab-x'); if (x) x.click(); return 1")
    time.sleep(1)


def paging_fast():
    """Page through a 400-page PDF as fast as keys repeat (PageDown): the page stays responsive, and the page
    the person lands on is drawn."""
    open_tab(os.path.join(HEAVY, "big.pdf"))
    app.wait(lambda: rendered(0), 20, "page 1 drawn")
    focus_main()
    pings = []
    for burst in range(6):  # real key presses: PageDown, 25 at a time, 10 ms apart
        subprocess.run(["xdotool", "key", "--repeat", "25", "--delay", "10", "Next"], env=app.env, capture_output=True)
        pings.append(ping())
    worst = max(pings)
    if worst > 1.0:
        raise AssertionError(f"the page took {worst:.2f} s to answer while paging (each burst 25 pages)")
    # WebKitGTK plays each PageDown as a smooth-scroll step, one after another, so the view keeps moving for
    # seconds after the last key. Time the drawing from when the view settles, not from the last key.
    t_keys = time.time()
    last, since = current_page(), time.time()
    while time.time() - since < 1.0:
        time.sleep(0.1)
        now = current_page()
        if now != last:
            last, since = now, time.time()
        if time.time() - t_keys > 60:
            raise AssertionError("the view never settled after paging")
    settled_after = since - t_keys
    landed = current_page()
    t0 = since
    app.wait(lambda: rendered(landed - 1), 20, f"page {landed} drawn")
    drawn_in = max(0.0, time.time() - t0)
    if drawn_in > 2.0:
        raise AssertionError(f"page {landed} drew {drawn_in:.1f} s after the view settled on it")
    app.js("document.querySelector('.tb-pg-box').value='400'; document.querySelector('.tb-pg-box').dispatchEvent(new Event('change')); return 1")
    app.wait(lambda: current_page() == 400 and rendered(399), 20, "page 400 drawn")
    close_active_tab()
    return (f"6 bursts of 25 PageDowns: page answered within {worst:.2f} s each; the view settled on page {landed} "
            f"{settled_after:.1f} s after the last key (smooth scrolling), drawn "
            f"{'within the 1 s it took to count as settled' if drawn_in <= 1.05 else f'{drawn_in:.1f} s after it settled'}; "
            "jumped to page 400, drawn")


step("36a-paging-fast-big-pdf", paging_fast)


def close_mid_render():
    """Close a CAD drawing's tab the moment it opens, while sheet 1 is usually still drawing: nothing hangs or
    errors, and the next file opens and draws at once. (Core's RenderOffUiThreadTests hold a render open with a
    hook for a deterministic mid-render close; a generated page can't be made reliably slow.)"""
    before = memory_mb()
    open_tab(os.path.join(HEAVY, "cad.pdf"))
    mid = not rendered(0)  # usually: sheet 1 takes ~0.3 s (deterministic mid-render closes: RenderOffUiThreadTests)
    close_active_tab()
    t0 = time.time()
    open_tab(os.path.join(FIX, "five-pages.pdf"))
    app.wait(lambda: rendered(0), 15, "the next file's page 1 drawn")
    next_in = time.time() - t0
    worst = max(ping() for _ in range(5))
    time.sleep(8)  # the cancelled render finishes its sheet, then the document closes
    after = memory_mb()
    close_active_tab()
    if next_in > 2.0:
        raise AssertionError(f"the next file took {next_in:.1f} s to draw: it waited for the abandoned render")
    if worst > 1.0:
        raise AssertionError(f"the page took {worst:.2f} s to answer after closing mid-render")
    return (f"closed {'mid-render' if mid else 'just after sheet 1 was drawn'}; next file drawn in {next_in:.1f} s; "
            f"page answers in ≤ {worst:.2f} s; memory app/web {before[0]}/{before[1]} MB → {after[0]}/{after[1]} MB")


step("36b-close-tab-mid-render", close_mid_render)


def cad_drawing():
    """A 5-sheet A1 vector drawing (10,000 strokes a sheet; B-27's kind of file): the page answers while sheets
    draw, every sheet really draws (its page-sized drawing, not the loading icon: B-28), and once all five are
    drawn, closing it gives the memory back: within 100 MB of before it opened, within 90 s."""
    sheet_limit = 30  # measured on 2 vCPU, no GPU: 5.5-7 s a sheet (B-27, a library item); about four times that
    baseline = memory_mb()
    t0 = time.time()
    open_tab(os.path.join(HEAVY, "cad.pdf"))
    worst = max(ping() for _ in range(3))
    app.wait(lambda: rendered(0), sheet_limit, "sheet 1 drawn")
    first = time.time() - t0
    # The view fits the drawing once sheet 1 lands, and every page's height changes (A1 landscape: ~2,600 px to
    # ~1,000 px); a scroll made before that lands on another sheet (BUILD-LOG §50). Wait until the heights hold.
    heights = lambda: app.js("return [...document.querySelectorAll('.rpage-wrap')].map(w => Math.round(w.getBoundingClientRect().height)).join(',')")
    last, since = heights(), time.time()
    while time.time() - since < 1.5 and time.time() - t0 < sheet_limit + 15:
        time.sleep(0.25)
        now = heights()
        if now != last:
            last, since = now, time.time()
    times = []
    for n in range(2, 6):
        t1 = time.time()
        # Scrolled into view as a person would. (Jumping by the page box can land on another sheet while the
        # page heights settle — a separate finding, BUILD-LOG §50.)
        app.js(f"document.querySelector('.rpage-wrap[data-page=\"{n - 1}\"]').scrollIntoView({{block: 'start'}}); return 1")
        worst = max(worst, ping())
        app.wait(lambda: rendered(n - 1), sheet_limit, f"sheet {n} drawn")
        worst = max(worst, ping())
        times.append(time.time() - t1)
    app.shot("36c-cad-drawing")
    mem = memory_mb()  # every sheet drawn: nothing still drawing
    close_active_tab()
    if worst > 1.0:
        raise AssertionError(f"the page took {worst:.2f} s to answer while a sheet was drawing")
    # Closing gives the memory back (sixteenth patch). Collections are at least 30 s apart (MemoryRelief.MinGap) and
    # 36b closed a drawing just before, so the relief can come up to ~30 s later (D-156): wait up to 40 s.
    t_close = time.time()
    after = memory_mb()
    trail = []
    while after[0] > baseline[0] + 100 and time.time() - t_close < 90:
        time.sleep(1)
        after = memory_mb()
        if int(time.time() - t_close) % 10 == 0:
            trail.append(f"{int(time.time() - t_close)}s:{after[0]}")
    # Twentieth and twenty-first patches: each relief pass waits for the finalizer thread, and drawn sheets are
    # served by address instead of as ~77 MB strings; the Linux host trims glibc after each pass.
    relief = (app.send("gc-count") or {}).get("reliefPasses", "?")
    if after[0] > baseline[0] + 100:
        raise AssertionError(f"the app kept its memory after closing the drawing: {baseline[0]} MB before opening, "
                             f"{mem[0]} MB with 5 sheets drawn, {after[0]} MB {time.time() - t_close:.0f} s after closing "
                             f"({' '.join(trail)}; relief passes: {relief})")
    kept = f"; relief passes: {relief}"
    return (f"sheet 1 drawn in {first:.1f} s; sheets 2-5 in {', '.join(f'{t:.1f}' for t in times)} s; page answered in "
            f"≤ {worst:.2f} s throughout; memory app/web: {baseline[0]}/{baseline[1]} MB before, {mem[0]}/{mem[1]} MB with "
            f"5 sheets drawn, {after[0]}/{after[1]} MB {time.time() - t_close:.0f} s after closing ({' '.join(trail)}){kept}")


step("36c-cad-drawing", cad_drawing)


def page_images_by_address():
    """D-158: a drawn (raster) sheet is shown from _chvd/pages/<token>.png, served in process by the Linux host:
    the image is there and decodes, it's a PNG and never cached, and an unknown token is simply not found."""
    open_tab(os.path.join(HEAVY, "cad.pdf"))
    # Reopened where it was left (36c ends on sheet 5): check the sheet in view.
    time.sleep(1)
    shown = app.wait(lambda: current_page() or None, 10, "the page box")
    app.wait(lambda: rendered(shown - 1), 30, f"sheet {shown} drawn")
    wrap = f"document.querySelector('.rpage-wrap[data-page=\"{shown - 1}\"]')"
    href = app.js(f"var im={wrap}.querySelector('image'); return im ? (im.getAttribute('href') || '') : ''")
    if not re.fullmatch(r"_chvd/pages/[0-9a-f]{32}\.png", href or ""):
        close_active_tab()
        raise AssertionError(f"sheet {shown} isn't drawn by address: image href {href!r}")
    size = app.js(f"return {wrap}.innerHTML.length")
    # WebKitGTK's fetch shows no content type for any app:// asset (scripts and styles too), so check the bytes are a
    # PNG and that an image element decodes the address, as the page itself does.
    probe = ("return fetch(ADDR).then(async r => { var b = new Uint8Array(await r.arrayBuffer()); "
             "var w = !r.ok ? 0 : await new Promise(res => { var i = new Image(); i.onload = () => res(i.naturalWidth); "
             "i.onerror = () => res(0); i.src = ADDR; }); "
             "return [r.status, b.length >= 8 && b[0] === 137 && b[1] === 80 && b[2] === 78 && b[3] === 71 ? 'PNG' : 'not a PNG', "
             "r.headers.get('cache-control'), w]; })")
    got = app.js(probe.replace("ADDR", json.dumps(href)))
    missing = app.js(probe.replace("ADDR", json.dumps("_chvd/pages/" + "0" * 32 + ".png")))
    close_active_tab()
    status, ctype, cache, width = got
    if status != 200 or ctype != "PNG" or "no-store" not in (cache or "") or width < 100:
        raise AssertionError(f"the page image came back as {got}")
    if missing[0] != 404:
        raise AssertionError(f"an unknown token gave {missing[0]}, not 404")
    return (f"sheet {shown} shown from {href[:24]}…; page markup {size} characters; served {status} {ctype}, '{cache}', "
            f"decodes to {width} px wide; unknown token 404")


step("36d-page-images-by-address", page_images_by_address)


def zoom_now():
    return float(app.js("var d=document.querySelector('.rdesk'); return d ? parseFloat(getComputedStyle(d).getPropertyValue('--rpage-zoom')) || 1 : 0"))


def pinch(x, y, scales):
    """One pinch at a place in the view, sent as GTK's zoom gesture sends it: begin, the scale so far at each
    change, end (a real pinch can't be made under Xvfb)."""
    app.send(f"pinch 0 1 {x} {y}")
    for s in scales:
        app.send(f"pinch 1 {s:.5f} {x} {y}")
        time.sleep(0.05)
    app.send(f"pinch 2 1 {x} {y}")


def page_point():
    """A point over the page in view (client coordinates) and where on that page it is (fractions of its box)."""
    return app.js("var w=[...document.querySelectorAll('.rpage-wrap')].find(e => { var r=e.getBoundingClientRect(); return r.bottom > 200 && r.top < innerHeight - 200; }); "
                  "var p=w.querySelector('.rpage') || w, r=p.getBoundingClientRect(); "
                  "var x=Math.round(r.left + r.width * 0.3), y=Math.round(Math.max(r.top, 160) + 120); "
                  "return [x, y, (x - r.left) / r.width, (y - r.top) / r.height, w.getAttribute('data-page')]")


def where_on_page(x, y, page):
    return app.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{page}\"]'); var p=w.querySelector('.rpage') || w, r=p.getBoundingClientRect(); "
                  f"return [({x} - r.left) / r.width, ({y} - r.top) / r.height]")


def pinch_and_ctrl_scroll():
    """Arun's laptop check (11 Nov): a trackpad pinch did nothing. The host takes the pinch (so WebKit doesn't zoom
    the whole app) and hands it to the Reader's shared entry, window.chuvadiPinch (patch 27). A pinch can't
    be made under Xvfb, so the steps are sent through the host's own forwarding (the gesture's signal calls the
    same function); Ctrl+scroll is real input. On Home, which has no zoom, neither changes anything."""
    open_tab(PDF)
    app.wait(lambda: rendered(0), 20, "page 1 drawn")
    time.sleep(0.5)
    scale = "return [window.visualViewport ? visualViewport.scale : 1, innerWidth]"
    whole = app.js(scale)
    z0 = zoom_now()
    x, y, fx, fy, page = page_point()
    pinch(x, y, [1.1 ** i for i in range(1, 6)])  # spread: five steps of 10 %
    app.wait(lambda: abs(zoom_now() - z0 * 1.1 ** 5) < 0.03 * z0, 5, f"zoom {z0 * 1.1 ** 5:.2f} after a spread from {z0:.2f} (now {zoom_now():.2f})")
    z1 = zoom_now()
    app.shot("37-pinch-spread")
    # About the fingers: checked once the page is wider than the view (a narrower page stays centred, as with
    # Ctrl+scroll), so the point can hold still both ways.
    wider = ("var d=document.querySelector('.rdesk'), w=document.querySelector('.rpage-wrap[data-page=\"%s\"]'); "
             "var p=w.querySelector('.rpage') || w; return p.getBoundingClientRect().width > d.clientWidth + 40") % page
    for _ in range(14):
        if app.js(wider):
            break
        pinch(x, y, [1.1])
        time.sleep(0.15)
    time.sleep(0.5)
    x, y, fx, fy, page = page_point()
    za = zoom_now()
    pinch(x, y, [1.1, 1.21, 1.331])
    app.wait(lambda: abs(zoom_now() - za * 1.1 ** 3) < 0.03 * za, 5, f"zoom {za * 1.1 ** 3:.2f} after a second spread (now {zoom_now():.2f})")
    time.sleep(0.4)
    ax, ay = where_on_page(x, y, page)
    if abs(ax - fx) > 0.02 or abs(ay - fy) > 0.02:
        raise AssertionError(f"the spread didn't zoom about the fingers: the point was at ({fx:.2f}, {fy:.2f}) of the page, now ({ax:.2f}, {ay:.2f})")
    zb = zoom_now()
    for _ in range(40):  # pinch back in, 10 % a step
        if zoom_now() <= z0 * 1.05:
            break
        pinch(x, y, [max(1 / 1.1, z0 / zoom_now())])
        time.sleep(0.1)
    app.wait(lambda: abs(zoom_now() - z0) < 0.03 * z0, 5, f"zoom back to {z0:.2f} after pinching in (now {zoom_now():.2f})")
    time.sleep(0.5)
    x, y, fx, fy, page = page_point()

    # Ctrl + scroll wheel, real input, pointer over the page.
    focus_main()
    gx, gy = (int(v) for v in window_geometry()[0].split(","))
    app.xdo("mousemove", str(gx + x), str(gy + y))
    app.xdo("keydown", "ctrl")
    try:
        app.xdo("click", "--repeat", "3", "--delay", "60", "4")
        app.wait(lambda: zoom_now() > z0 * 1.05, 5, f"zoom above {z0:.2f} after Ctrl+scroll up (now {zoom_now():.2f})")
        z2 = zoom_now()
        app.xdo("click", "--repeat", "6", "--delay", "60", "5")
        app.wait(lambda: zoom_now() < z2 * 0.95, 5, f"zoom below {z2:.2f} after Ctrl+scroll down (now {zoom_now():.2f})")
        z3 = zoom_now()
    finally:
        app.xdo("keyup", "ctrl")
    if app.js(scale) != whole:
        raise AssertionError(f"the whole app was zoomed: {whole} -> {app.js(scale)}")
    close_active_tab()

    go_home()
    time.sleep(0.5)
    before = app.js(scale + ".concat([document.body.scrollWidth, document.body.scrollHeight])")
    pinch(900, 500, [1.2, 1.44, 1.73, 2.07])
    app.xdo("mousemove", str(gx + 900), str(gy + 500))
    app.xdo("keydown", "ctrl")
    try:
        app.xdo("click", "--repeat", "3", "--delay", "60", "4")
    finally:
        app.xdo("keyup", "ctrl")
    time.sleep(0.6)
    after = app.js(scale + ".concat([document.body.scrollWidth, document.body.scrollHeight])")
    if after != before:
        raise AssertionError(f"Home changed size on a pinch or Ctrl+scroll: {before} -> {after}")
    return (f"spread x1.1 five times: zoom {z0:.2f} -> {z1:.2f}; at {za:.2f} -> {zb:.2f} the point under the fingers stayed put; "
            f"pinched back to {z0:.2f}; "
            f"Ctrl+scroll up -> {z2:.2f}, down -> {z3:.2f}; the app itself never scaled; Home unchanged by both")


step("37-pinch-and-ctrl-scroll", pinch_and_ctrl_scroll)


def pinch_other_viewers():
    """Patch 27: a pinch also changes the text size of the Word and Excel viewers (their zoom), through the
    same shared entry; real Ctrl+scroll does too. The app itself never scales."""
    zoom = "var e=[...document.querySelectorAll('[data-zoom]')].find(e => e.offsetParent); return e ? parseFloat(e.getAttribute('data-zoom')) : 0"
    box = "var e=[...document.querySelectorAll('[data-zoom]')].find(e => e.offsetParent), r=e.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)]"
    scale = "return [window.visualViewport ? visualViewport.scale : 1, innerWidth]"
    whole = app.js(scale)
    gx, gy = (int(v) for v in window_geometry()[0].split(","))
    said = []
    for name in ("sample.docx", "sample.xlsx"):
        open_tab(os.path.join(FIX, name))
        app.wait(lambda: app.js(zoom) > 0, 20, name + " shown")
        time.sleep(1.0)
        z0 = app.js(zoom)
        x, y = app.js(box)
        pinch(x, y, [1.15, 1.3, 1.4])
        app.wait(lambda: abs(app.js(zoom) - z0 * 1.4) <= 2, 5, f"{name}: {z0 * 1.4:.0f} % after a spread (now {app.js(zoom)})")
        z1 = app.js(zoom)
        pinch(x, y, [0.85, z0 / z1])
        app.wait(lambda: abs(app.js(zoom) - z0) <= 2, 5, f"{name}: back to {z0:.0f} % (now {app.js(zoom)})")
        focus_main()
        app.xdo("mousemove", str(gx + x), str(gy + y))
        app.xdo("keydown", "ctrl")
        try:
            app.xdo("click", "--repeat", "2", "--delay", "70", "4")
        finally:
            app.xdo("keyup", "ctrl")
        app.wait(lambda: app.js(zoom) > z0 + 5, 5, f"{name}: above {z0:.0f} % after Ctrl+scroll up (now {app.js(zoom)})")
        z2 = app.js(zoom)
        if app.js(scale) != whole:
            raise AssertionError(f"{name}: the whole app was zoomed: {whole} -> {app.js(scale)}")
        said.append(f"{name}: pinch {z0:.0f} -> {z1:.0f} -> {z0:.0f} %, Ctrl+scroll -> {z2:.0f} %")
        close_active_tab()
    return "; ".join(said) + "; the app itself never scaled"


step("37b-pinch-word-and-excel", pinch_other_viewers)


def mark_lands_under_pointer():
    """Mac Test's M-27 (a mark drawn with the mouse landed away from the pointer, by an amount that followed the
    zoom, in the build that added Mac's pinch): checked here at 54, 100 and 150 % reached by pinch steps, then by
    the rail and by Ctrl+scroll after those pinches. A rectangle dragged with the real mouse must sit on the
    drag's own corners."""
    ensure_reader(1)
    gx, gy = (int(v) for v in window_geometry()[0].split(","))
    view = ("var d=document.querySelector('.rdesk').getBoundingClientRect(); var best=null; "
            "document.querySelectorAll('.mk-layer').forEach(l => { var r=l.getBoundingClientRect(); "
            "var x0=Math.max(r.left,d.left), y0=Math.max(r.top,d.top,90), x1=Math.min(r.right,d.right), y1=Math.min(r.bottom,d.bottom,innerHeight-90); "
            "var a=Math.max(0,x1-x0)*Math.max(0,y1-y0); if (!best || a>best[4]) best=[x0,y0,x1,y1,a]; }); return best")
    shapes = "return [...document.querySelectorAll('.mk-shape.rect')].map(e => { var r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]; })"
    done = []

    def pinch_to(target):
        x0, y0, x1, y1, _ = app.js(view)
        for _ in range(60):
            z = zoom_now()
            if abs(z - target) < 0.004:
                break
            pinch(round((x0 + x1) / 2), round((y0 + y1) / 2), [max(1 / 1.12, min(1.12, target / z))])
            time.sleep(0.12)
        time.sleep(0.8)

    def draw(how):
        click_label(".srail", "Rectangle")
        focus_main()
        x0, y0, x1, y1, _ = app.js(view)
        w, h = x1 - x0, y1 - y0
        before = app.js(shapes)
        for k in range(40):  # a place clear of the shapes already there: pressing on one moves it
            ax, ay = round(x0 + w * (0.06 + 0.115 * (k % 7))), round(y0 + h * (0.06 + 0.15 * (k // 7)))
            bx, by = ax + round(min(w * 0.10, 110)), ay + round(min(h * 0.09, 70))
            if not any(ax - 12 < o[2] and bx + 12 > o[0] and ay - 12 < o[3] and by + 12 > o[1] for o in before):
                break
        else:
            raise AssertionError("no clear place left on the page")
        app.xdo("mousemove", str(gx + ax), str(gy + ay))
        time.sleep(0.15)
        app.xdo("mousedown", "1")
        for i in range(1, 11):
            app.xdo("mousemove", str(gx + ax + (bx - ax) * i // 10), str(gy + ay + (by - ay) * i // 10))
            time.sleep(0.04)
        time.sleep(0.15)
        app.xdo("mouseup", "1")
        time.sleep(1.0)
        new = [s for s in app.js(shapes) if not any(all(abs(a - b) < 0.5 for a, b in zip(s, o)) for o in before)]
        if len(new) != 1:
            raise AssertionError(f"{how}: {len(new)} new rectangles for one drag")
        off = [new[0][0] - ax, new[0][1] - ay, new[0][2] - bx, new[0][3] - by]
        if any(abs(v) > 2.5 for v in off):
            raise AssertionError(f"{how} at {zoom_now() * 100:.0f} %: the rectangle is off the pointer by (left, top, right, bottom) "
                                 f"{', '.join(f'{v:+.1f}' for v in off)} px; dragged ({ax},{ay}) to ({bx},{by})")
        done.append(f"{zoom_now() * 100:.0f} % ({how})")
        app.key("Escape")
        time.sleep(0.3)

    try:
        for z in (0.54, 1.0, 1.5):
            pinch_to(z)
            draw("pinch")
        click_label(".srail", "Zoom in")
        time.sleep(0.6)
        draw("rail, after pinches")
        x0, y0, x1, y1, _ = app.js(view)
        app.xdo("mousemove", str(int(gx + (x0 + x1) / 2)), str(int(gy + (y0 + y1) / 2)))
        app.xdo("keydown", "ctrl")
        try:
            app.xdo("click", "--repeat", "5", "--delay", "70", "5")
        finally:
            app.xdo("keyup", "ctrl")
        time.sleep(1.0)
        draw("Ctrl+scroll, after pinches")
        app.shot("38-marks-under-pointer")
    finally:
        try:
            app.key("Escape")
            click_label(".srail", "Fit page")  # the zoom the later steps start from (they launch afresh)
        except Exception:
            pass
    return "a rectangle dragged with the mouse sits on the drag's corners (within the outline's width) at " + ", ".join(done)


step("38-mark-lands-under-pointer", mark_lands_under_pointer)

# The desktop's window-button layout, followed exactly (any subset, any order, either end) — the
# setting GNOME (button-layout) and KDE hand to GTK, written to GTK's settings file for a fresh launch.
LAYOUTS = [
    ("appmenu:close", [], ["close"]),                                   # vanilla GNOME
    (":minimize,maximize,close", [], ["min", "max", "close"]),          # Ubuntu
    ("close,minimize,maximize:", ["close", "min", "max"], []),          # macOS-like, left
    ("close:maximize", ["close"], ["max"]),                             # split across both ends
    ("minimize:close", ["min"], ["close"]),
    (":close,minimize", [], ["close", "min"]),                          # any order
    ("appmenu:", [], []),                                               # no buttons at all
    ("close,minimize", ["close", "min"], []),                           # no ':' → all on the left
]


def shown_buttons():
    js = ("var f=s=>[...document.querySelectorAll(s+' .tl')].map(b=>b.className.match(/tl-(min|max|close)/)[1]);"
          "return {left:f('.tb-left'), right:f('.tb-right')}")
    return app.js(js)


def button_layouts():
    seen = []
    for i, (layout, left, right) in enumerate(LAYOUTS):
        app.restart([f"gtk-decoration-layout={layout}"], log_name=f"app-layout-{i}.log")
        got = shown_buttons()
        if got != {"left": left, "right": right}:
            raise AssertionError(f"{layout!r}: expected left {left} right {right}, got {got}")
        # Each button shown does its job (close is checked by the window-close step).
        if "max" in left + right:
            # A fresh profile may open maximised: read the state, then each press must flip it.
            label = lambda: app.js("return document.querySelector('.tl-max').getAttribute('aria-label')")
            first = label()
            other = {"Maximize": "Restore", "Restore": "Maximize"}[first]
            app.click(".tl-max")
            app.wait(lambda: label() == other and ("_NET_WM_STATE_MAXIMIZED" in wm_state()[1]) == (other == "Restore"), 10, other)
            app.click(".tl-max")
            app.wait(lambda: label() == first and ("_NET_WM_STATE_MAXIMIZED" in wm_state()[1]) == (first == "Restore"), 10, first)
        if "min" in left + right:
            app.click(".tl-min")
            app.wait(lambda: "Iconic" in wm_state()[1], 10, "minimised")
            subprocess.run(["xdotool", "windowactivate", "--sync", wm_state()[0]], env=app.env, capture_output=True)
            app.wait(lambda: "Iconic" not in wm_state()[1], 10, "back from minimised")
        # B-19: the brand cell's divider lines up with the left bar's edge, wherever the buttons are.
        cell = app.js("var r=document.querySelector('.tb-brandbox').getBoundingClientRect(); return r.right")
        bar = app.js("var r=document.querySelector('.leftbar').getBoundingClientRect(); return r.right")
        if abs(cell - bar) > 1.5:  # top bar padding 12 px + cell (left bar − 12 px) = the left bar's edge
            raise AssertionError(f"{layout!r}: top-bar cell ends at {cell:.0f} px, left bar at {bar:.0f} px")
        app.shot(f"35-layout-{i}")
        seen.append(f"{layout or '(empty)'} → {'/'.join(left) or '-'} | {'/'.join(right) or '-'}")
    # The window-close step runs under vanilla GNOME's close-only layout.
    app.restart(["gtk-decoration-layout=appmenu:close"], log_name="app-3.log")
    if shown_buttons() != {"left": [], "right": ["close"]}:
        raise AssertionError("close-only layout not shown for the window-close step")
    # D-101: the desktop's layout changes while the app is open — the top bar follows without a restart.
    for layout, left, right in [(":minimize,maximize,close", [], ["min", "max", "close"]),
                                ("close,maximize:", ["close", "max"], []),
                                ("appmenu:close", [], ["close"])]:
        app.send("set-layout " + layout)
        app.wait(lambda: shown_buttons() == {"left": left, "right": right}, 10, f"live change to {layout}")
        seen.append(f"live {layout} → {'/'.join(left) or '-'} | {'/'.join(right) or '-'}")
    return f"{len(LAYOUTS)} layouts exact: " + "; ".join(seen)


step("35-button-layouts", button_layouts)


def sheet_pager():
    """Linux Test B-33: in an Excel file the title bar's sheet arrows and number box did nothing (the tabs under
    the sheet worked). Checked from Home, with a PDF already open, and on a second workbook, with real clicks
    and typing. Fixed in the shared Reader page by Foundation's patch 31 (6c85f066)."""
    book = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests", "ChuvadiReader.Tests", "Fixtures", "Office", "layout.xlsx")
    book = os.path.normpath(book)
    state = lambda: app.js("var b=document.querySelector('.tb-pg-box'), t=document.querySelector('.xv-tab.on'); return [b ? b.value : null, t ? t.textContent.trim() : null]")
    names = lambda: app.js("return [...document.querySelectorAll('.xv-tab')].map(t => t.textContent.trim())")

    def check(where):
        app.wait(lambda: state()[1] is not None, 20, "the workbook shown " + where)
        time.sleep(0.8)
        sheets = names()
        if len(sheets) < 2 or state() != ["1", sheets[0]]:
            raise AssertionError(f"{where}: starts at {state()}, sheets {sheets}")
        app.click_real('.tb-pg-btn[aria-label^="Next"]')
        app.wait(lambda: state() == ["2", sheets[1]], 5, f"{where}: sheet 2 '{sheets[1]}' after Next (now {state()})")
        app.click_real('.tb-pg-btn[aria-label^="Previous"]')
        app.wait(lambda: state() == ["1", sheets[0]], 5, f"{where}: sheet 1 after Previous (now {state()})")
        app.click_real(".tb-pg-box")
        app.xdo("key", "ctrl+a")
        app.xdo("type", str(len(sheets)))
        app.xdo("key", "Return")
        app.wait(lambda: state() == [str(len(sheets)), sheets[-1]], 5, f"{where}: sheet {len(sheets)} '{sheets[-1]}' after typing its number (now {state()})")
        # A tab under the sheet, then the arrows again: the two stay in step.
        app.js("document.querySelectorAll('.xv-tab')[0].click(); return 1")
        app.wait(lambda: state() == ["1", sheets[0]], 5, f"{where}: sheet 1 after its tab (now {state()})")
        app.click_real('.tb-pg-btn[aria-label^="Next"]')
        app.wait(lambda: state() == ["2", sheets[1]], 5, f"{where}: sheet 2 after Next following a tab press (now {state()})")
        return len(sheets)

    while app.js("return document.querySelectorAll('.rtab').length") > 0:
        close_active_tab()
    go_home()
    open_tab(book)
    n = check("from Home")
    close_active_tab()
    open_tab(PDF)
    app.wait(lambda: rendered(0), 20, "the PDF drawn")
    open_tab(book)
    check("with a PDF already open")
    open_tab(os.path.join(FIX, "sample.xlsx"))
    app.wait(lambda: state()[1] is not None and names() and names()[0] == state()[1], 20, "the second workbook shown")
    time.sleep(0.8)
    second = names()
    if len(second) >= 2:
        app.click_real('.tb-pg-btn[aria-label^="Next"]')
        app.wait(lambda: state() == ["2", second[1]], 5, f"second workbook: sheet 2 after Next (now {state()})")
    app.js("var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('layout.xlsx')); t.click(); return 1")
    check("back on the first workbook's tab")
    for _ in range(3):
        close_active_tab()
    return (f"Next, Previous and a typed number change the sheet ({n} sheets) from Home, with a PDF already open, and back on the "
            f"first workbook after a second one ({len(second)} sheet{'s' if len(second) != 1 else ''}); tabs and arrows stay in step")


step("40-sheet-pager", sheet_pager)  # fixed in the shared Reader page by Foundation's patch 31


def encoding_picker():
    """Patch 31 (D-191): "Read this file as" for text, Markdown and HTML files, from the status bar's button and
    from the Document menu's "Text encoding…". Checked in the Linux app with files of known bytes: the text
    follows the choice, the choice is remembered while the file is in Recents, and the file is never changed."""
    import hashlib
    folder = os.path.join(OUT, "encoding")
    os.makedirs(folder, exist_ok=True)
    text = "Café résumé – “quoted” €5, naïve"
    files = {
        "enc-1252.txt": text.encode("cp1252"),
        "enc-utf8.md": ("# " + text + "\n").encode("utf-8"),
        "enc-1252.html": ("<html><body><p>" + text + "</p></body></html>").encode("cp1252"),
    }
    for name, data in files.items():
        with open(os.path.join(folder, name), "wb") as f:
            f.write(data)
    digest = lambda name: hashlib.sha256(open(os.path.join(folder, name), "rb").read()).hexdigest()
    before = {n: digest(n) for n in files}
    # An HTML file is shown in a closed frame: its text is the frame's own document (srcdoc), with entities decoded.
    shown = lambda: app.js("var v=document.querySelector('.rviewer'); if (!v) return ''; var f=v.querySelector('iframe'); "
                           "var t=v.innerText; if (f && f.srcdoc) { var d=new DOMParser().parseFromString(f.srcdoc, 'text/html'); t += ' ' + d.body.textContent; } "
                           "return t.replace(/\\s+/g, ' ').trim()")
    button = lambda: app.js("var b=[...document.querySelectorAll('.sb-btn')].find(b => (b.title||'').startsWith('Read this file as')); return b ? b.textContent.trim() : null")
    rows = lambda: app.js("return [...document.querySelectorAll('.enc-row')].map(r => [r.querySelector('.enc-n').textContent.trim(), r.getAttribute('aria-checked') === 'true'])")
    chosen = lambda: next((n for n, on in rows() if on), None)

    def open_card_from_status_bar():
        app.js("var b=[...document.querySelectorAll('.sb-btn')].find(b => (b.title||'').startsWith('Read this file as')); b.click(); return 1")
        app.wait(lambda: len(rows()) > 0, 5, "the encoding card from the status bar")

    def choose(name):
        ok = app.js(f"var r=[...document.querySelectorAll('.enc-row')].find(r => r.querySelector('.enc-n').textContent.trim() === {json.dumps(name)}); if (!r) return false; r.click(); return true")
        if not ok:
            raise AssertionError(f"no '{name}' in the encoding card: {rows()}")
        app.wait(lambda: chosen() == name, 5, f"'{name}' chosen (now {chosen()})")
        time.sleep(0.8)

    said = []
    # A Windows-1252 text file: Automatic reads it right; UTF-8 does not fit and says so; back again.
    open_tab(os.path.join(folder, "enc-1252.txt"))
    app.wait(lambda: text in shown(), 15, f"the Windows-1252 file read automatically (shown: {shown()[:80]!r})")
    label = button()
    if not label or "1252" not in label:
        raise AssertionError(f"the status bar's encoding button on a Windows-1252 file: {label!r}")
    open_card_from_status_bar()
    names = [n for n, _ in rows()]
    if names != ["Automatic", "UTF-8", "Windows-1252", "UTF-16 LE", "UTF-16 BE"] or chosen() != "Automatic":
        raise AssertionError(f"the encoding card: {rows()}")
    choose("UTF-8")
    app.wait(lambda: text not in shown() and "Caf" in shown(), 5, f"the text re-read as UTF-8 (shown: {shown()[:80]!r})")
    note = app.js("var e=document.querySelector('.fc-status.err'); return e ? e.textContent.trim() : ''")
    if not note:
        raise AssertionError("read as UTF-8, bytes that don't fit: the card says nothing")
    if "UTF-8" not in (button() or ""):
        raise AssertionError(f"the status bar's button after choosing UTF-8: {button()!r}")
    app.shot("41-encoding-utf8-on-1252")
    said.append(f"Windows-1252 text: Automatic reads it (button '{label}'); as UTF-8 the accents go and the card says \"{note[:70]}\"")

    # Remembered with Recents: close the tab, open the file again.
    app.key("Escape")
    close_active_tab()
    open_tab(os.path.join(folder, "enc-1252.txt"))
    app.wait(lambda: "Caf" in shown(), 15, "the file open again")
    time.sleep(0.8)
    if text in shown() or "UTF-8" not in (button() or ""):
        raise AssertionError(f"the choice was not remembered: button {button()!r}, shown {shown()[:60]!r}")
    # From the Document menu's entry this time, and back to Automatic (which forgets the choice).
    cmd = next((c for c in app.commands() if c["Id"] == "doc.encoding"), None)
    if not cmd or not cmd["Enabled"] or cmd["Label"] != "Text encoding…" or cmd["Group"] != "Document":
        raise AssertionError(f"the Document menu's entry: {cmd}")
    app.invoke("doc.encoding")
    app.wait(lambda: chosen() == "UTF-8", 5, f"the card from the Document menu with UTF-8 chosen (now {rows()})")
    choose("Windows-1252")
    app.wait(lambda: text in shown(), 5, "the text right again as Windows-1252")
    choose("UTF-16 LE")
    app.wait(lambda: "Caf" not in shown(), 5, "the text re-read as UTF-16 LE")
    choose("Automatic")
    app.wait(lambda: text in shown(), 5, "the text right again on Automatic")
    app.key("Escape")
    close_active_tab()
    said.append("the choice is remembered on opening the file again; the Document menu's \"Text encoding…\" opens the same card; Windows-1252, UTF-16 LE and Automatic each re-read it")

    # Markdown (UTF-8) and HTML (Windows-1252) have it too.
    for name, wrong in (("enc-utf8.md", "Windows-1252"), ("enc-1252.html", "UTF-8")):
        open_tab(os.path.join(folder, name))
        app.wait(lambda: text in shown(), 15, f"{name} read automatically (shown: {shown()[:80]!r})")
        if not button():
            raise AssertionError(f"{name}: no encoding button in the status bar")
        open_card_from_status_bar()
        choose(wrong)
        app.wait(lambda: text not in shown(), 5, f"{name} re-read as {wrong}")
        choose("Automatic")
        app.wait(lambda: text in shown(), 5, f"{name} right again on Automatic")
        app.key("Escape")
        close_active_tab()
    said.append("Markdown and HTML files have it too")

    # Not offered where it means nothing.
    open_tab(PDF)
    app.wait(lambda: rendered(0), 20, "the PDF drawn")
    if button() is not None or any(c["Id"] == "doc.encoding" and c["Enabled"] for c in app.commands()):
        raise AssertionError("a PDF offers a text encoding")
    close_active_tab()
    after = {n: digest(n) for n in files}
    if after != before:
        raise AssertionError(f"a file was changed by choosing an encoding: {[n for n in files if after[n] != before[n]]}")
    said.append("a PDF does not offer it; the three files are byte-for-byte as written")
    return "; ".join(said)


step("41-encoding-picker", encoding_picker)


def ask_before_closing():
    """D-190 on Linux: with unsaved marks, closing a tab, all tabs or the window asks Save / Save as / Discard /
    Cancel. The window is closed the real ways: Alt F4 (the desktop's close request) and the title bar's own
    close button. Cancel and Escape keep everything; the window goes only when every file has an answer."""
    import hashlib, shutil
    folder = os.path.join(OUT, "closeq")
    os.makedirs(folder, exist_ok=True)
    files = {n: os.path.join(folder, n) for n in ("ask-a.pdf", "ask-b.pdf")}
    for path in files.values():
        shutil.copyfile(PDF, path)
    digest = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
    before = {n: digest(path) for n, path in files.items()}
    shapes = lambda: app.js("return document.querySelectorAll('.mk-shape').length")
    tabs = lambda: app.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())")
    card = lambda: app.js("var c=document.querySelector('.closeq'); return c ? {title: c.querySelector('.closeq-title').textContent.trim(), "
                          "text: c.querySelector('.closeq-text').textContent.replace(/\\s+/g,' ').trim(), "
                          "buttons: [...c.querySelectorAll('button')].map(b => b.textContent.trim())} : null")

    def show(name):
        app.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes({json.dumps(name)})); t.click(); return 1")
        app.wait(lambda: app.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.textContent.includes({json.dumps(name)})"), 10, name + " on screen")
        app.wait(lambda: rendered(0), 20, name + " drawn")
        time.sleep(0.6)

    def mark_mode():
        if not app.js("return [...document.querySelectorAll('.srail button')].some(b => b.offsetParent && (b.getAttribute('aria-label')||'').startsWith('Rectangle'))"):
            app.click(".lb-mode", 1)  # Mark
            time.sleep(1.2)

    def draw():
        mark_mode()
        click_label(".srail", "Rectangle")
        focus_main()
        gx, gy = (int(v) for v in window_geometry()[0].split(","))
        x, y = app.js("var d=document.querySelector('.rdesk').getBoundingClientRect(), l=document.querySelector('.mk-layer').getBoundingClientRect(); "
                      "return [Math.round(Math.max(l.left, d.left) + 80), Math.round(Math.max(l.top, d.top, 90) + 80)]")
        n = shapes()
        app.xdo("mousemove", str(gx + x), str(gy + y))
        app.xdo("mousedown", "1")
        for i in range(1, 9):
            app.xdo("mousemove", str(gx + x + 12 * i), str(gy + y + 8 * i))
            time.sleep(0.04)
        app.xdo("mouseup", "1")
        app.wait(lambda: shapes() == n + 1, 5, "a rectangle drawn")
        app.key("Escape")
        time.sleep(0.3)

    def answer(label):
        ok = app.js(f"var b=[...document.querySelectorAll('.closeq button')].find(b => b.textContent.trim() === {json.dumps(label)}); if (!b) return false; b.click(); return true")
        if not ok:
            raise AssertionError(f"no '{label}' on the card: {card()}")
        time.sleep(1.2)

    def asked(what):
        app.wait(lambda: card() is not None, 6, "the question after " + what)
        time.sleep(0.4)
        if not app.alive():
            raise AssertionError(f"the app closed on {what} with unsaved marks")
        return card()

    def alt_f4():
        focus_main()
        app.xdo("key", "alt+F4")

    said = []
    for name, path in files.items():
        open_tab(path)
    show("ask-a.pdf")
    draw()
    show("ask-b.pdf")
    if shapes() != 0:
        raise AssertionError("the other tab shows the first tab's mark")
    show("ask-a.pdf")
    if shapes() != 1:
        raise AssertionError(f"the mark did not stay with its tab: {shapes()} shapes after a tab switch")
    said.append("the mark stays with its tab")

    # A tab's own x.
    app.js("document.querySelector('.rtab.active .rtab-x').click(); return 1")
    c = asked("the tab's x")
    if "ask-a.pdf" not in c["title"] or c["buttons"] != ["Save", "Save as…", "Discard", "Cancel"]:
        raise AssertionError(f"the card on closing a tab: {c}")
    answer("Cancel")
    if card() or "ask-a.pdf" not in tabs() or shapes() != 1:
        raise AssertionError(f"Cancel on a tab's x: card {card()}, tabs {tabs()}, shapes {shapes()}")
    said.append("tab x asks (Save / Save as… / Discard / Cancel), Cancel keeps it")

    # Close all tabs (Ctrl Shift W, real key).
    focus_main()
    app.xdo("key", "ctrl+shift+w")
    asked("Close all tabs")
    app.key("Escape")
    time.sleep(0.8)
    if card() or len(tabs()) != 2 or shapes() != 1:
        raise AssertionError(f"Escape on Close all tabs: card {card()}, tabs {tabs()}, shapes {shapes()}")
    # Close inactive tabs (Ctrl Alt W) from the other tab: the file with marks is the inactive one.
    show("ask-b.pdf")
    focus_main()
    app.xdo("key", "ctrl+alt+w")
    c = asked("Close inactive tabs")
    if "ask-a.pdf" not in c["title"]:
        raise AssertionError(f"Close inactive tabs asked about the wrong file: {c}")
    seen_while_asked = shapes()
    app.shot("39-ask-inactive-tab")
    answer("Cancel")
    if card() or len(tabs()) != 2:
        raise AssertionError(f"Cancel on Close inactive tabs: card {card()}, tabs {tabs()}")
    show("ask-a.pdf")
    mark_mode()  # the file asked about is shown in Read, where marks are not drawn
    if shapes() != 1:
        raise AssertionError(f"the mark was lost by a cancelled Close inactive tabs ({shapes()} shapes in Mark)")
    said.append(f"Close all tabs and Close inactive tabs ask, Escape and Cancel keep both (while asked about the inactive file, "
                f"{seen_while_asked} of its 1 mark is on screen: it is shown in Read)")

    # The window: Alt F4, then the title bar's close button, then a second request while the question is up.
    alt_f4()
    asked("Alt F4")
    answer("Cancel")
    if card() or not app.alive() or shapes() != 1:
        raise AssertionError("Cancel after Alt F4 did not leave the app as it was")
    app.click_real(".tl-close")
    asked("the title bar's close button")
    app.shot("39-ask-before-closing")
    alt_f4()
    time.sleep(1.0)
    if not app.alive() or app.js("return document.querySelectorAll('.closeq').length") != 1:
        raise AssertionError("a second close while the question is up closed the app or asked twice")
    answer("Cancel")
    said.append("Alt F4 and the close button ask, a second close asks once, Cancel keeps the window")

    # Two files with marks: one question each; Save on the first, Discard on the second; then the window goes.
    show("ask-b.pdf")
    draw()
    alt_f4()
    c = asked("Alt F4 with two files")
    if "File 1 of 2" not in c["text"]:
        raise AssertionError(f"two files with marks, first card: {c}")
    first = "ask-a.pdf" if "ask-a.pdf" in c["title"] else "ask-b.pdf"
    second = "ask-b.pdf" if first == "ask-a.pdf" else "ask-a.pdf"
    answer("Save")
    app.wait(lambda: (card() or {}).get("text", "").find("File 2 of 2") >= 0 or not app.alive(), 15, "the second file's question")
    c = card()
    if not c or second not in c["title"]:
        raise AssertionError(f"the second card: {c}")
    if not app.alive():
        raise AssertionError("the app closed before the second file was answered")
    # The window closes on this answer, so the click is made just after the driver has replied.
    app.js("var b=[...document.querySelectorAll('.closeq button')].find(b => b.textContent.trim() === 'Discard'); setTimeout(() => b.click(), 200); return 1")
    app.wait(lambda: not app.alive(), 15, "the window to close once every file has an answer")
    code = app.proc.returncode
    after = {n: digest(path) for n, path in files.items()}
    if after[first] == before[first]:
        raise AssertionError(f"Save did not write the marks into {first}")
    if after[second] != before[second]:
        raise AssertionError(f"Discard changed {second}")
    said.append(f"two files: asked one at a time; Save wrote {first}, Discard left {second} as it was; then the app closed (exit {code})")
    app.restart(log_name="app-after-ask.log")
    time.sleep(1.5)
    return "; ".join(said)


step("39-ask-before-closing", ask_before_closing, shot=False)


def window_close():
    app.click_real(".tl-close")
    app.wait(lambda: not app.alive(), 15, "app exit")
    return f"exit code {app.proc.returncode}"


baseline_close = errors_in_log()
try:
    results.append({"step": "36-window-close", "ok": True, "detail": window_close(), "s": 0})
except Exception as ex:
    results.append({"step": "36-window-close", "ok": False, "detail": str(ex), "s": 0})
app.stop()

passed = sum(r["ok"] for r in results)
with open(os.path.join(OUT, "results.json"), "w") as f:
    json.dump(results, f, indent=1)
with open(os.path.join(OUT, "report.md"), "w") as f:
    f.write(f"# Linux UI test pass\n\n{passed} of {len(results)} steps passed.\n\n| Step | Result | Detail |\n|---|---|---|\n")
    for r in results:
        f.write(f"| {r['step']} | {'pass' if r['ok'] else '**FAIL**'} | {r['detail'].replace('|', '/')[:400]} |\n")
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
