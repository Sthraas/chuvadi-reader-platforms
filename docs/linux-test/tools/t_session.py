# D-194 on Linux (build log 62): a sign-out or shutdown with unsaved work is held and asked about.
# Linux Test's own check, with its own stand-in for the desktop (fake_desktop.py) on a private session bus.
# Usage: t_session.py <work dir> <mark-rot.pdf> <part: portal|stale|ending|gnome|fallback|refused|empty|nobus|deadbus>
import helpers as h, json, hashlib, shutil, tempfile
from lt_base import *
WORK, SRC, PART = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORK, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def P(*x): print(*x, flush=True)
def fresh(*names):
    out = []
    for n in names:
        p = os.path.join(WORK, n); shutil.copyfile(SRC, p); out.append(p)
    return out
DISP = {'portal': 71, 'stale': 72, 'ending': 73, 'gnome': 74, 'fallback': 75, 'refused': 76, 'empty': 77, 'nobus': 78, 'deadbus': 79, 'refusedgnome': 80, 'stalegnome': 81, 'kinds': 82}[PART]
a = App(APP, EV + f"/session-{PART}", display=f":{DISP}"); h.bind(a); a.start_display()
LOG = os.path.join(a.out, "desktop.jsonl")
if os.path.exists(LOG): os.remove(LOG)
extra = []
# A private bus with no service files, so nothing real (xdg-desktop-portal) can be started on it.
if PART in ("portal", "stale", "stalegnome", "kinds", "ending", "gnome", "fallback", "refused", "refusedgnome", "empty"):
    conf = os.path.join(a.out, "bus.conf")
    open(conf, "w").write("<busconfig><type>session</type><listen>unix:tmpdir=/tmp</listen><auth>EXTERNAL</auth>"
                          "<policy context='default'><allow send_destination='*' eavesdrop='true'/><allow eavesdrop='true'/><allow own='*'/></policy></busconfig>")
    out = subprocess.run(["dbus-daemon", "--config-file=" + conf, "--fork", "--print-address=1", "--print-pid=1"], capture_output=True, text=True, check=True).stdout.split()
    BUS, BUSPID = out[0], int(out[1]); a.env["DBUS_SESSION_BUS_ADDRESS"] = BUS
    mode = {"stale": "portal", "ending": "portal", "stalegnome": "gnome", "kinds": "portal"}.get(PART, PART)
    if mode != "empty":
        extra.append(subprocess.Popen(["/usr/bin/python3.12", os.path.join(HERE, "fake_desktop.py"), mode, LOG], env=dict(os.environ, DBUS_SESSION_BUS_ADDRESS=BUS)))
        for _ in range(50):
            if os.path.exists(LOG): break
            time.sleep(0.1)
elif PART == "nobus":
    a.env.pop("DBUS_SESSION_BUS_ADDRESS", None)      # and XDG_RUNTIME_DIR is an empty folder: no bus socket
elif PART == "deadbus":
    a.env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/tmp/lt-no-such-bus-socket"
def events(): return [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
def names(since=0): return [e["ev"] + (str(e.get("phase", "")) if e["ev"] == "notice" else "") for e in events()[since:]]
def notice(phase=2):
    subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop", "--object-path", "/org/freedesktop/portal/desktop", "--method", "lt.Ctl.State", str(phase)],
                   env=dict(os.environ, DBUS_SESSION_BUS_ADDRESS=BUS), capture_output=True, check=True)
