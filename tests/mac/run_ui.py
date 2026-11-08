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
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
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


def launch(*files, settle=3.0, fresh=False):
    if fresh:
        quit_app()
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


# ───────────────────────────── T1.6 / T2 ─────────────────────────────

@case("T1.6 Launch Services")
def t1_6():
    sh(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister", "-f", APP])
    rows = {}
    ok = True
    for f in ["five-pages.pdf", "sample.docx", "sample.xlsx", "notes.md", "notes.txt", "page.html"]:
        _, out = drive("lsquery", f"{FX}/{f}")
        can = APP in out
        default = out.splitlines()[0] if out else ""
        rows[f] = {"candidate": can, "default": default}
        if f in ("five-pages.pdf", "sample.docx", "sample.xlsx") and (not can or APP in default):
            ok = False
    record("T1.6 Launch Services", "pass" if ok else "fail",
           "candidate for pdf/docx/xlsx, never the default" if ok else "see rows", rows=rows)


def timing_runs(label, runs, cold, file=None):
    res = []
    for i in range(1, runs + 1):
        quit_app()
        time.sleep(1.0)
        if cold:
            sh("sudo purge", timeout=120)
            time.sleep(1.0)
        rc, out = drive("firstframe", APP, *([file] if file else []), f"{OUT}/timing", "--label", f"{label}-{i}", "--timeout", 40, timeout=80)
        try:
            j = json.load(open(f"{OUT}/timing/{label}-{i}.json"))
        except Exception:
            j = {"marks": {}, "error": out[-400:]}
        time.sleep(0.5)
        j["app"] = last_startup_block()
        res.append(j)
        # keep only a few evidence frames
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
    sets = {
        "cold": timing_runs("cold", runs, cold=True),
        "warm": timing_runs("warm", runs, cold=False),
        "pdf-cold": timing_runs("pdf-cold", runs, cold=True, file=f"{FX}/five-pages.pdf"),
        "pdf-warm": timing_runs("pdf-warm", runs, cold=False, file=f"{FX}/five-pages.pdf"),
    }
    for k, rs in sets.items():
        key = "first_page" if k.startswith("pdf") else "first_render"
        summary[k] = {
            "probe_window": stats([r["marks"].get("window") for r in rs]),
            "probe_" + key: stats([r["marks"].get(key) for r in rs]),
            "probe_process_start": stats([r["marks"].get("process_start") for r in rs]),
            "app_first_render": stats([r["app"].get("first-render") for r in rs]),
            "app_webview_ready": stats([r["app"].get("webview-ready") for r in rs]),
            "app_main": stats([r["app"].get("main") for r in rs]),
            "missing": sum(1 for r in rs if r["marks"].get(key) is None),
        }
    with open(f"{OUT}/timing/summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    missing = sum(v["missing"] for k, v in summary.items() if k != "first_launch")
    record("T2 startup", "info" if missing == 0 else "fail",
           f"{missing} runs without the expected frame" if missing else "all runs reached their frame",
           summary={k: v for k, v in summary.items() if k != "first_launch"},
           first_launch=summary["first_launch"].get("marks"))


# ───────────────────────────── T3 look + menus ─────────────────────────────

MENUS = []


@case("T3.7 menu bar")
def t3_7():
    global MENUS
    reset_state({"theme": "light"})
    launch(f"{FX}/five-pages.pdf")
    MENUS = menu_dump("reader-pdf", live=True)
    tops = [m["title"] for m in MENUS]
    expected = ["Chuvadi", "File", "Edit", "View", "Document", "Window", "Help"]
    bad = []
    if [t for t in tops if t != "Apple"] != expected:
        bad.append(f"menus {tops} ≠ {expected}")
    ctrl = []

    def scan(items, path):
        for it in items:
            t = it.get("title", "")
            if re.search(r"\bCtrl\b", t) or re.search(r"\bF11\b", t):
                ctrl.append(" › ".join(path + [t]))
            if "items" in it:
                scan(it["items"], path + [t])
    for m in MENUS:
        scan(m.get("items", []), [m["title"]])
    if ctrl:
        bad.append(f"'Ctrl'/'F11' in menu titles: {ctrl}")
    shortcuts = []

    def collect(items, path):
        for it in items:
            if it.get("shortcut"):
                shortcuts.append(f"{' › '.join(path + [it['title']])}  {it['shortcut']}")
            if "items" in it:
                collect(it["items"], path + [it["title"]])
    for m in MENUS:
        collect(m.get("items", []), [m["title"]])
    settings_cmd = any(s.endswith("⌘,") for s in shortcuts)
    if not settings_cmd:
        bad.append("no ⌘, (Settings…) item in the app menu")
    record("T3.7 menu bar", "pass" if not bad else "fail", "; ".join(bad) or "menus and glyphs as expected",
           menus=tops, shortcuts=shortcuts)
    # Live enabled state with no document: close the tab and dump again
    menu_by = menu_by_title(MENUS, "Close tab")
    if menu_by:
        menu(*menu_by)
        time.sleep(1.5)
    nodoc = menu_dump("no-document", live=True)
    doc_menu = next((m for m in nodoc if m["title"] == "Document"), {"items": []})
    enabled = [i["title"] for i in doc_menu.get("items", []) if i.get("enabled") and i.get("title")]
    record("T3.7b document menu greyed with no document", "pass" if not enabled else "fail",
           f"enabled with no document: {enabled}" if enabled else "all Document items greyed", items=doc_menu.get("items"))
    quit_app()


@case("T3.1 screens light")
def t3_1():
    reset_state({"theme": "light"})
    launch(settle=4)
    ev = {"home-first-run": shot("light-home-first-run")}
    txt = axdump("home-first-run")
    ctrl_lines = [l.strip()[:160] for l in txt.splitlines() if re.search(r"\bCtrl\b|\bF11\b", l)]
    sh(["open", "-a", APP, f"{FX}/five-pages.pdf"])
    time.sleep(4)
    ev["reader-read"] = shot("light-reader-read")
    txt2 = axdump("reader-read")
    ctrl_lines += [l.strip()[:160] for l in txt2.splitlines() if re.search(r"\bCtrl\b|\bF11\b", l)]
    menus = menu_dump("t31", live=False)
    for mode in ["Mark mode", "Arrange mode", "Protect mode", "Read mode"]:
        rc, out = press_menu(menus, mode)
        time.sleep(2.5)
        ev[mode] = shot("light-reader-" + mode.split()[0].lower()) + f" ({out})"
    for target in ["Library", "Settings", "Home"]:
        p = find_menu_item(menus, lambda it, t=target: it.get("title") == t and "items" not in it)
        rc, out = menu(*p) if p else (1, "no menu item")
        time.sleep(2.5)
        ev[target] = shot("light-" + target.lower()) + f" ({out})"
        if target == "Settings":
            stxt = axdump("settings")
            ctrl_lines += [l.strip()[:160] for l in stxt.splitlines() if re.search(r"\bCtrl\b|\bF11\b", l)]
            for sec in ["Appearance", "Reading", "Saving", "Library", "Language", "Accessibility", "Shortcuts",
                        "Kiosk", "Account", "About"]:
                rc2, o2 = press(sec, index=-1)
                time.sleep(1.2)
                ev["settings-" + sec] = shot("light-settings-" + sec.lower()) + f" ({o2[:80]})"
                if sec == "Shortcuts":
                    sc = axdump("settings-shortcuts")
                    ctrl_lines += [l.strip()[:160] for l in sc.splitlines() if re.search(r"\bCtrl\b|\bF11\b|⌘Tab", l)]
                if sec == "About":
                    rc3, o3 = press("Licences", contains=True)
                    time.sleep(1.5)
                    ev["licences"] = shot("light-licences") + f" ({o3[:80]})"
                    lic = axdump("licences")
                    tabs = [t for t in ["Licence agreement", "Licence", "Privacy", "notices", ".NET runtime"] if t.lower() in lic.lower()]
                    rc4, o4 = press(".NET runtime", contains=True)
                    time.sleep(1.5)
                    ev["licences-dotnet"] = shot("light-licences-dotnet") + f" ({o4[:80]})"
                    dot = axdump("licences-dotnet")
                    record("T1.10 Licences tabs", "pass" if ".NET runtime" in tabs and "Mono" in dot else "fail",
                           f"tabs found: {tabs}; Mono notices shown: {'Mono' in dot}")
    uniq = sorted(set(ctrl_lines))
    record("T3.7c no Ctrl/F11 labels in the Ui", "pass" if not uniq else "fail",
           f"{len(uniq)} AX texts still say Ctrl/F11/⌘Tab" if uniq else "none", lines=uniq[:80])
    record("T3.1 screens light", "info", "screenshots taken", shots=ev)
    quit_app()


@case("T3.2 themes")
def t3_2():
    ev = {}
    for th in THEMES:
        reset_state({"theme": th})
        launch(f"{FX}/five-pages.pdf", settle=4)
        ev[th + "-reader"] = shot(f"{th}-reader")
        menus = menu_dump(f"theme-{th}", live=False)
        p = find_menu_item(menus, lambda it: it.get("title") == "Home" and "items" not in it)
        if p:
            menu(*p)
            time.sleep(2)
            ev[th + "-home"] = shot(f"{th}-home")
        p = find_menu_item(menus, lambda it: it.get("title") == "Settings" and "items" not in it)
        if p:
            menu(*p)
            time.sleep(2)
            ev[th + "-settings"] = shot(f"{th}-settings")
        saved = (read_settings() or {}).get("theme")
        ev[th + "-kept"] = saved
        quit_app()
    record("T3.2 themes", "info", "5 themes × reader/home/settings", shots=ev)


@case("T3.3 interface size")
def t3_3():
    ev = {}
    for pct in ["125", "150"]:
        reset_state({"theme": "light", "ui-scale": pct})
        launch(f"{FX}/five-pages.pdf", settle=4)
        ev[pct] = shot(f"light-reader-scale{pct}")
        quit_app()
    record("T3.3 interface size", "info", "125 % and 150 %", shots=ev)


@case("T3.5 window buttons")
def t3_5():
    reset_state({"theme": "light"})
    launch(f"{FX}/five-pages.pdf", settle=4)
    ev = {}
    _, before = drive("winstate", NAME)
    ev["before"] = before
    rc, o = press("Minimize")
    time.sleep(1.5)
    _, st = drive("winstate", NAME)
    minimized = "minimized=true" in st
    ev["minimize"] = o + " | " + st
    drive("setwin", NAME, "minimized", "false")
    time.sleep(1.5)
    rc, o = press("Zoom")
    time.sleep(1.5)
    _, st2 = drive("winstate", NAME)
    ev["zoom"] = o + " | " + st2
    ev["zoomed-shot"] = shot("light-reader-zoomed")
    zoom_changed = st2.split("cg windows:")[-1] != before.split("cg windows:")[-1]
    rc, o = press("Exit full screen")  # label the Ui gives the green button when zoomed
    ev["green-label-when-zoomed"] = o
    time.sleep(1.5)
    _, st3 = drive("winstate", NAME)
    ev["unzoom"] = st3
    # Immersive ⌃⌘F
    drive("key", "ctrl+cmd+f")
    time.sleep(2.5)
    _, st4 = drive("winstate", NAME)
    ev["immersive"] = st4
    ev["immersive-shot"] = shot("light-reader-immersive")
    drive("key", "escape")
    time.sleep(2)
    _, st5 = drive("winstate", NAME)
    ev["after-escape"] = st5
    ev["after-escape-shot"] = shot("light-reader-after-escape")
    # Close (red): window goes; does the process stay?
    rc, o = press("Close")
    time.sleep(2)
    ev["close"] = o
    ev["after-close-processes"] = pids()
    _, ev["after-close-windows"] = drive("windows")
    record("T3.5 window buttons", "pass" if minimized and zoom_changed else "fail",
           f"minimise={'ok' if minimized else 'NO'}, zoom changes frame={'ok' if zoom_changed else 'NO'}", **ev)
    quit_app()


# ───────────────────────────── T4 function ─────────────────────────────

@case("T4.14 single instance")
def t4_14():
    reset_state({"theme": "light"})
    launch(f"{FX}/five-pages.pdf", settle=4)
    p0 = pids()
    sh(["open", "-a", APP, f"{FX}/second.pdf", f"{FX}/third.pdf"])
    time.sleep(4)
    p1 = pids()
    _, wins = drive("windows")
    nwin = sum(1 for l in wins.splitlines() if l.startswith(NAME + "\t") and "layer=0" in l)
    txt = axdump("single-instance")
    tabs = [n for n in ["five-pages.pdf", "second.pdf", "third.pdf"] if n in txt]
    ev = {"shot": shot("single-instance-3-tabs"), "pids_before": p0, "pids_after": p1, "windows": nwin, "tabs_seen": tabs}
    ok = len(p1) == 1 and p0 == p1 and nwin == 1 and len(tabs) == 3
    # order: positions of names in the AX dump (tabs are laid out left to right)
    order = sorted(tabs, key=lambda n: txt.find(n))
    ev["order"] = order
    record("T4.14 single instance", "pass" if ok and order == ["five-pages.pdf", "second.pdf", "third.pdf"] else "fail",
           f"processes {len(p1)}, windows {nwin}, tabs {tabs}, order {order}", **ev)
    # forced second instance (open -n) — recorded only
    sh(["open", "-n", "-a", APP, f"{FX}/five-pages.pdf"])
    time.sleep(5)
    record("T4.14b open -n (forced new instance)", "info", f"processes now {len(pids())}", pids=pids())
    quit_app()
    sh(["pkill", "-9", "-x", "ChuvadiReader.Mac"])


@case("T4.12 clipboard text + T4.13 Show in Finder")
def t4_12():
    reset_state({"theme": "light"})
    launch(f"{FX}/five-pages.pdf", settle=4)
    menus = menu_dump("clip", live=False)
    sh("pbcopy < /dev/null")
    rc, o = press_menu(menus, "Copy file path")
    time.sleep(1.5)
    _, pb = sh("pbpaste")
    ok = pb.strip() == os.path.realpath(f"{FX}/five-pages.pdf") or pb.strip() == f"{FX}/five-pages.pdf"
    record("T4.12 copy file path (text clipboard)", "pass" if ok else "fail", f"pasteboard: {pb[:200]!r} ({o})")
    rc, o = press_menu(menus, "Show in folder")
    if rc != 0:
        rc, o = press_menu(menus, "Show in Finder")
    time.sleep(3)
    _, sel = sh(["osascript", "-e", 'tell application "Finder" to get POSIX path of (item 1 of (get selection) as alias)'], timeout=20)
    rcf, fdump = drive("axdump", "Finder", f"{OUT}/ax/finder-after-reveal.txt", timeout=60)
    try:
        ftxt = open(f"{OUT}/ax/finder-after-reveal.txt", encoding="utf-8").read()
    except Exception:
        ftxt = ""
    ok2 = sel.strip().endswith("five-pages.pdf") or ("five-pages.pdf" in ftxt and "fixtures" in ftxt)
    record("T4.13 Show in Finder", "pass" if ok2 else "fail", f"Finder selection: {sel[:200]!r} ({o})")
    sh(["osascript", "-e", 'tell application "Finder" to close every window'])
    quit_app()


def cups_jobs():
    _, out = sh("lpstat -W completed -o ChvdTest; lpstat -o ChvdTest")
    return out


def spool_files():
    _, out = sh("sudo ls /var/spool/cups")
    return set(x for x in out.split() if x.startswith("d"))


@case("T4.7 print vector")
def t4_7():
    reset_state({"theme": "light"})
    before = spool_files()
    launch(f"{FX}/annotated.pdf", settle=4)
    menus = menu_dump("print", live=False)
    ev = {}
    rc, o = press_menu(menus, "Print…") if menu_by_title(menus, "Print…") else press_menu(menus, "Print")
    ev["menu"] = o
    time.sleep(2)
    ev["card"] = shot("print-card")
    axdump("print-card")
    # The Ui's Print card: press its Print button (the last "Print" button in the page)
    found = drive("press", NAME, "Print", "--role", "AXButton", "--index", "-1")
    ev["card-press"] = found[1]
    time.sleep(4)
    ev["panel"] = shot("print-panel")
    panel = axdump("print-panel")
    # The native panel's default button is Print: Return presses it.
    drive("key", "return")
    ev["panel-press"] = "Return"
    time.sleep(8)
    new = sorted(spool_files() - before)
    ev["spool-new"] = new
    ev["jobs"] = cups_jobs()
    ok = False
    if new:
        f = f"{OUT}/printed-annotated.bin"
        sh(f"sudo cp /var/spool/cups/{new[-1]} '{f}' && sudo chmod 644 '{f}'")
        _, kind = sh(["file", "-b", f])
        ev["kind"] = kind
        if "PDF" in kind:
            _, fonts = sh(["pdffonts", f])
            _, imgs = sh(["pdfimages", "-list", f])
            _, text = sh(["pdftotext", f, "-"])
            _, info = sh(["pdfinfo", f])
            _, annots = sh(f"qpdf --json --json-key=pages '{f}' | grep -c '/Annots' || true")
            img_lines = [l for l in imgs.splitlines()[2:] if l.strip()]
            ev.update(fonts=fonts, images=imgs, text=text[:400], info=info, annots_refs=annots)
            ok = ("marker-1" in text) and len(img_lines) == 0 and len(fonts.splitlines()) > 2
    record("T4.7 print vector", "pass" if ok else "fail",
           "vector PDF in the spool: fonts present, no images, text extractable" if ok else "see evidence", **ev)
    quit_app()


@case("T4.8 print refused")
def t4_8():
    reset_state({"theme": "light"})
    jobs0 = cups_jobs()
    launch(f"{FX}/noprint.pdf", settle=4)
    menus = menu_dump("noprint", live=False)
    p = menu_by_title(menus, "Print…") or menu_by_title(menus, "Print")
    rc, o = menu(*p) if p else (1, "no Print item")
    time.sleep(2)
    s1 = shot("noprint-card")
    txt = axdump("noprint-card")
    msg = "permissions don" in txt
    drive("press", NAME, "Print", "--role", "AXButton", "--index", "-1")
    time.sleep(4)
    s2 = shot("noprint-after-press")
    txt2 = axdump("noprint-after-press")
    panel = "Copies" in txt2 or "Pages" in txt2 and "Paper" in txt2
    jobs1 = cups_jobs()
    ok = msg and not panel and jobs0 == jobs1
    record("T4.8 print refused", "pass" if ok else "fail",
           f"message shown={msg}, native panel opened={panel}, new CUPS job={jobs0 != jobs1}",
           shots=[s1, s2], menu=o)
    quit_app()


@case("T4.1 open panel")
def t4_1():
    reset_state({"theme": "light"})
    launch(settle=4)
    menus = menu_dump("open", live=False)
    p = find_menu_item(menus, lambda it: it.get("title", "").startswith("Open"))
    rc, o = menu(*p) if p else (1, "no Open item")
    time.sleep(2.5)
    s1 = shot("open-panel")
    _, wins = drive("windows")
    drive("key", "cmd+shift+g")
    time.sleep(1)
    drive("type", f"{FX}/sample.docx")
    time.sleep(0.8)
    drive("key", "return")
    time.sleep(1.2)
    drive("key", "return")
    time.sleep(5)
    s2 = shot("docx-opened")
    txt = axdump("docx-opened")
    ok = "marker-docx" in txt or "Chuvadi Mac test document" in txt
    record("T4.1 open panel → docx", "pass" if ok else "fail", f"docx text visible={ok} ({o})", shots=[s1, s2], windows=wins)
    quit_app()


@case("T4.9 formats")
def t4_9():
    ev = {}
    for f, marker in [("sample.xlsx", "marker-xlsx"), ("sample.docx", "marker-docx"), ("notes.md", "marker-md"),
                      ("notes.txt", "marker-txt"), ("page.html", "marker-html"), ("ஆவணம்-tamil-name.pdf", "marker-1")]:
        reset_state({"theme": "light"})
        launch(f"{FX}/{f}", settle=5)
        nm = re.sub(r"[^a-z0-9.-]", "_", f.lower())
        ev[f] = {"shot": shot("format-" + nm)}
        txt = axdump("format-" + nm)
        ev[f]["marker_in_ax"] = marker in txt
        if f == "sample.xlsx":
            ev[f]["currency_shown"] = "₹1,234.50" in txt or "1,234.50" in txt
            ev[f]["date_shown"] = [d for d in ["07/11/2026", "11/7/2026", "2026-11-07", "07-11-2026", "7/11/2026", "11/07/2026"] if d in txt]
        quit_app()
    bad = [k for k, v in ev.items() if not v["marker_in_ax"]]
    record("T4.9 formats", "pass" if not bad else "fail", f"not shown: {bad}" if bad else "all formats show their text", **ev)


# ───────────────────────────── T5 robustness ─────────────────────────────

@case("T5.1 damaged and hostile files")
def t5_1():
    ev = {}
    for f in ["damaged-truncated.pdf", "damaged-badxref.pdf", "damaged-garbage.pdf", "damaged-empty.pdf",
              "missing-part.docx", "aes256.pdf", "aes128.pdf", "rc4.pdf", "owner-only.pdf", "unsupported.zip"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        sh(["open", "-a", APP, f"{FX}/{f}"])
        time.sleep(5)
        alive = bool(pids())
        nm = f.replace(".", "_")
        e = {"alive": alive, "shot": shot("robust-" + nm) if alive else None}
        if alive:
            txt = axdump("robust-" + nm)
            e["messages"] = [l.strip()[:200] for l in txt.splitlines()
                             if re.search(r"could not|couldn|damaged|password|encrypted|error|offset|startxref", l, re.I)][:6]
        ev[f] = e
        quit_app()
    # hostile: bomb + far cell, then a normal file (queue blocked? Linux B-10)
    for f in ["bomb.docx", "far-cell.xlsx"]:
        reset_state({"theme": "light"})
        launch(settle=3)
        sh(["open", "-a", APP, f"{FX}/{f}"])
        peak = 0
        for _ in range(20):
            time.sleep(1)
            peak = max(peak, rss_mb() or 0)
        sh(["open", "-a", APP, f"{FX}/five-pages.pdf"])
        time.sleep(6)
        txt = axdump("hostile-" + f)
        ev[f] = {"peak_rss_mb_20s": peak, "alive": bool(pids()), "shot": shot("hostile-" + f.replace(".", "_")),
                 "next_file_opened": "marker-1" in txt}
        quit_app(force=True)
    crashed = [k for k, v in ev.items() if not v.get("alive")]
    record("T5.1 damaged and hostile files", "fail" if crashed else "info",
           f"app died on: {crashed}" if crashed else "app stayed up on every file (see messages)", **ev)


@case("T5.3 large files")
def t5_3():
    ev = {}
    for f in ["heavy-vector.pdf", "many-pages.pdf"]:
        reset_state({"theme": "light"})
        quit_app()
        rc, out = drive("firstframe", APP, f"{FX}/{f}", f"{OUT}/timing", "--label", "large-" + f, "--timeout", 60, timeout=100)
        try:
            j = json.load(open(f"{OUT}/timing/large-{f}.json"))["marks"]
        except Exception:
            j = {"error": out[-300:]}
        time.sleep(2)
        ev[f] = {"marks": j, "rss_mb": rss_mb(), "shot": shot("large-" + f.replace(".", "_"))}
        # scroll a little
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
    files = []
    for i in range(1, 31):
        p = f"{d}/doc-{i:02d}.pdf"
        shutil.copy(f"{FX}/five-pages.pdf", p)
        files.append(p)
    launch(settle=3)
    r0 = rss_mb()
    for i in range(0, 30, 5):
        sh(["open", "-a", APP, *files[i:i + 5]])
        time.sleep(3)
    time.sleep(5)
    r1 = rss_mb()
    txt = axdump("many-tabs")
    seen = sum(1 for f in files if os.path.basename(f) in txt)
    s = shot("many-tabs")
    quit_app()
    launch(settle=6)
    txt2 = axdump("many-tabs-restored")
    restored = sum(1 for f in files if os.path.basename(f) in txt2)
    s2 = shot("many-tabs-restored")
    record("T5.4 many tabs", "pass" if seen == 30 else "fail",
           f"tabs seen {seen}/30, RSS {r0} → {r1} MB, restored after relaunch {restored}/30", shots=[s, s2])
    quit_app()


@case("T5.5 low memory")
def t5_5():
    reset_state({"theme": "light"})
    launch(f"{FX}/many-pages.pdf", settle=4)
    p = subprocess.Popen(["sudo", "memory_pressure", "-S", "-l", "critical"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(15)
    sh(["open", "-a", APP, f"{FX}/heavy-vector.pdf"])
    time.sleep(8)
    alive = bool(pids())
    s = shot("low-memory") if alive else None
    p.terminate()
    record("T5.5 low memory", "pass" if alive else "fail", f"alive under critical memory pressure: {alive}", shot=s, rss=rss_mb())
    quit_app()


@case("T5.7 network use")
def t5_7():
    reset_state({"theme": "light"})
    launch(f"{FX}/page.html", settle=5)
    sh(["open", "-a", APP, f"{FX}/links.pdf", f"{FX}/five-pages.pdf"])
    conns = []
    for _ in range(10):
        p = pids()
        if p:
            _, out = sh(["lsof", "-nP", "-a", "-i", "-p", ",".join(map(str, p))])
            conns += [l for l in out.splitlines()[1:] if l.strip()]
        _, wk = sh("lsof -nP -i | grep -i -E 'com.apple.WebKit|WebContent|Networking' || true")
        conns += [l for l in wk.splitlines() if l.strip()]
        time.sleep(1)
    uniq = sorted(set(conns))
    record("T5.7 network use", "pass" if not uniq else "fail",
           "no sockets from the app or its WebKit processes" if not uniq else f"{len(uniq)} socket lines", lines=uniq[:40])
    quit_app()


@case("T5.8 locale en-IN")
def t5_8():
    ev = {}
    for loc in ["en_IN", "de_DE", "ta_IN"]:
        sh(["defaults", "write", "-g", "AppleLocale", loc])
        reset_state({"theme": "light"})
        launch(f"{FX}/sample.xlsx", settle=5)
        ev[loc] = {"shot": shot("locale-" + loc)}
        txt = axdump("locale-" + loc)
        ev[loc]["status_texts"] = [l.strip()[:160] for l in txt.splitlines() if re.search(r"\d{1,2}:\d{2}:\d{2}", l)][:3]
        ev[loc]["numbers"] = [l.strip()[:160] for l in txt.splitlines() if "1234" in l or "1,234" in l or "1.234" in l][:4]
        quit_app()
    sh(["defaults", "delete", "-g", "AppleLocale"])
    record("T5.8 locale", "info", "en_IN, de_DE, ta_IN — see texts", **ev)


@case("T5.9 fresh, upgrade, corrupt, read-only")
def t5_9():
    ev = {}
    # upgrade: settings from a previous build (theme dark, ui-scale 125, recents pointing at a real file)
    reset_state({"theme": "dark", "ui-scale": "125"})
    launch(settle=5)
    ev["upgrade"] = {"shot": shot("upgrade-dark-125"), "settings_after": read_settings()}
    quit_app()
    # corrupt settings.json
    reset_state()
    os.makedirs(STATE, exist_ok=True)
    open(f"{STATE}/settings.json", "w").write("{ not json")
    launch(settle=5)
    ev["corrupt"] = {"alive": bool(pids()), "shot": shot("corrupt-settings"), "file_after": open(f"{STATE}/settings.json").read()[:200]}
    quit_app()
    # read-only state folder
    reset_state({"theme": "light"})
    os.chmod(STATE, 0o500)
    sh(["open", "-a", APP, f"{FX}/five-pages.pdf"])
    w = window_up(20)
    time.sleep(4)
    ev["readonly"] = {"window": bool(w), "alive": bool(pids()), "shot": shot("readonly-state") if pids() else None}
    quit_app()
    os.chmod(STATE, 0o700)
    # fresh user: nothing at all
    reset_state()
    launch(settle=5)
    txt = axdump("fresh-home")
    ev["fresh"] = {"shot": shot("fresh-home"), "sample_recents_present": "discharge-summary" in txt or "lab-report" in txt}
    quit_app()
    ok = ev["corrupt"]["alive"] and ev["readonly"]["alive"] and not ev["fresh"]["sample_recents_present"]
    record("T5.9 fresh, upgrade, corrupt, read-only", "pass" if ok else "fail",
           f"corrupt alive={ev['corrupt']['alive']}, read-only alive={ev['readonly']['alive']}, "
           f"sample recents on fresh install={ev['fresh']['sample_recents_present']}", **ev)


@case("T4.15 folders")
def t4_15():
    reset_state({"theme": "light"})
    marker = "/tmp/chvd-t415-marker"
    open(marker, "w").write("x")
    time.sleep(1)
    launch(f"{FX}/five-pages.pdf", settle=5)
    quit_app()
    _, newer = sh(f"find {HOME}/Library {HOME}/Documents {HOME}/.config /tmp -newer {marker} -type f 2>/dev/null | grep -v -E '/Library/(Caches/com.apple|Logs/DiagnosticReports|Biome|Daemon|Metadata|Group Containers|Containers/com.apple)|/runner/work/|/actions-runner/|/_diag/|chvd-print|/\\.Trash' | head -80", timeout=180)
    in_config = os.path.exists(f"{HOME}/.config/Chuvadi")
    record("T4.15 folders", "pass" if not in_config else "fail",
           f"~/.config/Chuvadi exists={in_config}; files written during a launch listed", files=newer.splitlines())


@case("T3.3b HiDPI")
def t3_3b():
    rc, out = drive("displays", "--hidpi")
    ev = {"displays": out}
    if rc == 0 and "ok" in out:
        time.sleep(3)
        for th in ["light", "dark"]:
            reset_state({"theme": th})
            launch(f"{FX}/five-pages.pdf", settle=4)
            ev[th] = shot(f"hidpi-{th}-reader")
            quit_app()
    record("T3.3b HiDPI", "info" if rc == 0 else "blocked", out.splitlines()[-1] if out else "no output", **ev)


def main():
    _, trust = drive("trust")
    record("env", "info", trust.replace("\n", "; "), sw=sh("sw_vers")[1], arch=sh("uname -m")[1],
           cpu=sh("sysctl -n machdep.cpu.brand_string")[1], displays=drive("displays")[1])
    t1_6()
    t2(A.runs)
    t3_7()
    t4_14()
    t4_12()
    t4_7()
    t4_8()
    if A.suite == "full":
        t3_1()
        t3_2()
        t3_3()
        t3_5()
        t4_1()
        t4_9()
        t4_15()
        t5_1()
        t5_3()
        t5_4()
        t5_7()
        t5_8()
        t5_9()
        t3_3b()
        t5_5()
    quit_app()
    log("done")


main()
