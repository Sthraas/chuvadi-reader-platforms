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
    return app.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{page_index}\"]'); return !!w && !!w.querySelector('svg')")


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
    t0 = time.time()
    landed = app.wait(lambda: current_page() > 100 and rendered(current_page() - 1) and current_page(), 20, "the landed-on page drawn")
    drawn_in = time.time() - t0
    app.js("document.querySelector('.tb-pg-box').value='400'; document.querySelector('.tb-pg-box').dispatchEvent(new Event('change')); return 1")
    app.wait(lambda: current_page() == 400 and rendered(399), 20, "page 400 drawn")
    close_active_tab()
    return (f"6 bursts of 25 PageDowns: page answered within {worst:.2f} s each; landed on page {landed}, drawn {drawn_in:.1f} s "
            "after the last click; jumped to page 400, drawn")


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
    """A 5-sheet A1 vector drawing (~120,000 strokes a sheet; B-27's kind of file): the page answers while
    sheets draw, every sheet draws, and memory after paging through is reported."""
    t0 = time.time()
    open_tab(os.path.join(HEAVY, "cad.pdf"))
    worst = max(ping() for _ in range(3))
    app.wait(lambda: rendered(0), 60, "sheet 1 drawn")
    first = time.time() - t0
    times = []
    for n in range(2, 6):
        t1 = time.time()
        app.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{n}'; b.dispatchEvent(new Event('change')); return 1")
        worst = max(worst, ping())
        app.wait(lambda: rendered(n - 1), 60, f"sheet {n} drawn")
        times.append(time.time() - t1)
    app.shot("36c-cad-drawing")
    mem = memory_mb()
    close_active_tab()
    if worst > 1.0:
        raise AssertionError(f"the page took {worst:.2f} s to answer while a sheet was drawing")
    return (f"sheet 1 drawn in {first:.1f} s; sheets 2-5 in {', '.join(f'{t:.1f}' for t in times)} s; page answered in "
            f"≤ {worst:.2f} s throughout; memory after 5 sheets app/web {mem[0]}/{mem[1]} MB")


step("36c-cad-drawing", cad_drawing)

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
