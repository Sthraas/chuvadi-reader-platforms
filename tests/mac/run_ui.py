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


def reset_state(settings=None):
    quit_app()
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


def press(text, contains=False, role=None, index=0):
    args = ["press", NAME, text]
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
    if how == "key":
        drive("key", "cmd+o")
    else:
        rc, o = press("Open ⌘O")
        if rc != 0:
            press("Open document")
    time.sleep(2.5)
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


def run_cmd(label, settle=1.5):
    """Runs a command through the ⌘K bar, as a person would: ⌘K, type, Return."""
    drive("activate", NAME)
    drive("key", "cmd+k")
    time.sleep(0.8)
    drive("type", label)
    time.sleep(0.8)
    drive("key", "return")
    time.sleep(settle)


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
                rc2, o2 = press(sec, contains=True, index=-1)
                time.sleep(1.2)
                ev["settings-" + sec] = shot("light-settings-" + sec.lower()) + f" ({o2[:70]})"
                t = axdump("settings-" + sec.lower())
                texts += t
                if sec == "About":
                    rc3, o3 = press("Licences", contains=True)
                    time.sleep(1.5)
                    ev["licences"] = shot("light-licences") + f" ({o3[:70]})"
                    lic = axdump("licences")
                    rc4, o4 = press(".NET runtime", contains=True)
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
        press("Appearance", contains=True, index=-1)
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
    panel = sum(1 for l in wins.splitlines() if l.startswith(NAME + "\t") and "layer=0" in l) > 1
    drive("key", "escape")
    record("T4.0 keyboard reaches the app at launch", "pass" if opened_without_click and panel else "fail",
           f"⌘K before any click opens the bar={opened_without_click}; after a click={opened_after_click}; ⌘O opens a panel={panel}",
           shots=[s1, s2, sc], windows=wins)
    quit_app()


@case("T3.5 window + immersive + keys")
def t3_5():
    reset_state({"theme": "light"})
    launch(settle=4)
    ok, _ = open_doc(f"{FX}/five-pages.pdf")
    ok2, _ = open_doc(f"{FX}/second.pdf")
    ev = {"docs_opened": [ok, ok2]}
    _, ev["before"] = drive("winstate", NAME)
    # Immersive: ⌃⌘F (Mac binding) and F11 (what the Ui shows)
    drive("key", "ctrl+cmd+f")
    time.sleep(2.5)
    _, ev["immersive_ctrl_cmd_f"] = drive("winstate", NAME)
    ev["immersive-shot"] = shot("light-reader-immersive")
    drive("key", "escape")
    time.sleep(2)
    drive("key", "f11")
    time.sleep(2.5)
    _, ev["immersive_f11"] = drive("winstate", NAME)
    ev["f11-shot"] = screen("screen-after-f11")
    drive("key", "escape")
    time.sleep(1.5)
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
    full = "fullscreen=true" in ev["immersive_ctrl_cmd_f"]
    record("T3.5 window + immersive + keys", "pass" if full and ev["ctrl_tab_changed_screen"] and ev["minimized"] else "fail",
           f"⌃⌘F full screen={full}; ⌃Tab switches tab={ev['ctrl_tab_changed_screen']}; minimise={ev['minimized']}", **ev)
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
    run_cmd("Copy file path")
    _, pb = sh("pbpaste")
    good = pb.strip() in (f"{FX}/five-pages.pdf", os.path.realpath(f"{FX}/five-pages.pdf"))
    record("T4.12 copy file path (text clipboard)", "pass" if good else "fail", f"doc opened={ok}; pasteboard: {pb[:200]!r}")
    # image: Snapshot a region → copies PNG?
    run_cmd("Snapshot a region")
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
    run_cmd("Show in folder")
    time.sleep(3)
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
    rc, ev["card-press"] = press("Print", role="AXButton", index=-1)
    time.sleep(4)
    ev["panel"] = screen("print-panel")
    axdump("print-panel")
    drive("key", "return")
    time.sleep(8)
    new = sorted(spool_files() - before)
    ev["spool-new"] = new
    ev["jobs"] = cups_jobs()
    good = False
    if new:
        f = f"{OUT}/printed-annotated.pdf"
        sh(f"sudo cp /var/spool/cups/{new[-1]} '{f}' && sudo chmod 644 '{f}'")
        good = check_printed(f, ev, "marker-1")
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
    ev = {}
    for f in ["aes256.pdf", "aes128.pdf", "rc4.pdf", "owner-only.pdf"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        ok, _ = open_doc(f"{FX}/{f}", settle=4)
        txt = axdump("pw-" + f)
        e = {"tab": ok, "shot": shot("pw-" + f.replace(".", "_")),
             "messages": [l.strip()[:200] for l in txt.splitlines() if re.search(r"password|encrypted|locked|unlock", l, re.I)][:6]}
        field = "AXTextField" in txt and re.search(r"password", txt, re.I)
        if field and f != "owner-only.pdf":
            press("password", contains=True)
            drive("type", "wrong")
            drive("key", "return")
            time.sleep(2)
            e["wrong"] = [l.strip()[:200] for l in axdump("pw-wrong-" + f).splitlines() if re.search(r"wrong|incorrect|password", l, re.I)][:4]
            press("password", contains=True)
            drive("key", "cmd+a")
            drive("type", "user1")
            drive("key", "return")
            time.sleep(3)
            e["right_shows_page"] = "marker-1" in axdump("pw-right-" + f) or "Page 1" in axdump("pw-right2-" + f)
            e["right_shot"] = shot("pw-right-" + f.replace(".", "_"))
        e["prompt"] = bool(field)
        ev[f] = e
        quit_app()
    bad = [k for k, v in ev.items() if k != "owner-only.pdf" and not v.get("right_shows_page")]
    record("T4.6 passwords", "pass" if not bad else "fail", f"no working prompt for: {bad}" if bad else "prompt, wrong and right password", **ev)


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


def main():
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
    if A.runs > 0:
        t2(A.runs)
    if A.suite == "full":
        t4_0c()
        t3_1()
        t3_2()
        t3_3()
        t4_9()
        t4_6()
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
