#!/usr/bin/env python3
"""Mac Test orchestrator — TESTING ONLY, never shipped.

Runs the T2–T5 cases against an installed /Applications/Chuvadi.app using the macdrive driver, and writes
every observation to <out>/results.json plus screenshots, AX dumps and logs. It never stops on a failure:
each case records pass / fail / info with its evidence, and the next case starts from a known state.

  run_ui.py <macdrive> <fixtures> <out> --suite full|core [--runs 10]
"""
import argparse
import json
import os
import plistlib
import re
import shutil
import statistics
import subprocess
import sys
import time
import traceback

APP = "/Applications/Chuvadi.app"
BID = "in.sthraas.chuvadi.reader"
NAME = "Chuvadi"
HOME = os.path.expanduser("~")
STATE = f"{HOME}/Library/Application Support/Chuvadi"
LOGS = f"{HOME}/Library/Logs/Chuvadi"
WEBKIT = [f"{HOME}/Library/WebKit/{BID}", f"{HOME}/Library/Caches/{BID}", f"{HOME}/Library/HTTPStorages/{BID}",
          f"{HOME}/Library/Saved Application State/{BID}.savedState", f"{HOME}/Library/Preferences/{BID}.plist"]
THEMES = ["light", "dark", "palm", "indigo", "contrast"]

ap = argparse.ArgumentParser()
ap.add_argument("drive")
ap.add_argument("fixtures")
ap.add_argument("out")
ap.add_argument("--suite", default="core")
ap.add_argument("--runs", type=int, default=10)
A = ap.parse_args()
OUT = A.out
os.makedirs(f"{OUT}/shots", exist_ok=True)
os.makedirs(f"{OUT}/ax", exist_ok=True)
os.makedirs(f"{OUT}/timing", exist_ok=True)
FX = A.fixtures
RESULTS = []


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(cmd, timeout=60, check=False):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, errors="replace", timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        if check and p.returncode != 0:
            raise RuntimeError(f"{cmd} → {p.returncode}: {out[-800:]}")
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired as e:
        return 124, f"timeout after {timeout}s: {cmd}"


def drive(*args, timeout=60):
    return sh([A.drive, *[str(a) for a in args]], timeout=timeout)


def record(case, status, note="", **evidence):
    RESULTS.append({"case": case, "status": status, "note": note, **evidence})
    log(f"[{status.upper()}] {case}: {note}")
    with open(f"{OUT}/results.json", "w") as f:
        json.dump(RESULTS, f, indent=1, ensure_ascii=False)


def case(cid):
    def wrap(fn):
        def run(*a, **k):
            try:
                fn(*a, **k)
            except Exception as e:
                record(cid, "error", f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])
                quit_app()
        run.cid = cid
        return run
    return wrap


def pids():
    _, out = sh(["pgrep", "-x", "ChuvadiReader.Mac"])
    return [int(x) for x in out.split()] if out else []


def quit_app(force=False):
    if not pids():
        return
    drive("quit", NAME, *(["--force"] if force else []), timeout=20)
    for _ in range(50):
        if not pids():
            break
        time.sleep(0.1)
    if pids():
        sh(["pkill", "-9", "-x", "ChuvadiReader.Mac"])
        time.sleep(0.5)


def write_settings(values):
    os.makedirs(STATE, exist_ok=True)
    with open(f"{STATE}/settings.json", "w") as f:
        json.dump(values, f)


def read_settings():
    try:
        with open(f"{STATE}/settings.json") as f:
            return json.load(f)
    except Exception:
        return None


SAVED_LOGS = [0]


def reset_state(settings=None):
    quit_app()
    # keep the app's own error log (D-132) before the folder is cleared
    if os.path.isdir(LOGS) and os.listdir(LOGS):
        SAVED_LOGS[0] += 1
        shutil.copytree(LOGS, f"{OUT}/chuvadi-logs/{SAVED_LOGS[0]:03d}", dirs_exist_ok=True)
    for d in [STATE, LOGS, *WEBKIT]:
        shutil.rmtree(d, ignore_errors=True) if os.path.isdir(d) else (os.path.exists(d) and os.remove(d))
    if settings is not None:
        write_settings(settings)


def window_up(timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, out = drive("windows")
        for line in out.splitlines():
            if line.startswith(NAME + "\t") and "layer=0" in line:
                return line
        time.sleep(0.2)
    return None


LAUNCHES = [0]


def launch(*files, settle=3.0, fresh=False):
    """Launches through LaunchServices with the app's stdout/stderr kept (unhandled .NET exceptions land there)."""
    if fresh:
        quit_app()
    if not pids():
        LAUNCHES[0] += 1
        os.makedirs(f"{OUT}/applogs", exist_ok=True)
        lp = f"{OUT}/applogs/{LAUNCHES[0]:03d}.txt"
        sh(["open", "--stdout", lp, "--stderr", lp, "-a", APP, *files], timeout=30)
    else:
        sh(["open", "-a", APP, *files], timeout=30)
    w = window_up()
    time.sleep(settle)
    drive("activate", NAME)
    time.sleep(0.3)
    return w


def shot(name):
    rc, out = drive("capture", NAME, f"{OUT}/shots/{name}.png")
    return f"shots/{name}.png" if rc == 0 else f"(capture failed: {out})"


def axdump(name):
    drive("axdump", NAME, f"{OUT}/ax/{name}.txt", timeout=120)
    try:
        return open(f"{OUT}/ax/{name}.txt", encoding="utf-8").read()
    except Exception:
        return ""


def menu(*path):
    return drive("menu", NAME, *path)


def press(text, contains=False, role=None, index=0, click=False):
    args = ["press", NAME, text] + (["--click"] if click else [])
    if contains:
        args.append("--contains")
    if role:
        args += ["--role", role]
    if index:
        args += ["--index", str(index)]
    return drive(*args)


def find(text, contains=False, timeout=10):
    return drive("find", NAME, text, *(["--contains"] if contains else []), "--timeout", timeout, timeout=timeout + 15)


def rss_mb():
    p = pids()
    if not p:
        return None
    _, out = sh(["ps", "-o", "rss=", "-p", str(p[0])])
    try:
        return round(int(out.strip()) / 1024, 1)
    except ValueError:
        return None


def last_startup_block():
    try:
        txt = open(f"{LOGS}/startup.log").read().strip().split("\n\n")[-1]
        return {m[0]: float(m[1]) for m in re.findall(r"^(\S+)\s+(\d+) ms$", txt, re.M)}
    except Exception:
        return {}


def find_menu_item(menus, pred):
    """Depth-first search of a menudump JSON for the first item matching pred; returns its title path."""
    def rec(items, path):
        for it in items:
            p = path + [it.get("title", "")]
            if pred(it):
                return p
            if "items" in it:
                r = rec(it["items"], p)
                if r:
                    return r
        return None
    for top in menus:
        r = rec(top.get("items", []), [top["title"]])
        if r:
            return r
    return None


def menu_dump(name, live=True):
    path = f"{OUT}/ax/menus-{name}.json"
    drive("menudump", NAME, path, *(["--live"] if live else []), timeout=120)
    try:
        return json.load(open(path))
    except Exception:
        return []


def menu_by_title(menus, title, contains=False):
    return find_menu_item(menus, lambda it: (title.lower() in it.get("title", "").lower()) if contains
                          else it.get("title", "") == title)


def press_menu(menus, title, contains=False):
    p = menu_by_title(menus, title, contains)
    if not p:
        return 1, f"no menu item '{title}'"
    return menu(*p)


def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"n": len(vals), "median": round(statistics.median(vals)), "worst": round(max(vals)),
            "best": round(min(vals)), "all": [round(v) for v in vals]}


# ───────────────────────────── Ui-driven helpers (round 2) ─────────────────────────────
# Round 1 showed that files handed over by macOS never open and the menu bar has no Chuvadi items (BUGS M-01,
# M-02), so documents are opened through the app's own Open panel (⌘O) and commands run through ⌘K.

DIAG = f"{HOME}/Library/Logs/DiagnosticReports"


def crash_reports():
    try:
        return sorted(f for f in os.listdir(DIAG) if "ChuvadiReader" in f)
    except FileNotFoundError:
        return []


def screen(name):
    sh(["screencapture", "-x", f"{OUT}/shots/{name}.png"])
    return f"shots/{name}.png"


