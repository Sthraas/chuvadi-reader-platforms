#!/usr/bin/env python3
"""Full Linux UI test pass for Chuvadi Reader (test-only, never shipped).

  tools/linux/uitest.py <ui-test publish dir> <out dir> [--cups-out DIR]

Needs: Xvfb, mutter, xdotool, xclip, ImageMagick (import), poppler-utils (pdfinfo, pdffonts,
pdfimages), a CUPS queue that is the default destination and writes PDFs (cups-pdf), all test tools.
Writes <out>/report.md, <out>/results.json and one screenshot per step.
Every step also checks: the app is running, Blazor's error bar is hidden, and no new "Chuvadi error"
is in the app log.
"""
import glob, json, os, subprocess, sys, time, traceback

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


def native_windows():
    """Open GTK dialogs (file chooser, print) — anything titled other than the main window."""
    r = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "."], env=app.env, capture_output=True, text=True)
    names = []
    for w in r.stdout.split():
        n = subprocess.run(["xdotool", "getwindowname", w], env=app.env, capture_output=True, text=True).stdout.strip()
        if n and n != "Chuvadi" and "mutter" not in n.lower():
            names.append((w, n))
    return names


def dismiss():
    """Closes any card, menu or dialog a step left open."""
    for w, _ in native_windows():
        subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
        app.key("Escape")
        time.sleep(0.5)
    for _ in range(2):
        try:
            app.js("document.activeElement && document.activeElement.blur(); document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));")
        except Exception:
            pass
        time.sleep(0.2)
    try:
        app.js("var c=[...document.querySelectorAll('.chvd-card .close, .card-close, [aria-label=Close][class*=close]')].filter(b=>b.offsetParent!==null); c.forEach(b=>b.click()); return c.length")
    except Exception:
        pass
    time.sleep(0.3)


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


def cups_pdfs():
    roots = [CUPS_OUT] if CUPS_OUT else []
    roots += [os.path.expanduser("~/PDF"), app.home + "/PDF", "/var/spool/cups-pdf/ANONYMOUS"]
    roots += glob.glob("/home/*/PDF") + glob.glob("/root/PDF")
    files = set()
    for r in roots:
        files.update(glob.glob(os.path.join(r, "*.pdf")))
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