held = lambda: int(a.send("session-hold"))
shapes = lambda: a.js("return document.querySelectorAll('.mk-layer .mk-shape').length")
tabs = lambda: a.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())")
card = lambda: a.js("var c=document.querySelector('.closeq'); return c ? {title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\\s+/g,' ').trim(), buttons: [...c.querySelectorAll('button')].map(b => b.textContent.trim())} : null")
ncards = lambda: a.js("return document.querySelectorAll('.closeq').length")
def open_tab(path):
    n = os.path.basename(path); a.send("open " + path, timeout=15)
    a.wait(lambda: a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{n}')"), 30, n); time.sleep(2)
def mark_mode():
    if not a.js("return [...document.querySelectorAll('.srail button')].some(b => b.offsetParent && (b.getAttribute('aria-label')||'').startsWith('Rectangle'))"):
        a.click(".lb-mode", 1); time.sleep(1.3)
def draw(dx=0):
    mark_mode(); h.click_label(".srail", "Rectangle"); h.focus_main()
    pr = a.js("var r=document.querySelector('.rpage-wrap[data-page=\"0\"] .rpage').getBoundingClientRect(); return [r.left,r.top,r.width,r.height]")
    x, y = int(pr[0] + 120 + dx), int(pr[1] + 140); n = shapes()
    a.xdo("mousemove", str(x), str(y)); a.xdo("mousedown", "1")
    for i in range(1, 9): a.xdo("mousemove", str(x + 14 * i), str(y + 9 * i)); time.sleep(0.04)
    a.xdo("mouseup", "1"); time.sleep(0.7); a.key("Escape"); time.sleep(0.3)
    assert shapes() == n + 1, "rectangle not drawn"
def close_x(name):
    a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.querySelector('.rtab-x').click(); return 1"); time.sleep(1.2)
def answer(label):
    try: ok = a.js(f"var b=[...document.querySelectorAll('.closeq button')].find(b => b.textContent.trim() === '{label}'); if (!b) return false; b.click(); return true")
    except Exception: ok = None   # the window can close before the reply comes back
    time.sleep(1.5); return ok
def alive(): return a.proc.poll() is None
def gap(first, second, since=0):
    ev = events()[since:]; t1 = [e["t"] for e in ev if e["ev"] == first]; t2 = [e["t"] for e in ev if e["ev"] == second]
    return (t2[0] - t1[0]) if t1 and t2 else None
try:
    t0 = time.time(); a.launch(); P(f"START ({PART}): app up in {time.time() - t0:.1f} s | alive: {alive()} | hold state: {held()}")
    time.sleep(1.5)
    if PART == "portal":
        ev = events(); mon = [e for e in ev if e["ev"] == "monitor"]
        P("AT START calls seen by the desktop:", names(), "| monitor asked for:", json.dumps(mon[0]["options"]) if mon else None, "| card after the 'running' state:", card())
        fa, fc = fresh("s-mark.pdf", "s-clean.pdf"); open_tab(fc)
        n = len(events()); notice(); time.sleep(1.5)
        P("CLEAN notice with nothing unsaved ->", names(n), "| answered after", gap("notice", "query-end-response", n), "ms | card:", card(), "| hold:", held(), "| alive:", alive())
        open_tab(fa); draw(); P("MARK drawn: hold state", held(), "| Inhibit calls so far:", sum(1 for e in events() if e["ev"] == "inhibit"), "(from patch 32 the lock is taken when work becomes unsaved)")
        n = len(events()); notice(); time.sleep(2); ev = events()[n:]; inh = [e for e in ev if e["ev"] == "inhibit"]
        P("UNSAVED notice ->", names(n), "| Inhibit:", json.dumps({k: inh[0][k] for k in ("window", "flags", "options")}) if inh else None)
        P("  lock asked for", gap("notice", "inhibit", n), "ms after the notice, answer sent", gap("notice", "query-end-response", n), "ms after | hold:", held())
        P("  the window asks:", json.dumps(card()), "| alive:", alive())
        n = len(events()); notice(); time.sleep(1.5); P("SECOND notice while the card is open ->", names(n), "| cards:", ncards(), "| hold:", held())
        answer("Cancel"); P("Cancel -> card gone:", card() is None, "| mark kept:", shapes() == 1, "| hold:", held(), "| lock given up:", "request-close" in names(), "| alive:", alive())
        a.key("Escape"); n = len(events()); notice(); time.sleep(1.5)
        P("THIRD notice after Cancel ->", names(n), "| asks again:", card() is not None, "| second Inhibit:", "inhibit" in names(n))
        a.key("Escape"); time.sleep(1); P("  Escape on the card -> gone:", card() is None, "| hold:", held(), "| alive:", alive())
        n = len(events()); notice(); time.sleep(1.5); answer("Save"); time.sleep(3)
        P("FOURTH notice, Save -> app exited:", not alive(), "code", a.proc.poll(), "| file written:", sha(fa) != sha(SRC), "| clean file untouched:", sha(fc) == sha(SRC), "| desktop saw:", names(n), "| OUTFILE", fa)
    if PART in ("stale", "stalegnome"):
        fa, fc = fresh("st-mark.pdf", "st-clean.pdf"); open_tab(fc); open_tab(fa); draw()
        P("MARK drawn -> hold:", held(), "| desktop saw:", names())
        if PART == "stale": notice()
        else: a.send("session-end")
        time.sleep(2); P("UNSAVED notice -> card:", card() is not None, "| hold:", held()); answer("Cancel")
        close_x("st-mark.pdf"); c = card(); answer("Discard"); P("Then the marked tab closed with Discard (asked:", c is not None, ") -> tabs:", tabs(), "| file byte-identical:", sha(fa) == sha(SRC))
        time.sleep(1); P("  desktop saw so far:", names()); P("NOTHING UNSAVED NOW: hold state", held(), "| lock given up:", ("request-close" in names()) or ("gsm-uninhibit" in names()), "(2 and False = the desktop still lists Chuvadi as having unsaved work)")
        draw(dx=60); P("A NEW MARK -> hold:", held(), "| desktop saw:", names()[-2:])
        a.js("var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('st-clean')); t.click(); return 1"); time.sleep(1)
        n = len(events())
        if PART == "stale": notice()
        else: a.send("session-end")
        time.sleep(1.5)
        P("Next notice ->", names(n), "| card:", card(), "| hold:", held(), "| alive:", alive())
    if PART == "kinds":
        # Patch 32: bookmark edits, redaction areas and Arrange desks are unsaved work too, so they take the lock.
        def key(k): h.focus_main(); a.xdo("key", k); time.sleep(0.7)
        def lock(): ev = names(); return held(), (ev[-1] if ev else None)
        def deskclick():
            r = a.js("var e=document.querySelector('.rdesk') || document.querySelector('.mk-layer') || document.querySelector('main'); var r=e.getBoundingClientRect(); return [r.left, r.top]")
            a.xdo("mousemove", str(int(r[0] + 20)), str(int(r[1] + 20))); a.xdo("click", "1"); time.sleep(0.3)
        fb, fr, fx, fy = fresh("k-bm.pdf", "k-rd.pdf", "k-ar1.pdf", "k-ar2.pdf"); open_tab(fb)
        key("ctrl+b"); a.xdo("key", "Return"); time.sleep(1); P("BOOKMARK added -> hold, last call:", lock())
        close_x("k-bm.pdf"); answer("Discard"); time.sleep(1); P("  Discard -> hold, last call:", lock())
        open_tab(fr); deskclick(); key("4"); key("r"); time.sleep(1)
        if not a.js("return !!document.querySelector('.mk-layer.drawmode')"):
            P("REDACTION AREA: redaction is held on this build (patch 33), so not drawn"); deskclick(); key("1"); time.sleep(1)
        else:
            L = a.js("var r=document.querySelector('.mk-layer.drawmode').getBoundingClientRect(); return [r.left, r.top, r.width]")
            x, y = int(L[0] + L[2] * 0.3), int(max(L[1], 140) + 60); a.xdo("mousemove", str(x), str(y)); a.xdo("mousedown", "1")
            for i in range(1, 6): a.xdo("mousemove", str(x + 28 * i), str(y + 7 * i)); time.sleep(0.04)
            a.xdo("mouseup", "1"); time.sleep(1); P("REDACTION AREA drawn -> hold, last call:", lock())
            deskclick(); key("1"); time.sleep(1); close_x("k-rd.pdf"); answer("Discard"); time.sleep(1); P("  Discard -> hold, last call:", lock())
        open_tab(fx); open_tab(fy); deskclick(); key("3"); time.sleep(2.5)
        a.js("[...document.querySelectorAll('.shelf-tool')].find(b => (b.title||'').startsWith('Weave')).click(); return 1"); time.sleep(0.8)
        a.js("var s=document.querySelectorAll('.shelf-interleave select'); s[1].selectedIndex = 1; s[1].dispatchEvent(new Event('change')); return 1"); time.sleep(0.6)
        a.js("document.querySelector('.shelf-interleave .bt-prime').click(); return 1"); time.sleep(2.5); P("ARRANGE desk built -> hold, last call:", lock())
        n = len(events()); notice(); time.sleep(2); c = card(); P("  notice -> desktop saw:", names(n), "| card:", c and c["title"])
        answer("Discard"); time.sleep(3); P("  Discard -> app exited:", not alive(), "code", a.proc.poll(), "| desktop saw:", names(n), "| files untouched:", all(sha(f) == sha(SRC) for f in (fb, fr, fx, fy)))
    if PART == "ending":
        fa, = fresh("e-mark.pdf"); open_tab(fa); draw(); n = len(events()); notice(3); time.sleep(2)
        P("STATE 3 (ending, no question) with a mark unsaved ->", names(n), "| card:", card(), "| hold:", held(), "| alive:", alive())
    if PART in ("gnome", "fallback", "refused", "refusedgnome", "empty", "nobus", "deadbus"):
        fa, = fresh(f"{PART}-mark.pdf"); open_tab(fa); draw()
        P("MARK drawn: hold state", held(), "| desktop saw:", names())
        n = len(events()); a.send("session-end"); time.sleep(2); ev = events()[n:]
        P("SESSION END (the driver's stand-in for the notice) ->", names(n), "| hold:", held(), "| card:", json.dumps(card()), "| alive:", alive())
        for e in ev:
            if e["ev"] in ("gsm-inhibit", "inhibit"): P("  ", json.dumps({k: v for k, v in e.items() if k not in ("t", "sender")}))
        answer("Cancel"); P("Cancel -> mark kept:", shapes() == 1, "| hold:", held(), "| alive:", alive())
        n = len(events()); a.send("session-end"); time.sleep(2); c2 = card(); up = alive(); P("Again -> asks again:", c2 is not None, "| alive before the answer:", up, "| hold:", held())
        try: answer("Discard")
        except Exception: pass    # the window can close before the click's reply comes back to the driver
        time.sleep(3)
        P("  Discard -> app exited:", not alive(), "code", a.proc.poll(), "| file byte-identical:", sha(fa) == sha(SRC), "| desktop saw:", names(n))
    errs = open(a.log_path, errors="replace").read()
    P("LOG: 'Chuvadi error' lines:", errs.count("Chuvadi error"), "| GLib criticals:", errs.count("CRITICAL"), "| warnings mentioning dbus:", sum(1 for l in errs.splitlines() if "dbus" in l.lower() or "GDBus" in l))
finally:
    try: a.stop()
    except Exception: pass
    for p in extra: p.terminate()
    try: os.kill(BUSPID, 15)
    except Exception: pass