def open_doc(path, settle=4.0, label=None, how="button"):
    """Opens a document through Chuvadi's own Open panel: the left bar's Open button (or ⌘O), then ⇧⌘G in the
    panel and the path. Returns (opened, first_page_ms). Leaves a screen capture of the panel the first time."""
    if not pids():
        launch(settle=3)
    drive("activate", NAME)
    time.sleep(0.3)
    def panel_up(timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            _, w = drive("windows")
            # the Open panel is a separate window of the app (layer 8), next to the main window (layer 0)
            if sum(1 for l in w.splitlines() if l.startswith(NAME + "\t")) > 1:
                return round(time.time() - t0, 1)
            time.sleep(0.3)
        return None
    if how == "key":
        drive("key", "cmd+o")
    else:
        rc, o = press("Open ⌘O")
        if rc != 0:
            press("Open document")
    waited = panel_up(10)
    if waited is None and find("Open a document", timeout=1)[0] != 0:
        PANEL_RETRIES.append(os.path.basename(path))
        press("Open ⌘O")
        waited = panel_up(10)
    PANEL_WAITS.append(waited)
    time.sleep(0.8)
    global PANEL_SHOT
    if not PANEL_SHOT:
        PANEL_SHOT = screen("open-panel-" + how)
        drive("windows")
    drive("activate", NAME)
    drive("key", "cmd+shift+g")
    time.sleep(2.5)
    rc, o = drive("focusset", NAME, path)
    if "set: ok" not in o:
        drive("type", path)
    time.sleep(1.5)
    drive("key", "return")
    time.sleep(2.5)
    ms = None
    if label:
        rc, out = drive("waitpage", NAME, f"{OUT}/timing", label, "--key", "return", "--timeout", 20, timeout=40)
        try:
            ms = json.loads(out.splitlines()[-1]).get("first_page")
        except Exception:
            ms = None
    else:
        drive("key", "return")
    time.sleep(settle)
    rc, _ = find(os.path.basename(path), contains=True, timeout=3)
    return rc == 0, ms


PANEL_SHOT = None
PANEL_WAITS = []
PANEL_RETRIES = []


def run_cmd(label, settle=1.5):
    """Runs a command through the ⌘K bar, as a person would: ⌘K, type, Return."""
    drive("activate", NAME)
    drive("key", "cmd+k")
    time.sleep(0.8)
    drive("type", label)
    time.sleep(0.8)
    drive("key", "return")
    time.sleep(settle)


def focus_field(label):
    """Clicks the centre of the AX element whose label is `label` (puts the caret in a text field)."""
    rc, out = find(label, timeout=3)
    m = re.search(r"@(-?\d+),(-?\d+) (\d+)x(\d+)", out)
    if rc != 0 or not m:
        return False
    x, y, w, h = map(int, m.groups())
    drive("click", x + w // 2, y + h // 2)
    time.sleep(0.5)
    return True


def ax_text(name):
    return axdump(name)


def ui_error():
    """True when Blazor's "An error occurred. Reload" bar is showing (an unhandled exception in the Ui)."""
    rc, _ = find("Reload", timeout=1)
    return rc == 0


def app_log():
    try:
        return open(f"{OUT}/applogs/{LAUNCHES[0]:03d}.txt", errors="replace").read()
    except Exception:
        return ""


def exceptions_in(text):
    out = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if re.search(r"Exception|Unhandled|crit:|fail:", l):
            out.append("\n".join(lines[i:i + 14]))
    return out[:6]


@case("T4.0b Settings page")
def t4_0b():
    reset_state({"theme": "light"})
    launch(settle=4)
    clean = not ui_error()
    press("Settings")
    time.sleep(3)
    err = ui_error()
    s = shot("settings-fresh")
    axdump("settings-fresh")
    time.sleep(1)
    record("T4.0b Settings page", "fail" if err else "pass",
           f"Ui clean before={clean}; error bar after pressing Settings={err}", shot=s, exceptions=exceptions_in(app_log()))
    quit_app()


def secure_input_holder():
    """Which process has Secure Event Input on (it silently drops synthetic keystrokes for every app)."""
    _, out = sh("ioreg -l -w 0 | grep -o '\"kCGSSessionSecureInputPID\"=[0-9]*' | head -1")
    m = re.search(r"=(\d+)", out)
    if not m:
        return None
    pid = m.group(1)
    _, name = sh(["ps", "-o", "comm=", "-p", pid])
    return f"{pid} {name.strip()}"


def open_licences(mouse=True):
    """About is open: scroll its column so the Help card shows, then press the Open button on the Licences row
    (the third plain "Open" button; the row's label is static text)."""
    rc, out = find("About", timeout=3)
    m = re.search(r"@(-?\d+),(-?\d+) (\d+)x(\d+)", out)
    if m:
        drive("scroll", 1200, 500, 15)
        time.sleep(0.8)
    return press("Open", role="AXButton", index=2, click=mouse)



@case("M-18 Settings after the Reader")
def m18():
    """M-18 (D-154): an Accessibility press on Settings › Appearance or About › Licences ends WebKit's content process on
    macOS 26. Expected since ac4e1a2: the app reopens the same screen with a plain message, no "An error occurred",
    and chuvadi.log gets the first error (M-19). Mouse-click paths are the control."""
    LOG = f"{HOME}/Library/Logs/Chuvadi/chuvadi.log"
    flows = {
        # name: (open a doc first?, how to get to the section, final press, AX or mouse, marker of the target screen)
        "ax-appearance-home": (False, None, "Appearance", False, "Cream paper"),
        "ax-appearance-reader": (True, None, "Appearance", False, "Cream paper"),
        "ax-licences-home": (False, "About", "Licences", False, ".NET runtime"),
        "mouse-appearance-home": (False, None, "Appearance", True, "Cream paper"),
        "mouse-licences-home": (False, "About", "Licences", True, ".NET runtime"),
    }
    ev, bad = {}, []
    for fname, (with_doc, section, target, mouse, marker) in flows.items():
        reset_state({"theme": "light"})
        launch(settle=4)
        if with_doc:
            open_doc(f"{FX}/five-pages.pdf")
        press("Settings")
        time.sleep(2)
        if section:
            press(section, contains=True, index=-1, click=True)
            time.sleep(1.5)
        before_log = open(LOG, errors="replace").read() if os.path.exists(LOG) else ""
        _, before_diag = sh(f"ls {DIAG} 2>/dev/null")
        if target == "Licences":
            rc, out = open_licences(mouse)
        else:
            rc, out = press(target, contains=True, index=-1, click=mouse)
        e = {"press": out[:120]}
        # the message may be short-lived: look early, then again once things settle
        time.sleep(1.5)
        t1 = axdump(f"m18-{fname}-early")
        e["early_shot"] = shot(f"m18-{fname}-early")
        e["early_error_bar"] = ui_error()
        time.sleep(5)
        t2 = axdump(f"m18-{fname}-late")
        e["late_shot"] = shot(f"m18-{fname}-late")
        e["late_error_bar"] = ui_error()
        e["on_target_screen"] = marker in t2
        e["doc_tab_kept"] = ("five-pages.pdf" in t2) if with_doc else None
        msg_re = r"reopen|reload|restart|sorry|went wrong|problem|stopped|again|recover"
        e["messages"] = sorted({l.strip()[:200] for l in (t1 + "\n" + t2).splitlines() if re.search(msg_re, l, re.I)})[:6]
        after_log = open(LOG, errors="replace").read() if os.path.exists(LOG) else ""
        e["new_log"] = [l[:400] for l in after_log[len(before_log):].splitlines() if l.strip()][:6]
        _, after_diag = sh(f"ls {DIAG} 2>/dev/null")
        new_reports = sorted(set(after_diag.split()) - set(before_diag.split()))
        e["new_crash_reports"] = [x for x in new_reports if re.search(r"WebContent|Chuvadi", x, re.I)]
        for x in e["new_crash_reports"][:2]:
            sh(["cp", f"{DIAG}/{x}", f"{OUT}/logs/"])
        e["alive"] = bool(pids())
        crashed = bool(e["new_crash_reports"])
        if mouse:
            e["verdict"] = "ok" if (not e["late_error_bar"] and e["on_target_screen"] and not crashed) else "FAIL"
        elif crashed:
            # the content process ended: the app must come back on the same screen, explain, and log the first error
            ok = (e["alive"] and not e["late_error_bar"] and e["on_target_screen"] and bool(e["messages"]) and bool(e["new_log"])
                  and (e["doc_tab_kept"] is not False))
            e["verdict"] = "recovered" if ok else "FAIL"
        else:
            e["verdict"] = "ok (no content-process end)" if (not e["late_error_bar"] and e["on_target_screen"]) else "FAIL"
        ev[fname] = e
        if e["verdict"] == "FAIL":
            bad.append(fname)
        quit_app()
    record("M-18 Settings after the Reader", "fail" if bad else "pass",
           f"failed: {bad}" if bad else "; ".join(f"{k}: {v['verdict']}" for k, v in ev.items()), **ev)


@case("T4.0c single keys on Home and Reader")
def t4_0c():
    bad = {}
    keys = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["-", "=", "/", ".", ",", "[", "]", "space", "escape", "return", "tab"]
    reset_state({"theme": "light"})
    launch(settle=4)
    for k in keys:
        drive("key", k)
        time.sleep(0.4)
        if ui_error():
            bad[k] = exceptions_in(app_log())[-1:] if exceptions_in(app_log()) else []
            shot("key-error-" + k)
            quit_app()
            launch(settle=4)
    quit_app()
    record("T4.0c single keys on Home", "fail" if bad else "pass", f"keys that break the Ui: {list(bad)}" if bad else "no key breaks the Ui", details=bad)


# ───────────────────────────── T1.6 / T2 ─────────────────────────────

@case("T1.6 Launch Services")
def t1_6():
    sh(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister", "-f", APP])
    rows = {}
    ok = True
    for f in ["five-pages.pdf", "sample.docx", "sample.xlsx", "notes.md", "notes.txt", "page.html"]:
        _, out = drive("lsquery", f"{FX}/{f}")
        can = APP in out
        lines = out.splitlines()
        default = lines[0] if lines else ""
        others = [l for l in lines[1:] if APP not in l]
        rows[f] = {"candidate": can, "default": default, "other_handlers": len(others)}
        # Chuvadi may be the default only when no other app on the machine can open the type.
        if f in ("five-pages.pdf", "sample.docx", "sample.xlsx") and (not can or (APP in default and others)):
            ok = False
    record("T1.6 Launch Services", "pass" if ok else "fail",
           "candidate for pdf/docx/xlsx; default only where it is the sole handler" if ok else "see rows", rows=rows)


def timing_runs(label, runs, cold, file=None):
    res = []
    for i in range(1, runs + 1):
        quit_app()
        time.sleep(1.0)
        if cold:
            sh("sudo purge", timeout=120)
            time.sleep(1.0)
        rc, out = drive("firstframe", APP, *([file] if file else []), f"{OUT}/timing", "--label", f"{label}-{i}", "--timeout", 30, timeout=70)
        try:
            j = json.load(open(f"{OUT}/timing/{label}-{i}.json"))
        except Exception:
            j = {"marks": {}, "error": out[-400:]}
        time.sleep(0.5)
        j["app"] = last_startup_block()
        res.append(j)
        if i > 2:
            for suffix in ("first-paint", "first-render", "settled", "first-page"):
                p = f"{OUT}/timing/{label}-{i}-{suffix}.png"
                if os.path.exists(p):
                    os.remove(p)
    quit_app()
    return res


@case("T2 startup")
def t2(runs):
    reset_state({"theme": "light"})
    first = timing_runs("first-launch", 1, cold=True)
    summary = {"first_launch": first[0]}
    sets = {"cold": timing_runs("cold", runs, cold=True), "warm": timing_runs("warm", runs, cold=False),
            "pdf-cold": timing_runs("pdf-cold", runs, cold=True, file=f"{FX}/five-pages.pdf"),
            "pdf-warm": timing_runs("pdf-warm", runs, cold=False, file=f"{FX}/five-pages.pdf")}
    for k, rs in sets.items():
        summary[k] = {
            "probe_window": stats([r["marks"].get("window") for r in rs]),
            "probe_first_render": stats([r["marks"].get("first_render") for r in rs]),
            "probe_first_page": stats([r["marks"].get("first_page") for r in rs]),
            "probe_process_start": stats([r["marks"].get("process_start") for r in rs]),
            "app_first_render": stats([r["app"].get("first-render") for r in rs]),
            "app_webview_ready": stats([r["app"].get("webview-ready") for r in rs]),
            "app_maui_built": stats([r["app"].get("maui-built") for r in rs]),
            "app_main": stats([r["app"].get("main") for r in rs]),
            "missing": sum(1 for r in rs if r["marks"].get("first_page" if k.startswith("pdf") else "first_render") is None),
        }
    # T2.3 launch with a file (Finder double-click): does the page appear at all?
    reset_state({"theme": "light"})
    lw = timing_runs("launch-with-pdf", 2, cold=False, file=f"{FX}/five-pages.pdf")
    summary["launch_with_pdf"] = [r["marks"] for r in lw]
    # T2.3 time to first page through the Open panel (from the panel's Open to the page on screen), warm app
    pages = []
    for i in range(1, runs + 1):
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, ms = open_doc(f"{FX}/five-pages.pdf", settle=0.5, label=f"open-page-{i}")
        pages.append(ms)
        quit_app()
    summary["open_panel_first_page"] = stats(pages)
    with open(f"{OUT}/timing/summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    missing = sum(v["missing"] for k, v in summary.items() if k in ("cold", "warm", "pdf-cold", "pdf-warm"))
    lwp = sum(1 for m in summary["launch_with_pdf"] if m.get("first_page"))
    record("T2 startup", "info" if missing == 0 else "fail",
           f"{missing} launches without a first frame; launch-with-PDF showed the page in {lwp}/2; "
           f"Open-panel first page in {summary['open_panel_first_page']['n'] if summary['open_panel_first_page'] else 0}/{runs}",
           summary={k: v for k, v in summary.items() if k != "first_launch"},
           first_launch=summary["first_launch"].get("marks"))


# ───────────────────────────── crash on quit (M-03) ─────────────────────────────

@case("T5.10 quit")
def t5_10():
    reset_state({"theme": "light"})
    ev = {}
    for how in ["cmd+q", "terminate"]:
        before = crash_reports()
        log_path = f"{OUT}/logs-quit-{how.replace('+', '')}.txt"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        p = subprocess.Popen(["open", "-W", "--stdout", log_path, "--stderr", log_path, APP])
        window_up()
        time.sleep(4)
        if how == "cmd+q":
            drive("activate", NAME)
            time.sleep(0.5)
            drive("key", "cmd+q")
        else:
            drive("quit", NAME)
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            pass
        time.sleep(4)
        new = sorted(set(crash_reports()) - set(before))
        ev[how] = {"new_crash_reports": new, "screen": screen(f"after-quit-{how.replace('+', '')}")}
        try:
            ev[how]["stdout_tail"] = open(log_path, errors="replace").read()[-12000:]
        except Exception:
            pass
        for n in new:
            shutil.copy(f"{DIAG}/{n}", f"{OUT}/logs-{n}")
        quit_app(force=True)
        sh(["osascript", "-e", 'tell application "System Events" to keystroke return'], timeout=10)  # dismiss "quit unexpectedly"
    crashed = [k for k, v in ev.items() if v["new_crash_reports"] or "Terminating app due to uncaught exception" in v.get("stdout_tail", "")
               or "Got a SIGABRT" in v.get("stdout_tail", "")]
    for k, v in ev.items():
        m = re.search(r"Terminating app due to uncaught exception '([^']+)'", v.get("stdout_tail", ""))
        if m:
            v["exception"] = m.group(1)
    record("T5.10 quit", "fail" if crashed else "pass", f"crash report written on quit via: {crashed}" if crashed else "clean quit both ways", **ev)


# ───────────────────────────── T3 look + menus ─────────────────────────────

@case("T3.7 menu bar")
def t3_7():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/five-pages.pdf")
    menus = menu_dump("reader-pdf", live=True)
    tops = [m["title"] for m in menus]
    counts = {m["title"]: len([i for i in m.get("items", []) if i.get("title")]) for m in menus}
    expected = ["Chuvadi", "File", "Edit", "View", "Document", "Window", "Help"]
    bad = []
    if [t for t in tops if t != "Apple"] != expected:
        bad.append(f"menus {tops} ≠ {expected}")
    for m in ("File", "Document", "View"):
        if counts.get(m, 0) < 3:
            bad.append(f"{m} menu has {counts.get(m, 0)} items")
    if menu_by_title(menus, "Enter Full Screen"):
        bad.append("system 'Enter Full Screen' still in the menu (decision: Immersive ⌃⌘F replaces it)")
    if not find_menu_item(menus, lambda it: it.get("shortcut", "").endswith("⌘,")):
        bad.append("no Settings… ⌘, item")
    record("T3.7 menu bar", "pass" if not bad else "fail", "; ".join(bad) or "menus as designed", doc_opened=ok,
           menus=tops, item_counts=counts)
    # waiting longer and switching modes must not change the result if the rebuild were only late
    run_cmd("Mark mode")
    time.sleep(5)
    menus2 = menu_dump("reader-pdf-after-mark", live=True)
    counts2 = {m["title"]: len([i for i in m.get("items", []) if i.get("title")]) for m in menus2}
    record("T3.7d menu bar after mode switch + 5 s", "pass" if counts2.get("File", 0) >= 3 else "fail", f"item counts {counts2}")
    quit_app()


SECTIONS = ["Appearance", "Reading", "Saving", "Library", "Language", "Accessibility", "Shortcuts", "Kiosk", "Account", "About"]


@case("T3.1 screens light")
def t3_1():
    reset_state({"theme": "light"})
    launch(settle=4)
    ev = {"home": shot("light-home-first-run")}
    axdump("home-first-run")
    ok, _ = open_doc(f"{FX}/five-pages.pdf")
    ev["opened"] = ok
    ev["reader-read"] = shot("light-reader-read")
    reader = axdump("reader-read")
    texts = reader
    for mode in ["Mark", "Arrange", "Protect", "Read"]:
        press(f"{mode} ", contains=True)  # left bar "Mark 2" etc.
        time.sleep(2.5)
        ev[mode] = shot("light-reader-" + mode.lower())
        texts += axdump("reader-" + mode.lower())
    # Document ▾ menu and the View rail hover
    rc, o = press("Document")
    time.sleep(1.2)
    ev["document-menu"] = shot("light-reader-document-menu") + f" ({o[:60]})"
    texts += axdump("reader-document-menu")
    drive("key", "escape")
    drive("key", "cmd+k")
    time.sleep(1)
    ev["command-bar"] = shot("light-command-bar")
    texts += axdump("command-bar")
    drive("key", "escape")
    for target in ["Library", "Settings", "Home"]:
        press(target)
        time.sleep(2.5)
        ev[target] = shot("light-" + target.lower())
        if target == "Settings":
            texts += axdump("settings")
            for sec in SECTIONS:
                rc2, o2 = press(sec, contains=True, index=-1, click=True)
                time.sleep(1.2)
                ev["settings-" + sec] = shot("light-settings-" + sec.lower()) + f" ({o2[:70]})"
                t = axdump("settings-" + sec.lower())
                texts += t
                if sec == "About":
                    rc3, o3 = open_licences(True)
                    time.sleep(1.5)
                    ev["licences"] = shot("light-licences") + f" ({o3[:70]})"
                    lic = axdump("licences")
                    rc4, o4 = press(".NET runtime", contains=True, click=True)
                    time.sleep(1.5)
                    ev["licences-dotnet"] = shot("light-licences-dotnet") + f" ({o4[:70]})"
                    dot = axdump("licences-dotnet")
                    tabs = [x for x in ["Licence agreement", "Privacy", "notices", ".NET runtime"] if x.lower() in lic.lower()]
                    record("T1.10 Licences tabs", "pass" if ".NET runtime" in tabs and "Mono" in dot else "fail",
                           f"tabs found: {tabs}; Mono notices shown: {'Mono' in dot}")
    bad = sorted(set(l.strip()[:170] for l in texts.splitlines() if re.search(r"\bCtrl\b|\bF11\b|⌘Tab|⌘ Tab", l)))
    record("T3.7c no Ctrl / F11 / ⌘Tab labels in the Ui", "pass" if not bad else "fail",
           f"{len(bad)} AX texts" if bad else "none", lines=bad[:60])
    record("T3.1 screens light", "info", "screenshots", shots=ev)
    quit_app()


@case("T3.2 themes")
def t3_2():
    ev = {}
    for th in THEMES:
        reset_state({"theme": th})
        launch(settle=4)
        ev[th + "-home"] = shot(f"{th}-home")
        open_doc(f"{FX}/five-pages.pdf")
        ev[th + "-reader"] = shot(f"{th}-reader")
        press("Settings")
        time.sleep(2)
        press("Appearance", contains=True, index=-1, click=True)
        time.sleep(1.2)
        ev[th + "-settings"] = shot(f"{th}-settings")
        ev[th + "-kept"] = (read_settings() or {}).get("theme")
        quit_app()
    record("T3.2 themes", "info", "5 themes × home/reader/settings", shots=ev)


@case("T3.3 interface size")
def t3_3():
    ev = {}
    for pct in ["125", "150"]:
        reset_state({"theme": "light", "ui-scale": pct})
        launch(settle=4)
        open_doc(f"{FX}/five-pages.pdf")
        ev[pct] = shot(f"light-reader-scale{pct}")
        quit_app()
    record("T3.3 interface size", "info", "125 % and 150 %", shots=ev)


def top_crop(name, h=90):
    """Bytes of the top strip of a window capture (tabs live there; the clock does not)."""
    from struct import unpack
    p = f"{OUT}/shots/{name}.png"
    drive("capture", NAME, p)
    try:
        import zlib
        return open(p, "rb").read()  # fallback: whole file
    except Exception:
        return b""


@case("T4.0 keyboard reaches the app at launch")
def t4_0():
    reset_state({"theme": "light"})
    launch(settle=4)
    n0 = len(axdump("kbd-before").splitlines())
    drive("key", "cmd+k")
    time.sleep(1.5)
    t1 = axdump("kbd-after-cmdk")
    opened_without_click = len(t1.splitlines()) != n0 or "Find or do anything" in t1 and "AXTextField" in t1
    s1 = shot("kbd-after-cmdk-no-click")
    drive("key", "escape")
    time.sleep(0.5)
    w = window_up(5)
    m = re.search(r"\t(\d+),(\d+) (\d+)x(\d+)", w or "")
    if m:
        x, y, wd, ht = map(int, m.groups())
        drive("click", x + wd // 2, y + ht - 60)  # an empty spot low in the page
        time.sleep(0.8)
    drive("key", "cmd+k")
    time.sleep(1.5)
    t2 = axdump("kbd-after-click-cmdk")
    opened_after_click = len(t2.splitlines()) != n0
    s2 = shot("kbd-after-click-cmdk")
    drive("key", "escape")
    drive("key", "cmd+o")
    time.sleep(2.5)
    sc = screen("kbd-after-cmdo")
    _, wins = drive("windows")
    # the Open panel is its own window ("Open a document", layer 8) — counting only layer-0 windows was my bug until 10 Nov
    panel = any(l.startswith(NAME + "\t") and "Open a document" in l for l in wins.splitlines())
    ev_focus = {"last_click": "an empty spot low in the page, then ⌘K and Esc, then ⌘O"}
    drive("key", "escape")
    record("T4.0 keyboard reaches the app at launch", "pass" if opened_without_click and panel else "fail",
           f"⌘K before any click opens the bar={opened_without_click}; after a click={opened_after_click}; ⌘O opens a panel={panel}",
           shots=[s1, s2, sc], windows=wins, **ev_focus)
    quit_app()


@case("T3.5 window + immersive + keys")
def t3_5():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/five-pages.pdf")
    ok2, _ = open_doc(f"{FX}/second.pdf")
    ev = {"docs_opened": [ok, ok2]}
    _, ev["before"] = drive("winstate", NAME)
    # Immersive is an in-app mode on every platform (chrome hidden, "exit" button); ⌃⌘F is its Mac key.
    drive("key", "ctrl+cmd+f")
    time.sleep(2.5)
    ev["immersive-shot"] = shot("light-reader-immersive")
    ev["immersive_on_ctrl_cmd_f"] = find("exit", timeout=2)[0] == 0
    if not ev["immersive_on_ctrl_cmd_f"]:
        # seen once on 15-Intel (a7be951): Immersive on, page left as its "page 1" placeholder, no exit button, keys dead.
        # Keep what the process is doing (main-thread stack) and look again later to tell slow from stuck.
        os.makedirs(f"{OUT}/logs", exist_ok=True)
        pid = (pids() or [""])[0]
        sh(f"sample {pid} 3 -file {OUT}/logs/t3_5-stuck-sample.txt", timeout=60)
        _, cpu = sh(f"ps -o %cpu=,rss=,state= -p {pid}")
        ev["stuck_ps"] = cpu.strip()
        time.sleep(15)
        ev["stuck_shot_after_20s"] = shot("t3_5-stuck-after-20s")
        ev["stuck_exit_after_20s"] = find("exit", timeout=2)[0] == 0
        ev["stuck_ax_lines"] = len(axdump("t3_5-stuck").splitlines())
    drive("key", "escape")
    time.sleep(1.5)
    ev["escape_leaves"] = find("exit", timeout=1)[0] != 0
    if not ev["escape_leaves"]:
        press("exit")
        time.sleep(1.5)
    drive("key", "f11")
    time.sleep(2)
    ev["f11_enters"] = find("exit", timeout=1)[0] == 0
    if ev["f11_enters"]:
        press("exit")
        time.sleep(1.5)
    _, ev["window_after"] = drive("winstate", NAME)
    drive("activate", NAME)
    # Next tab: the Ui says ⌘Tab (macOS app switcher); try ⌃Tab, the Mac convention
    t_a = axdump("tabs-before")
    shot("tabs-before")
    drive("key", "ctrl+tab")
    time.sleep(1.5)
    t_b = axdump("tabs-after-ctrl-tab")
    shot("tabs-after-ctrl-tab")
    # the page counter / title in the top bar differs between five-pages.pdf (active last opened = second.pdf) and the other
    strip = lambda t: "\n".join(l for l in t.splitlines() if not re.search(r"\d{2}:\d{2}:\d{2}", l))
    ev["ctrl_tab_changed_screen"] = strip(t_a) != strip(t_b)
    # traffic lights
    press("Zoom")
    time.sleep(1.5)
    _, ev["zoomed"] = drive("winstate", NAME)
    rc, ev["green_label_when_zoomed"] = press("Exit full screen")
    time.sleep(1.5)
    press("Minimize")
    time.sleep(1.5)
    _, st = drive("winstate", NAME)
    ev["minimized"] = "minimized=true" in st
    drive("setwin", NAME, "minimized", "false")
    time.sleep(1)
    ev["dock"] = screen("screen-with-dock")
    record("T3.5 window + immersive + keys", "pass" if ev["immersive_on_ctrl_cmd_f"] and ev["escape_leaves"] and ev["minimized"] else "fail",
           f"⌃⌘F → Immersive={ev['immersive_on_ctrl_cmd_f']}; Esc leaves={ev['escape_leaves']}; F11 enters={ev['f11_enters']}; "
           f"minimise={ev['minimized']} (tab keys: see the M-08 case)", **ev)
    quit_app()


# ───────────────────────────── T4 function ─────────────────────────────

@case("T4.14 single instance")
def t4_14():
    reset_state({"theme": "light"})
    launch(settle=4)
    open_doc(f"{FX}/five-pages.pdf")
    p0 = pids()
    sh(["open", "-a", APP, f"{FX}/second.pdf", f"{FX}/third.pdf"])
    time.sleep(5)
    p1 = pids()
    txt = axdump("single-instance")
    tabs = [n for n in ["five-pages.pdf", "second.pdf", "third.pdf"] if n in txt]
    ok = len(p1) == 1 and p0 == p1 and len(tabs) == 3
    record("T4.14 single instance", "pass" if ok else "fail", f"processes {len(p1)}, tabs {tabs}",
           shot=shot("single-instance-3-tabs"))
    quit_app()


@case("T4.12 clipboard + T4.13 reveal")
def t4_12():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/five-pages.pdf")
    sh("pbcopy < /dev/null")
    rc, o = menu("File", "Copy file path")
    time.sleep(1.5)
    _, pb = sh("pbpaste")
    good = pb.strip() in (f"{FX}/five-pages.pdf", os.path.realpath(f"{FX}/five-pages.pdf"))
    record("T4.12 copy file path (text clipboard)", "pass" if good else "fail", f"doc opened={ok}; pasteboard: {pb[:200]!r}")
    # image: Snapshot a region → copies PNG?
    menu("View", "Snapshot a region")
    time.sleep(1)
    w = window_up(5)
    m = re.search(r"\t(\d+),(\d+) (\d+)x(\d+)", w or "")
    if m:
        x, y, wd, ht = map(int, m.groups())
        cx, cy = x + wd // 2, y + ht // 2
        drive("drag", cx - 120, cy - 120, cx + 120, cy + 40)
        time.sleep(1.5)
        shot("snapshot-panel")
        press("Copy", contains=True, role="AXButton")
        time.sleep(1.5)
    _, types = drive("pasteboard", f"{OUT}/pasteboard")
    record("T4.12b snapshot → image clipboard", "info", types, shot=shot("after-snapshot"))
    menu("File", "Show in folder")
    time.sleep(4)
    _, sel = sh(["osascript", "-e", 'tell application "Finder" to get POSIX path of (item 1 of (get selection) as alias)'], timeout=20)
    drive("axdump", "Finder", f"{OUT}/ax/finder-after-reveal.txt", timeout=60)
    ok2 = sel.strip().endswith("five-pages.pdf")
    record("T4.13 Show in Finder", "pass" if ok2 else "fail", f"Finder selection: {sel[:200]!r}", screen=screen("finder-after-reveal"))
    sh(["osascript", "-e", 'tell application "Finder" to close every window'], timeout=15)
    quit_app()


def spool_files():
    _, out = sh("sudo ls /var/spool/cups")
    return set(x for x in out.split() if x.startswith("d"))


def cups_jobs():
    _, out = sh("lpstat -o ChvdTest; lpstat -W completed -o ChvdTest")
    return out


def check_printed(f, ev, phrase):
    _, kind = sh(["file", "-b", f])
    ev["kind"] = kind
    if "PDF" not in kind:
        return False
    _, fonts = sh(["pdffonts", f])
    _, imgs = sh(["pdfimages", "-list", f])
    _, text = sh(["pdftotext", f, "-"])
    _, info = sh(["pdfinfo", f])
    _, js = sh(f"qpdf --json '{f}'", timeout=60)
    img_lines = [l for l in imgs.splitlines()[2:] if l.strip()]
    ev.update(fonts=fonts, images=imgs, text=text[:500], info=info, live_annots=js.count('"/Annots"'), forms=js.count('"/AcroForm"'))
    return phrase in text and not img_lines and len(fonts.splitlines()) > 2


@case("T4.7 print vector")
def t4_7():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/annotated.pdf")
    before = spool_files()
    ev = {"opened": ok}
    drive("key", "cmd+p")
    time.sleep(2)
    ev["card"] = shot("print-card")
    axdump("print-card")
    rc, ev["card-press"] = press("Print 2 pages", contains=True)
    time.sleep(4)
    ev["panel"] = screen("print-panel")
    axdump("print-panel")
    # Print to the paused test queue (ChvdTest): the job macOS submits stays in the CUPS spool as the PDF the
    # print system generated — the same document "Save as PDF" writes. The panel's Save sheet could not be driven
    # reliably from outside (local-network alert, M-22), so this is the check.
    _, ev["panel_printer"] = sh("defaults read org.cups.PrintingPrefs UseLastPrinter 2>&1; lpstat -d 2>&1")
    rc, ev["print-press"] = press("Print", role="AXButton", index=-1)
    time.sleep(3)
    # "Printing of jobs for this printer is stopped…" → Add to Printer keeps the job in the spool
    rc, ev["add-to-printer"] = press("Add to Printer", role="AXButton")
    time.sleep(10)
    ev["after-print"] = screen("print-after-print")
    new = sorted(spool_files() - before)
    ev["spool-new"] = new
    ev["jobs"] = cups_jobs()
    good = False
    if new:
        f = f"{OUT}/printed-annotated.pdf"
        sh(f"sudo cp /var/spool/cups/{new[-1]} '{f}' && sudo chmod 644 '{f}'")
        good = check_printed(f, ev, "marker-1")
        ev["flattened"] = ev.get("live_annots", 1) == 0 and ev.get("forms", 1) == 0
        good = good and ev["flattened"]
    record("T4.7 print vector", "pass" if good else "fail",
           "vector PDF reached CUPS: fonts, no images, text extractable" if good else "see evidence", **ev)
    quit_app()


@case("T4.8 print refused")
def t4_8():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/noprint.pdf")
    jobs0 = spool_files()
    drive("key", "cmd+p")
    time.sleep(2)
    s1 = shot("noprint-card")
    txt = axdump("noprint-card")
    msg = "permissions don" in txt
    press("Print", role="AXButton", index=-1)
    time.sleep(4)
    s2 = screen("noprint-after-press")
    txt2 = axdump("noprint-after-press")
    panel = "AXSheet" in txt2
    jobs1 = spool_files()
    good = ok and msg and not panel and jobs0 == jobs1
    record("T4.8 print refused", "pass" if good else "fail",
           f"opened={ok}, message shown={msg}, native panel opened={panel}, new CUPS job={jobs0 != jobs1}", shots=[s1, s2])
    quit_app()


@case("T4.9 formats")
def t4_9():
    ev = {}
    for f, marker in [("sample.xlsx", "marker-xlsx"), ("sample.docx", "marker-docx"), ("notes.md", "marker-md"),
                      ("notes.txt", "marker-txt"), ("page.html", "marker-html"), ("ஆவணம்-tamil-name.pdf", "Page 1")]:
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, _ = open_doc(f"{FX}/{f}", settle=5)
        nm = re.sub(r"[^a-z0-9.-]", "_", f.lower())
        ev[f] = {"opened": ok, "shot": shot("format-" + nm)}
        txt = axdump("format-" + nm)
        ev[f]["marker_in_ax"] = marker in txt
        if f == "sample.xlsx":
            press("Second sheet", contains=True)
            time.sleep(1.5)
            ev[f]["sheet2"] = "marker-xlsx" in axdump("format-xlsx-sheet2")
            ev[f]["sheet2_shot"] = shot("format-xlsx-sheet2")
            ev[f]["cells"] = [l.strip()[:120] for l in txt.splitlines() if re.search(r"1234|1,234|₹|3\.14|6\.28|Merged|2026", l)][:12]
        quit_app()
    bad = [k for k, v in ev.items() if not (v["opened"] and v["marker_in_ax"])]
    record("T4.9 formats", "pass" if not bad else "fail", f"not shown: {bad}" if bad else "all formats show their text", **ev)


@case("T4.6 passwords")
def t4_6():
    """Session A: right password straight away. Session B (AES-256 only): wrong, then right.
    Before each submit the harness presses "show" so the typed value is readable in the AX tree,
    then re-focuses the field and presses Return, so a failure can't be a lost keystroke."""
    ev = {}
    # In the full suite on macOS 26 keystrokes stopped reaching the field after the print cases; check whether some
    # process (a print or auth sheet) still holds Secure Event Input, and end it — testing only.
    holder = secure_input_holder()
    ev["secure_input_before"] = holder
    if holder and "Chuvadi" not in holder:
        sh(["sudo", "kill", holder.split()[0]])
        time.sleep(1)
        ev["secure_input_after_kill"] = secure_input_holder()

    def submit(tag, f, pw):
        r = {"focused": focus_field("Password to open")}
        press("show")
        time.sleep(0.6)
        focus_field("Password to open")
        for ch in pw:  # real key codes, one key at a time (unicode-string events did not reach the field)
            drive("key", ch)
            time.sleep(0.08)
        time.sleep(0.6)
        t = axdump(f"pw-{tag}-typed-" + f)
        r["typed_values"] = [l.strip()[:160] for l in t.splitlines() if "AXTextField" in l][:3]
        r["typed_ok"] = f'value="{pw}"' in t
        r["open_button"] = [l.strip()[:120] for l in t.splitlines() if 'AXButton desc="Open"' in l][:1]
        focus_field("Password to open")
        drive("key", "return")
        time.sleep(4)
        rt = axdump(f"pw-{tag}-" + f)
        r["messages"] = [l.strip()[:200] for l in rt.splitlines() if re.search(r"wrong|incorrect|doesn|password", l, re.I)][:4]
        r["shows_page"] = "marker-1" in rt or "Page 1 of five" in rt or "of 5" in rt
        r["ui_error"] = ui_error()
        r["shot"] = shot(f"pw-{tag}-" + f.replace(".", "_"))
        return r

    for f in ["aes256.pdf", "aes128.pdf", "rc4.pdf", "owner-only.pdf"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, _ = open_doc(f"{FX}/{f}", settle=4)
        txt = axdump("pw-" + f)
        field = "AXSecureTextField" in txt
        e = {"tab": ok, "prompt": field, "shot": shot("pw-" + f.replace(".", "_"))}
        if f == "owner-only.pdf":
            e["shows_page"] = "marker-1" in txt or "Page 1 of five" in txt
        elif field:
            e["right_first"] = submit("right", f, "user1")
        ev[f] = e
        quit_app()

    reset_state({"theme": "light"})
    launch(settle=3)
    open_doc(f"{FX}/aes256.pdf", settle=4)
    ev["aes256 wrong then right"] = {"wrong": submit("wrong", "aes256.pdf", "wrong"),
                                     "right": submit("right2", "aes256.pdf", "user1")}
    quit_app()

    bad = []
    for k in ("aes256.pdf", "aes128.pdf", "rc4.pdf"):
        r = ev[k].get("right_first") or {}
        if not ev[k].get("prompt") or not r.get("shows_page") or r.get("ui_error"):
            bad.append(k)
    seq = ev["aes256 wrong then right"]
    if seq["wrong"].get("ui_error") or seq["right"].get("ui_error") or not seq["right"].get("shows_page"):
        bad.append("aes256 wrong-then-right")
    if not ev["owner-only.pdf"].get("shows_page"):
        bad.append("owner-only.pdf")
    record("T4.6 passwords", "pass" if not bad else "fail", f"failed: {bad}" if bad else "prompt, wrong and right password", **ev)


# ───────────────────────────── T5 robustness ─────────────────────────────

@case("T5.1 damaged and hostile files")
def t5_1():
    ev = {}
    for f in ["damaged-truncated.pdf", "damaged-badxref.pdf", "damaged-garbage.pdf", "damaged-empty.pdf", "missing-part.docx"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, _ = open_doc(f"{FX}/{f}", settle=4)
        alive = bool(pids())
        e = {"alive": alive, "shot": shot("robust-" + f.replace(".", "_")) if alive else None}
        if alive:
            txt = axdump("robust-" + f)
            e["messages"] = [l.strip()[:220] for l in txt.splitlines() if re.search(r"could not|couldn|damaged|error|offset|startxref|expected", l, re.I)][:6]
        ev[f] = e
        quit_app()
    for f in ["bomb.docx", "far-cell.xlsx"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        open_doc(f"{FX}/{f}", settle=1)
        peak = 0
        for _ in range(20):
            time.sleep(1)
            peak = max(peak, rss_mb() or 0)
        ok2, _ = open_doc(f"{FX}/five-pages.pdf", settle=4)
        ev[f] = {"peak_rss_mb_20s": peak, "alive": bool(pids()), "next_file_opened": ok2,
                 "shot": shot("hostile-" + f.replace(".", "_"))}
        quit_app(force=True)
    crashed = [k for k, v in ev.items() if not v.get("alive")]
    stuck = [k for k in ("bomb.docx", "far-cell.xlsx") if not ev[k]["next_file_opened"]]
    record("T5.1 damaged and hostile files", "fail" if crashed or stuck else "info",
           f"died on {crashed}; later open blocked after {stuck}", **ev)


@case("T5.3 large files")
def t5_3():
    ev = {}
    for f in ["heavy-vector.pdf", "many-pages.pdf"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, ms = open_doc(f"{FX}/{f}", settle=1, label="large-" + f)
        ev[f] = {"opened": ok, "first_page_ms": ms, "rss_mb": rss_mb(), "shot": shot("large-" + f.replace(".", "_"))}
        for _ in range(10):
            drive("key", "pagedown")
        time.sleep(2)
        ev[f]["after_scroll_rss_mb"] = rss_mb()
        ev[f]["after_scroll_shot"] = shot("large-scrolled-" + f.replace(".", "_"))
        quit_app()
    record("T5.3 large files", "info", "stand-ins (the 7.9 MB CAD PDF is not available here)", **ev)


@case("T5.4 many tabs")
def t5_4():
    reset_state({"theme": "light"})
    d = "/tmp/chvd-many"
    os.makedirs(d, exist_ok=True)
    launch(settle=3)
    r0 = rss_mb()
    opened = 0
    for i in range(1, 16):
        p = f"{d}/doc-{i:02d}.pdf"
        shutil.copy(f"{FX}/five-pages.pdf", p)
        ok, _ = open_doc(p, settle=1.5)
        opened += ok
    r1 = rss_mb()
    s = shot("many-tabs")
    quit_app()
    launch(settle=6)
    txt2 = axdump("many-tabs-restored")
    restored = sum(1 for i in range(1, 16) if f"doc-{i:02d}.pdf" in txt2)
    record("T5.4 many tabs", "pass" if opened == 15 else "fail",
           f"opened {opened}/15 through the panel, RSS {r0} → {r1} MB, restored after relaunch {restored}/15",
           shots=[s, shot("many-tabs-restored")])
    quit_app()


@case("T5.7 network use")
def t5_7():
    reset_state({"theme": "light"})
    launch(settle=3)
    open_doc(f"{FX}/page.html")
    open_doc(f"{FX}/links.pdf")
    conns = []
    for _ in range(8):
        p = pids()
        if p:
            _, out = sh(["lsof", "-nP", "-a", "-i", "-p", ",".join(map(str, p))])
            conns += [l for l in out.splitlines()[1:] if l.strip()]
        _, wk = sh("lsof -nP -i | grep -i -E 'WebContent|WebKit.Networking|com.apple.WebKit' || true")
        conns += [l for l in wk.splitlines() if l.strip()]
        time.sleep(1)
    uniq = sorted(set(conns))
    record("T5.7 network use", "pass" if not uniq else "fail",
           "no sockets from the app or its WebKit processes (incl. an HTML page with a remote image)" if not uniq else f"{len(uniq)} socket lines",
           lines=uniq[:40], shot=shot("html-remote-image"))
    quit_app()


@case("T5.8 locale")
def t5_8():
    ev = {}
    for loc in ["en_IN", "de_DE", "ta_IN"]:
        sh(["defaults", "write", "-g", "AppleLocale", loc])
        reset_state({"theme": "light"})
        launch(settle=3)
        open_doc(f"{FX}/sample.xlsx", settle=4)
        ev[loc] = {"shot": shot("locale-" + loc)}
        txt = axdump("locale-" + loc)
        ev[loc]["texts"] = [l.strip()[:160] for l in txt.splitlines() if re.search(r"\d{1,2}:\d{2}:\d{2}|1234|1,234|1\.234|3,14|3\.14|2026|₹", l)][:10]
        quit_app()
    sh(["defaults", "delete", "-g", "AppleLocale"])
    record("T5.8 locale", "info", "en_IN, de_DE, ta_IN — see texts", **ev)


@case("T5.9 fresh, upgrade, corrupt, read-only")
def t5_9():
    ev = {}
    reset_state({"theme": "dark", "ui-scale": "125"})
    launch(settle=5)
    ev["upgrade"] = {"shot": shot("upgrade-dark-125"), "settings_after": read_settings()}
    quit_app()
    reset_state()
    os.makedirs(STATE, exist_ok=True)
    open(f"{STATE}/settings.json", "w").write("{ not json")
    launch(settle=5)
    ev["corrupt"] = {"alive": bool(pids()), "shot": shot("corrupt-settings")}
    quit_app()
    ev["corrupt"]["file_after"] = open(f"{STATE}/settings.json").read()[:200]
    reset_state({"theme": "light"})
    os.chmod(STATE, 0o500)
    sh(["open", "-a", APP])
    w = window_up(20)
    time.sleep(4)
    ok = open_doc(f"{FX}/five-pages.pdf")[0] if pids() else False
    ev["readonly"] = {"window": bool(w), "alive": bool(pids()), "opened": ok, "shot": shot("readonly-state") if pids() else None}
    quit_app()
    os.chmod(STATE, 0o700)
    reset_state()
    launch(settle=5)
    txt = axdump("fresh-home")
    ev["fresh"] = {"shot": shot("fresh-home"),
                   "sample_data_present": [n for n in ["patient_chart.pdf", "aerb_submission.pdf", "consent_form.pdf", "IMCHRC"] if n in txt]}
    quit_app()
    record("T5.9 fresh, upgrade, corrupt, read-only", "pass" if ev["corrupt"]["alive"] and ev["readonly"]["alive"] else "fail",
           f"corrupt alive={ev['corrupt']['alive']}, read-only alive={ev['readonly']['alive']}, "
           f"sample data on a fresh install={ev['fresh']['sample_data_present']} (D-94 H-12)", **ev)


@case("T4.15 folders")
def t4_15():
    reset_state({"theme": "light"})
    marker = "/tmp/chvd-t415-marker"
    open(marker, "w").write("x")
    time.sleep(1)
    launch(settle=3)
    open_doc(f"{FX}/five-pages.pdf")
    quit_app()
    _, newer = sh(f"find {HOME}/Library {HOME}/Documents {HOME}/.config /tmp -newer {marker} -type f 2>/dev/null | grep -i -E 'chuvadi|sthraas' | head -80", timeout=180)
    in_config = os.path.exists(f"{HOME}/.config/Chuvadi")
    record("T4.15 folders", "pass" if not in_config else "fail", f"~/.config/Chuvadi exists={in_config}", files=newer.splitlines())


@case("T5.5 low memory")
def t5_5():
    reset_state({"theme": "light"})
    launch(settle=3)
    open_doc(f"{FX}/many-pages.pdf")
    p = subprocess.Popen(["sudo", "memory_pressure", "-S", "-l", "critical"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(12)
    ok, _ = open_doc(f"{FX}/heavy-vector.pdf")
    alive = bool(pids())
    s = shot("low-memory") if alive else None
    p.terminate()
    sh("sudo pkill memory_pressure")
    record("T5.5 low memory", "pass" if alive and ok else "fail", f"alive={alive}, opened under pressure={ok}", shot=s, rss=rss_mb())
    quit_app()


def ax_paths(text, pattern):
    """Lines of an AX dump that match `pattern`, each with its role and the path of its ancestors (from indentation)."""
    out, stack = [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip(" "))
        stack = [(i, l) for i, l in stack if i < ind]
        if re.search(pattern, line):
            path = " › ".join(re.sub(r"\s*@.*$", "", l.strip())[:60] for _, l in stack[-5:])
            out.append({"element": re.sub(r"\s*@.*$", "", line.strip())[:160], "role": line.strip().split(" ")[0], "path": path})
        stack.append((ind, line))
    return out


@case("M-08/M-09/M-10 shared patch")
def m_shared():
    reset_state({"theme": "light"})
    launch(settle=4)
    open_doc(f"{FX}/five-pages.pdf")
    open_doc(f"{FX}/many-pages.pdf")  # different page count, so the status bar says which tab is active
    ev = {}
    t = axdump("shared-reader")
    status = lambda tx: [l.strip()[:120] for l in tx.splitlines() if re.search(r"page \d+ of \d+", l)][:2]
    ev["status_before"] = status(t)
    ev["shot_before"] = shot("tabkeys-0-before")
    drive("activate", NAME)
    time.sleep(0.6)

    def which(tag):
        st = status(axdump("tabkeys-" + tag))
        shot("tabkeys-" + tag)
        j = " ".join(st)
        return "many" if "of 500" in j else ("five" if "of 5" in j else "?" + j[:60])

    # Two tabs: 1 = five-pages, 2 = many-pages (active). Each key must land exactly where a person expects, in two
    # states: A as the app stands after opening files (no first responder), B after a click on the page (page focused).
    seq = [("ctrl+tab", "five"), ("ctrl+shift+tab", "many"), ("cmd+1", "five"), ("cmd+2", "many")]
    ev["tabkeys"] = {}
    for state in ("A-as-opened", "B-page-clicked"):
        if state.startswith("B"):
            w = window_up(3)
            m = re.search(r"\t(\d+),(\d+) (\d+)x(\d+)", w or "")
            if m:
                x, y, wd, ht = map(int, m.groups())
                drive("click", x + wd // 2, y + ht // 2)
                time.sleep(0.8)
        r = {"focused": drive("focused", NAME)[1][:120], "start": which(state + "-start")}
        for key, want in seq:
            drive("key", key)
            time.sleep(2)
            got = which(f"{state}-{key.replace('+', '-')}")
            r[key] = {"want": want, "got": got, "ok": got == want}
        ev["tabkeys"][state] = r
    ev["tabkeys_failed"] = [f"{st}: {k} → {v['got']} (want {v['want']})" for st, r in ev["tabkeys"].items()
                            for k, v in r.items() if isinstance(v, dict) and not v["ok"]]
    ev["m08_ctrl_tab_switches"] = not ev["tabkeys_failed"]
    # M-09: every Immersive / F11 mention in the Reader (View rail included)
    ev["m09_reader_immersive"] = ax_paths(t, r"Immersive|F11")
    # hover the View rail's Immersive button so a tooltip, if any, is in the tree too
    rc, o = find("Immersive", contains=True, timeout=2)
    m = re.search(r"@(-?\d+),(-?\d+) (\d+)x(\d+)", o)
    if m:
        x, y, w, h = map(int, m.groups())
        drive("move", x + w // 2, y + h // 2)
        time.sleep(1.5)
        ev["m09_hover"] = ax_paths(axdump("shared-immersive-hover"), r"Immersive|F11|⌃⌘F")
        ev["m09_hover_shot"] = shot("shared-immersive-hover")
    # M-10: traffic-light labels, before and after Zoom
    lights = lambda tx: [l.strip()[:90] for l in tx.splitlines() if re.search(r'desc="(Close|Minimize|Zoom|Exit full screen|Enter full screen|Full screen)"', l)][:4]
    ev["m10_lights_before"] = lights(t)
    press("Zoom")
    time.sleep(1.5)
    ev["m10_lights_zoomed"] = lights(axdump("shared-zoomed"))
    press("Zoom")
    time.sleep(1)
    # M-08 / M-09 in Settings › Shortcuts
    press("Settings")
    time.sleep(2)
    press("Shortcuts", role="AXButton", click=True)
    time.sleep(2.5)
    sc = axdump("shared-shortcuts")
    ev["on_shortcuts_screen"] = "Next / previous tab" in sc
    ev["shortcuts_shot"] = shot("shared-shortcuts")
    ev["shortcuts_lines"] = ax_paths(sc, r"Immersive|tab|Tab|F11|Ctrl|⌃")[:30]
    ev["shortcuts_bad"] = [x for x in ev["shortcuts_lines"] if re.search(r"F11|⌘Tab|⌘ Tab|\bCtrl\b", x["element"])]
    ev["m09_bad"] = [x for x in ev["m09_reader_immersive"] + ev.get("m09_hover", []) if "F11" in x["element"]]
    ev["m10_ok"] = any('"Zoom"' in l for l in ev["m10_lights_zoomed"]) and not any("full screen" in l for l in ev["m10_lights_zoomed"])
    ok = ev["m08_ctrl_tab_switches"] and ev["on_shortcuts_screen"] and not ev["shortcuts_bad"] and not ev["m09_bad"] and ev["m10_ok"]
    record("M-08/M-09/M-10 shared patch", "pass" if ok else "fail",
           f"tab keys (⌃Tab, ⌃⇧Tab, ⌘1, ⌘2 in two focus states) all right={ev['m08_ctrl_tab_switches']} {ev['tabkeys_failed']}; Shortcuts screen={ev['on_shortcuts_screen']}; F11 left={len(ev['m09_bad'])}; bad shortcut labels={len(ev['shortcuts_bad'])}; green light when zoomed={ev['m10_lights_zoomed']}", **ev)
    quit_app()


@case("T4.0d ⌘O in several states")
def t4_0d():
    """T4.0 failed twice on 15-Intel in the full suite (Esc then ⌘O with no pause, Library behind). Which state is it?"""
    def panel_now(wait=2.5):
        time.sleep(wait)
        _, wins = drive("windows")
        up = any(l.startswith(NAME + "\t") and "Open a document" in l for l in wins.splitlines())
        if up:
            drive("key", "escape")
            time.sleep(1.2)
        return up
    reset_state({"theme": "light"})
    launch(settle=4)
    ev = {}
    drive("key", "cmd+o"); ev["home"] = panel_now()
    press("Library"); time.sleep(1.5)
    drive("key", "cmd+o"); ev["library"] = panel_now()
    drive("key", "cmd+k"); time.sleep(1.5); drive("key", "escape"); time.sleep(1.0)
    drive("key", "cmd+o"); ev["cmdk_esc_wait_1s"] = panel_now()
    drive("key", "cmd+k"); time.sleep(1.5); drive("key", "escape")
    drive("key", "cmd+o"); ev["cmdk_esc_no_wait"] = panel_now()
    ev["shot_no_wait"] = shot("cmdo-after-esc-no-wait")
    if not ev["cmdk_esc_no_wait"]:
        drive("key", "cmd+o"); ev["cmdk_esc_no_wait_second_press"] = panel_now()
    drive("key", "cmd+k"); time.sleep(1.5)
    drive("key", "cmd+o"); ev["while_cmdk_open"] = panel_now()
    ev["shot_while_open"] = shot("cmdo-while-cmdk-open")
    drive("key", "escape")
    bad = [k for k in ("home", "library", "cmdk_esc_wait_1s", "cmdk_esc_no_wait") if not ev[k]]
    record("T4.0d ⌘O in several states", "fail" if bad else "pass", f"no panel in: {bad}; all: " + str({k: v for k, v in ev.items() if isinstance(v, bool)}), **ev)
    quit_app()


@case("P25 files from Finder (cold, several at once, Word)")
def p25():
    """Foundation patch 25: cold open goes straight into the Reader; several files at once all become tabs."""
    ev, bad = {}, []

    def tabs_in(txt, names):
        return [n for n in names if n in txt]

    # (a) cold start, Open With one PDF
    reset_state({"theme": "light"})
    quit_app()
    launch(f"{FX}/five-pages.pdf", settle=0.5)
    ev["a_early_shot"] = shot("p25-a-cold-one-early")
    time.sleep(6)
    drive("activate", NAME)
    t = axdump("p25-a-cold-one")
    for _ in range(5):  # the accessibility tree of a just-launched window can be empty for a few seconds
        if len(t.splitlines()) > 20:
            break
        time.sleep(2)
        t = axdump("p25-a-cold-one")
    ev["a"] = {"tab": "five-pages.pdf" in t, "page": bool(re.search(r"page \d+ of 5|of 5", t)), "home_showing": "Open a document to begin" in t,
               "error": ui_error(), "procs": len(pids()), "shot": shot("p25-a-cold-one")}
    if not (ev["a"]["tab"] and ev["a"]["page"] and not ev["a"]["error"] and ev["a"]["procs"] == 1):
        bad.append("cold start with one PDF")
    quit_app()

    # (b) cold start with four files at once, one of them Word
    four = ["five-pages.pdf", "second.pdf", "third.pdf", "sample.docx"]
    reset_state({"theme": "light"})
    launch(*[f"{FX}/{n}" for n in four], settle=10)
    t = axdump("p25-b-cold-four")
    got = tabs_in(t, four)
    ev["b"] = {"tabs": got, "error": ui_error(), "procs": len(pids()), "shot": shot("p25-b-cold-four")}
    if len(got) != 4 or ev["b"]["error"] or ev["b"]["procs"] != 1:
        bad.append(f"cold start with four files (tabs {got})")

    # (c) six more while running, in one go
    six = ["many-pages.pdf", "annotated.pdf", "sample.xlsx", "notes.md", "notes.txt", "page.html"]
    sh(["open", "-a", APP, *[f"{FX}/{n}" for n in six]])
    time.sleep(12)
    t = axdump("p25-c-six-more")
    got = tabs_in(t, four + six)
    ev["c"] = {"tabs": got, "missing": [n for n in four + six if n not in got], "error": ui_error(), "procs": len(pids()),
               "shot": shot("p25-c-six-more")}
    if len(got) != 10 or ev["c"]["error"] or ev["c"]["procs"] != 1:
        bad.append(f"six more while running (missing {ev['c']['missing']})")
    # tab order as shown (left to right), against the order the files were handed over
    def strip_order(txt, names):
        pos = {}
        for l in txt.splitlines():
            m = re.search(r'AXStaticText desc="([^"]+)" @(-?\d+),', l)
            if m and m.group(1) in names and m.group(1) not in pos:
                pos[m.group(1)] = int(m.group(2))
        return sorted(pos, key=pos.get)
    order = strip_order(t, four + six)
    ev["c"]["order_shown"] = order
    name_key = lambda n: (os.path.splitext(n)[0].lower(), os.path.splitext(n)[1].lower())
    ev["c"]["order_given"] = four + six
    ev["c"]["order_expected_m24"] = sorted(four, key=name_key) + sorted(six, key=name_key)  # each batch in Finder's Name order
    ev["c"]["order_kept"] = order == ev["c"]["order_expected_m24"]
    if not ev["c"]["order_kept"]:
        bad.append(f"M-24 tab order: shown {order}")
    # the tab keys still land right with ten tabs: ⌘n for the position of many-pages.pdf → "of 500"
    if "many-pages.pdf" in order and order.index("many-pages.pdf") < 9:
        n = order.index("many-pages.pdf") + 1
        drive("key", "cmd+1" if n != 1 else "cmd+2")
        time.sleep(1.5)
        drive("key", f"cmd+{n}")
        time.sleep(2)
        t = axdump("p25-c-cmdn")
        ev["c"]["cmd_n"] = n
        ev["c"]["cmd_n_lands_on_many_pages"] = "of 500" in " ".join(l for l in t.splitlines() if re.search(r"page \d+ of \d+", l))
        ev["c"]["cmd_n_shot"] = shot("p25-c-cmdn")
        if not ev["c"]["cmd_n_lands_on_many_pages"]:
            bad.append(f"⌘{n} with ten tabs")
    quit_app()

    # (d) Word file on a cold start
    reset_state({"theme": "light"})
    launch(f"{FX}/sample.docx", settle=8)
    t = axdump("p25-d-word")
    ev["d"] = {"tab": "sample.docx" in t, "text": "marker-docx" in t, "error": ui_error(), "shot": shot("p25-d-word"),
               "notes": [l.strip()[:200] for l in t.splitlines() if re.search(r"skipp|not shown|left out|couldn", l, re.I)][:5]}
    if not (ev["d"]["tab"] and ev["d"]["text"] and not ev["d"]["error"]):
        bad.append("Word file on a cold start")
    quit_app()
    record("P25 files from Finder (cold, several at once, Word)", "fail" if bad else "pass",
           f"failed: {bad}" if bad else f"cold one → Reader; cold four → 4 tabs; six more → 10 tabs; each batch in name order (M-24)={ev['c']['order_kept']}; ⌘n lands right={ev['c'].get('cmd_n_lands_on_many_pages')}; Word shows its text", **ev)


def zoom_percent(tag):
    t = axdump(tag)
    L = t.splitlines()
    for i, l in enumerate(L):
        if 'AXStaticText desc="%"' in l:
            for j in range(i - 1, max(0, i - 4), -1):
                m = re.search(r'desc="(\d+)"', L[j])
                if m:
                    return int(m.group(1))
    return None


def main_centre():
    rc, o = find("main", timeout=3)
    w = window_up(3)
    m = re.search(r"\t(\d+),(\d+) (\d+)x(\d+)", w or "")
    x, y, wd, ht = map(int, m.groups())
    return x + wd // 2 - 20, y + ht // 2, (x, y, wd, ht)


@case("P26 rotated page, Excel grid, pinch")
def p26():
    ev, bad = {}, []
    # ── a /Rotate 90 page: view, mark, save, print ────────────────────────────────────────────
    work = f"{FX}/rotated-work.pdf"
    shutil.copy(f"{FX}/rotated.pdf", work)
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(work, settle=4)
    r = {"opened": ok, "view_shot": shot("p26-rotated-view")}
    t = axdump("p26-rotated-view")
    r["error"] = ui_error()
    press("Mark 2")
    time.sleep(1.5)
    rc, o = press("Rectangle", role="AXButton")  # Accessibility press: the collapsed rail's frames don't match the screen
    r["tool_press"] = o[:100]
    time.sleep(1)
    cx, cy, win = main_centre()
    r["window"] = win
    # In Mark mode at this window size the page sits at window (378,213)–(812,520). Drag well inside it.
    r["drag_window"] = [480, 300, 600, 400]
    r["drag_screen"] = [win[0] + 480, win[1] + 300, win[0] + 600, win[1] + 400]
    # /Rotate 90: across the screen = up the page's y (842), down the screen = along its x (595)
    r["expected_rect_approx"] = [round((300 - 213) / 307 * 595), round((480 - 378) / 434 * 842),
                                 round((400 - 213) / 307 * 595), round((600 - 378) / 434 * 842)]
    drive("drag", *r["drag_screen"])
    time.sleep(1.5)
    r["marked_shot"] = shot("p26-rotated-marked")
    r["status_after_mark"] = [re.sub(r"\s*@.*$", "", l.strip())[:120] for l in axdump("p26-rotated-marked").splitlines() if re.search(r"shape|unsaved", l)][:3]
    rc, o = press("Save", role="AXButton")
    r["save_press"] = o[:100]
    time.sleep(4)
    r["after_save_shot"] = shot("p26-rotated-after-save")
    r["after_save_windows"] = [l for l in drive("windows")[1].splitlines() if l.startswith(NAME)]
    shutil.copy(work, f"{OUT}/p26-rotated-saved.pdf")
    _, js = sh(f"qpdf --json '{work}'", timeout=60)
    try:
        objs = json.loads(js)["qpdf"][1]
        sq = [v["value"] for v in objs.values() if isinstance(v.get("value"), dict) and v["value"].get("/Subtype") == "/Square"]
        r["squares"] = [{"Rect": q.get("/Rect"), "has_AP": "/AP" in q} for q in sq]
        pages = [v["value"] for v in objs.values() if isinstance(v.get("value"), dict) and v["value"].get("/Type") == "/Page"]
        r["page_rotate"] = [pg.get("/Rotate") for pg in pages]
    except Exception as e:  # noqa
        r["qpdf_error"] = str(e)[:200]
    r["new_square_saved"] = len(r.get("squares", [])) >= 2  # the fixture has one Square already
    exp = r["expected_rect_approx"]
    r["new_square_where_expected"] = any(
        q["Rect"] and all(abs(float(a) - b) <= 25 for a, b in zip(sorted(map(float, q["Rect"][0::2])) + sorted(map(float, q["Rect"][1::2])),
                                                                 sorted(exp[0::2]) + sorted(exp[1::2])))
        for q in r.get("squares", []) if q["Rect"] != [100, 600, 260, 680])
    # reopen-free check on screen: the saved mark must still sit where it was drawn
    r["after_save_status"] = [re.sub(r"\s*@.*$", "", l.strip())[:120] for l in axdump("p26-rotated-saved").splitlines() if re.search(r"shape|saved", l)][:3]
    # print it
    before = spool_files()
    drive("key", "cmd+p")
    time.sleep(2)
    r["print_card"] = shot("p26-rotated-print-card")
    rc, r["card_press"] = press("Print 2 pages", contains=True)
    time.sleep(4)
    r["panel"] = screen("p26-rotated-print-panel")
    press("Print", role="AXButton", index=-1)
    time.sleep(3)
    press("Add to Printer", role="AXButton")
    time.sleep(10)
    new = sorted(spool_files() - before)
    r["spool_new"] = new
    if new:
        f = f"{OUT}/p26-rotated-printed.pdf"
        sh(f"sudo cp /var/spool/cups/{new[-1]} '{f}' && sudo chmod 644 '{f}'")
        pr = {}
        r["print_vector"] = check_printed(f, pr, "marker-1")
        r["print_text"] = pr.get("text", "")[:200]
        r["print_has_page_text"] = "marker-1" in pr.get("text", "")
        r["print_info"] = [l for l in pr.get("info", "").splitlines() if re.search(r"Page size|Page rot|Pages", l)]
        r["print_images"] = pr.get("images", "")[:300]
        r["print_live_annots"] = pr.get("live_annots")
        sh(f"pdftoppm -r 50 -png '{f}' '{OUT}/shots/p26-rotated-printed'")
    else:
        r["print_vector"] = False
    quit_app()
    ev["rotated"] = r
    if not (ok and not r["error"] and r["new_square_saved"] and r["print_vector"]):
        bad.append(f"rotated page (mark saved={r['new_square_saved']} where drawn={r.get('new_square_where_expected')}, print vector={r['print_vector']})")

    # ── Excel: formats, Find on value and on shown text, hidden sheet ─────────────────────────
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/formats.xlsx", settle=5)
    t = axdump("p26-xlsx")
    x = {"opened": ok, "shot": shot("p26-xlsx"), "error": ui_error(),
         "cells": [l.strip()[:110] for l in t.splitlines() if re.search(r"1234|1,234|₹|3\.14|6\.28|Merged|2026|46334|A4\*2", l)][:14],
         "sheet_tabs": [re.sub(r"\s*@.*$", "", l.strip())[:120] for l in t.splitlines() if re.search(r"Charges|Second sheet|Hidden notes|sheets\"", l)][:8]}
    x["hidden_sheet_listed"] = "Hidden notes" in t
    x["currency_as_file_holds"] = bool(re.search(r"₹1,234\.50", t))
    fields = lambda tx: [re.sub(r"\s*@.*$", "", l.strip())[:120] for l in tx.splitlines() if "AXTextField" in l or "AXSearchField" in l]
    base_fields = fields(t)
    # does the ⌘F key open Find here (no click on the page first)?
    drive("key", "cmd+f")
    time.sleep(1.5)
    kt = axdump("p26-xlsx-cmdf")
    x["cmd_f_key_new_fields"] = [f for f in fields(kt) if f not in base_fields]
    x["cmd_f_key_shot"] = shot("p26-xlsx-cmdf")
    drive("key", "escape")
    time.sleep(0.8)
    for tag, needle in (("value", "1234"), ("shown", "2026"), ("absent", "7777")):
        rc, o = press("Find ⌘F", role="AXButton")
        time.sleep(1.5)
        ft0 = axdump(f"p26-xlsx-find-{tag}-open")
        x[f"find_{tag}_fields"] = [f for f in fields(ft0) if f not in base_fields]
        drive("key", "cmd+a")
        for ch in needle:
            drive("key", ch)
            time.sleep(0.08)
        time.sleep(0.5)
        drive("key", "return")
        time.sleep(2)
        ft = axdump(f"p26-xlsx-find-{tag}")
        x[f"find_{tag}"] = [re.sub(r"\s*@.*$", "", l.strip())[:140] for l in ft.splitlines() if l not in t and "AXStaticText" in l][:8]
        x[f"find_{tag}_shot"] = shot(f"p26-xlsx-find-{tag}")
        drive("key", "escape")
        time.sleep(0.8)
    rc, o = press("Hidden notes", contains=True, click=True)
    time.sleep(1.5)
    ht = axdump("p26-xlsx-hidden")
    x["hidden_sheet_opens"] = "marker-hidden" in ht
    x["hidden_shot"] = shot("p26-xlsx-hidden")
    quit_app()
    ev["xlsx"] = x
    if not (ok and not x["error"] and x["currency_as_file_holds"] and x["hidden_sheet_listed"]):
        bad.append(f"Excel (currency shown={x['currency_as_file_holds']}, hidden sheet listed={x['hidden_sheet_listed']})")

    # ── zoom by wheel + Ctrl (real events), and a synthetic trackpad pinch ────────────────────
    reset_state({"theme": "light"})
    launch(settle=4)
    open_doc(f"{FX}/five-pages.pdf", settle=4)
    cx, cy, _ = main_centre()
    z = {"start": zoom_percent("p26-zoom-0")}
    drive("scroll", cx, cy, -4, "--ctrl")
    time.sleep(1.5)
    z["after_ctrl_wheel_up"] = zoom_percent("p26-zoom-1")
    drive("scroll", cx, cy, 4, "--ctrl")
    time.sleep(1.5)
    z["after_ctrl_wheel_down"] = zoom_percent("p26-zoom-2")
    _, z["pinch_out"] = drive("pinch", cx, cy, 0.6)
    time.sleep(1.5)
    z["after_pinch_in_gesture"] = zoom_percent("p26-zoom-3")
    drive("pinch", cx, cy, -0.4)
    time.sleep(1.5)
    z["after_pinch_out_gesture"] = zoom_percent("p26-zoom-4")
    z["shot"] = shot("p26-zoom")
    z["ctrl_wheel_zooms"] = None not in (z["start"], z["after_ctrl_wheel_up"]) and z["after_ctrl_wheel_up"] != z["start"]
    z["synthetic_pinch_zooms"] = None not in (z["after_ctrl_wheel_down"], z["after_pinch_in_gesture"]) and z["after_pinch_in_gesture"] != z["after_ctrl_wheel_down"]
    quit_app()
    ev["zoom"] = z
    record("P26 rotated page, Excel grid, pinch", "fail" if bad else "pass",
           (f"failed: {bad}; " if bad else "") + f"rotated: squares {r.get('squares')}, print {r.get('print_info')}; xlsx tabs hidden listed={x['hidden_sheet_listed']}, "
           f"⌘F key opens Find={bool(x['cmd_f_key_new_fields'])}, find value={x['find_value'][:3]}, find shown={x['find_shown'][:3]}, find absent={x['find_absent'][:3]}; zoom {z['start']}→{z['after_ctrl_wheel_up']}→{z['after_ctrl_wheel_down']} (wheel+Ctrl), "
           f"→{z['after_pinch_in_gesture']}→{z['after_pinch_out_gesture']} (synthetic pinch)", **ev)


@case("M-14 .NET message in Details")
def m14():
    src = f"{FX}/noaccess.pdf"
    shutil.copy(f"{FX}/five-pages.pdf", src)
    os.chmod(src, 0)
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(src, settle=4)
    t = axdump("m14-after-open")
    ev = {"opened_tab": ok, "shot": shot("m14-after-open"),
          "messages": [l.strip()[:220] for l in t.splitlines() if re.search(r"denied|permission|access|couldn|could not|read", l, re.I)][:6]}
    rc, o = press("Details", contains=True)
    ev["details_press"] = o[:120]
    time.sleep(1.5)
    d = axdump("m14-details")
    ev["details_shot"] = shot("m14-details")
    lines = [l.strip()[:300] for l in d.splitlines() if "AXStaticText" in l or "AXTextArea" in l]
    new = [l for l in lines if l not in t]
    ev["details_text"] = new[:12]
    keys = [l for l in new if re.search(r'desc="[^"]*\b[A-Z][A-Za-z]+_[A-Za-z_]+\b', l)]
    ev["resource_keys"] = keys
    ev["real_message"] = any(re.search(r"denied|permission", l, re.I) for l in new)
    os.chmod(src, 0o644)
    record("M-14 .NET message in Details", "pass" if rc == 0 and ev["real_message"] and not keys else "fail",
           f"Details pressed={rc == 0}; real .NET text={ev['real_message']}; resource keys={len(keys)}", **ev)
    quit_app()



def main():
    if A.suite == "pw":
        t4_6()
        m18()
        return
    if A.suite == "shared":
        p26()
        p25()
        t4_0()
        t4_0d()
        m_shared()
        m14()
        t3_5()
        return
    if A.suite == "print":
        t4_7()
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, _ = open_doc(f"{FX}/five-pages.pdf")
        record("print: five-pages opened for the landscape check", "info", f"opened={ok}; panel waits {PANEL_WAITS}; retries {PANEL_RETRIES}")
        quit_app()
        return
    if A.suite == "diag":
        t4_0b()
        t4_0()
        reset_state({"theme": "light"})
        launch(settle=4)
        ok, _ = open_doc(f"{FX}/five-pages.pdf")
        record("diag open panel", "pass" if ok else "fail", f"opened={ok}", exceptions=exceptions_in(app_log()), shot=shot("diag-after-open"))
        quit_app()
        t4_0c()
        t5_10()
        return
    _, trust = drive("trust")
    record("env", "info", trust.replace("\n", "; "), sw=sh("sw_vers")[1], arch=sh("uname -m")[1],
           cpu=sh("sysctl -n machdep.cpu.brand_string")[1], displays=drive("displays")[1])
    t1_6()
    t4_0b()
    t4_0()
    t5_10()
    t3_7()
    t4_14()
    t4_12()
    t4_7()
    t4_8()
    t3_5()
    t4_6()
    m18()
    if A.runs > 0:
        t2(A.runs)
    if A.suite == "full":
        t4_0c()
        t3_1()
        t3_2()
        t3_3()
        t4_9()
        t4_15()
        t5_1()
        t5_3()
        t5_4()
        t5_7()
        t5_8()
        t5_9()
        t5_5()
    quit_app()
    log("done")


main()