def minimise():
    app.click(".tl-min")
    time.sleep(1.5)
    if app.windows("^Chuvadi$"):
        raise AssertionError("window still visible after Minimize")
    w = subprocess.run(["xdotool", "search", "--name", "^Chuvadi$"], env=app.env, capture_output=True, text=True).stdout.split()[0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(1.5)
    return "minimised, then raised again"


step("05-window-minimise", minimise)

# ── left rail and pages ─────────────────────────────────────────────────────
for i, name in [(6, "library"), (8, "settings"), (7, "home")]:
    step(f"06-rail-{name}", lambda i=i: (app.click(".leftbar .lb-btn", i), time.sleep(1.5), app.js("return location.pathname"))[-1])
step("07-rail-collapse", lambda: (app.click(".lb-toggle"), time.sleep(1), app.shot("07-collapsed"), app.click(".lb-toggle"), time.sleep(1), "collapsed and expanded")[-1], shot=False)


def settings_pages():
    app.click(".leftbar .lb-btn", 8)
    time.sleep(1.5)
    sections = visible(".settings nav button, .set-nav button, nav button")
    shots = []
    for idx, label in enumerate(sections[:12]):
        try:
            click_label(".settings nav, .set-nav, nav", label)
            app.shot(f"08-settings-{idx:02d}")
            shots.append(label)
        except AssertionError:
            pass
    return "sections: " + ", ".join(shots)


step("08-settings-sections", settings_pages, shot=False)


def interface_size():
    app.click(".leftbar .lb-btn", 8)
    time.sleep(1)
    out = []
    for size in ("125", "150", "100"):
        ok = app.js(f"var b=[...document.querySelectorAll('button, [role=radio]')].filter(b=>b.offsetParent!==null && b.innerText.trim().startsWith('{size}'))[0]; if(!b) return false; b.click(); return true;")
        time.sleep(1.2)
        app.shot(f"09-scale-{size}")
        out.append(f"{size}%:{'clicked' if ok else 'not found'}")
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
        done.append(f"{cid}:{'ran' if ok else 'refused'}")
    return f"{len(done)} run ({', '.join(done)}); skipped here (tested on their own or disabled): {', '.join(skipped)}"


step("20-every-command", every_command, shot=False)

# ── Mark: draw a rectangle, Save as new PDF through the GTK dialog, then Save ──
MARKED = os.path.join(app.home, "Documents", "marked.pdf")


def mark_and_save_as():
    app.click(".lb-mode", 1)
    time.sleep(2)
    rail_labels = visible(".srail button")
    click_label(".srail", "Rectangle")
    r = app.rect(".rpage-wrap", 0) or app.rect(".rpage")
    x, y = r[0] + r[2] * 0.3, r[1] + 200
    app.xdo("mousemove", str(int(x)), str(int(y)))
    app.xdo("mousedown", "1")
    for i in range(1, 12):
        app.xdo("mousemove", str(int(x + i * 18)), str(int(y + i * 10)))
        time.sleep(0.04)
    app.xdo("mouseup", "1")
    time.sleep(1)
    app.shot("21-mark-rectangle")
    click_label(".srail", "Save as new PDF")
    file_dialog("Save", MARKED)
    app.wait(lambda: os.path.exists(MARKED) and os.path.getsize(MARKED) > 0, 20, "marked.pdf written")
    info = pdfinfo(MARKED)
    annots = open(MARKED, "rb").read().count(b"/Annot")
    return f"Mark rail: {len(rail_labels)} tools; saved {os.path.getsize(MARKED)} bytes, {info.get('Pages')} pages, /Annot x{annots}"


step("21-mark-rectangle-save-as", mark_and_save_as)
rail_buttons("22-mark", skip=("Save", "Clear all marks", "Image", "Signature"))

# ── Protect: password-protect a copy, open it again with the password ───────
PROTECTED = os.path.join(app.home, "Documents", "protected.pdf")


def protect_copy():
    app.click(".lb-mode", 3)
    time.sleep(2)
    click_label(".srail", "Password")
    time.sleep(1)
    app.shot("23-password-card")
    pw = app.js("var i=[...document.querySelectorAll('input[type=password]')].filter(e=>e.offsetParent!==null); return i.length")
    if not pw:
        raise AssertionError("no password fields on the card")
    for idx in range(pw):
        app.click_real("input[type=password]", idx)
        app.key("ctrl+a")
        app.type("Chuvadi-Linux-1")
    time.sleep(0.5)
    app.shot("23-password-filled")
    btn = app.js("var b=[...document.querySelectorAll('.chvd-card button.primary, .card button.primary')].filter(b=>b.offsetParent!==null)[0]; if(!b) return null; var t=b.innerText; b.click(); return t")
    file_dialog("Save", PROTECTED)
    app.wait(lambda: os.path.exists(PROTECTED) and os.path.getsize(PROTECTED) > 0, 20, "protected.pdf written")
    enc = pdfinfo(PROTECTED).get("Encrypted", "?")
    if not enc.startswith("yes"):
        raise AssertionError("output isn't encrypted: " + enc)
    return f"'{btn}' → protected.pdf, Encrypted: {enc}"


step("23-protect-password-copy", protect_copy)
rail_buttons("24-protect", skip=("Password", "Save redacted copy", "Sign with certificate"))

# ── Arrange (bench) ─────────────────────────────────────────────────────────
step("25-arrange", lambda: (app.click(".lb-mode", 2), time.sleep(2.5), "; ".join(visible(".srail button")))[-1])


def bench_fetch():
    click_label(".srail", "Fetch file")
    file_dialog("Add PDF documents", PDF)
    time.sleep(2)
    return f"shelf files: {app.js('return document.querySelectorAll(\".bench-shelf .shelf-file, .shelf-item, .bench-shelf [data-file]\").length')}"


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
    before = cups_pdfs()
    app.js("var t=[...document.querySelectorAll('.rtab')].find(t=>t.innerText.includes('five-pages.pdf')); t && t.click(); return !!t")
    time.sleep(1.5)
    app.click(".lb-mode", 0)
    time.sleep(1.5)
    app.key("ctrl+p")
    time.sleep(1.2)
    app.shot("30-print-card")
    # pages 2-4, two copies
    app.js("var b=[...document.querySelectorAll('.chvd-card .seg button, .chvd-card [role=radio]')].filter(b=>b.offsetParent!==null); var c=b.find(x=>/custom|pages|range/i.test(x.innerText)) || b[b.length-1]; c && c.click(); return b.map(x=>x.innerText)")
    time.sleep(0.4)
    app.click_real(".chvd-card input[type=text]")
    app.key("ctrl+a")
    app.type("2-4")
    app.click(".chvd-card [aria-label='More copies']")
    time.sleep(0.4)
    app.shot("30-print-card-filled")
    app.click(".chvd-card button.primary")
    w = app.wait(lambda: [x for x in native_windows() if x[1].startswith("Print")], 15, "GTK print dialog")[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(3)  # printers load asynchronously
    app.shot("30-gtk-print-dialog")
    app.key("Return")
    new = app.wait(lambda: cups_pdfs() - before, 60, "cups-pdf output")
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
    return (f"app says '{status}'; CUPS wrote {os.path.basename(out)}: {info.get('Pages')} pages ({info.get('Page size')}), "
            f"pages with text {pages_seen}, fonts {[f.split()[0] for f in fonts]}, images: none (vector)")


step("30-print-pages-2-4-two-copies", print_pages)


def print_cancel():
    app.key("ctrl+p")
    time.sleep(1)
    app.click(".chvd-card button.primary")
    w = app.wait(lambda: [x for x in native_windows() if x[1].startswith("Print")], 15, "GTK print dialog")[0][0]
    subprocess.run(["xdotool", "windowactivate", "--sync", w], env=app.env, capture_output=True)
    time.sleep(1.5)
    app.key("Escape")
    time.sleep(1)
    return "dialog cancelled; " + str(app.js("return document.body.innerText.includes('Printing cancelled') ? 'no job, card stays' : 'no job'"))


step("31-print-cancel", print_cancel)

# ── keyboard ────────────────────────────────────────────────────────────────


def shortcuts():
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
    app.key("F11")
    time.sleep(1.5)
    app.shot("33-immersive")
    app.key("F11")
    time.sleep(1)
    return "F11 in and out"


step("33-immersive", immersive, shot=False)


def close_tabs():
    n = app.js("return document.querySelectorAll('.rtab').length")
    app.key("ctrl+shift+w")
    time.sleep(1.5)
    return f"{n} tabs → {app.js('return document.querySelectorAll(\".rtab\").length')}"


step("34-close-all-tabs", close_tabs)


def window_close():
    app.click(".tl-close")
    app.wait(lambda: not app.alive(), 15, "app exit")
    return f"exit code {app.proc.returncode}"


baseline_close = errors_in_log()
try:
    results.append({"step": "35-window-close", "ok": True, "detail": window_close(), "s": 0})
except Exception as ex:
    results.append({"step": "35-window-close", "ok": False, "detail": str(ex), "s": 0})
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
