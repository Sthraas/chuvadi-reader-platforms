# Patch 32 on Linux, Linux Test's own check with real mouse and keyboard (xdotool) in the real window:
#   bookmarks   bookmark edits stay with the tab and are asked about on close (Save bookmarks / Discard / Cancel)
#   redact      ten redaction areas drawn in a row are all kept, no text gets selected; they stay with the file
#               through Read and Home; closing asks Discard / Cancel only, focus on Cancel; also at app close
#   arrange     a new desk in Arrange is unsaved: closing the app asks first, before marks. From patch 34 (D-203)
#               "Keep what you arranged?": Save keeps the desks for the next start with no file dialog, Discard
#               clears them; checked across real restarts (older heads: Save session… with a file dialog)
#   find        the current Find match never rests under the Find bar (fixtures/find-top.pdf, word "topmark")
#   findfoot    AT-24 (patch 34): a match at the foot of a page taller than the view (fixtures/find-page3-foot.pdf,
#               "zephyrine" only at the foot of page 3; pass it as <find-top.pdf>): Fit width, continuous and Single
#               page, Find five times each: the match is on screen, on page 3, inside its own page
# Usage: t_patch32.py <work dir> <a.pdf (text)> <find-top.pdf> <part>
import helpers as h, json, hashlib, shutil
from lt_base import *
WORK, SRC, FIND, PART = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(WORK, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def P(*x): print(*x, flush=True)
def fresh(*names):
    out = []
    for n in names:
        p = os.path.join(WORK, n); shutil.copyfile(SRC, p); out.append(p)
    return out
a = App(APP, EV + f"/patch32-{PART}", display=f":{ {'bookmarks': 61, 'redact': 62, 'arrange': 63, 'find': 64, 'findfoot': 65}[PART] }"); h.bind(a); a.start_display()
tabs = lambda: a.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())")
card = lambda: a.js("var c=document.querySelector('.closeq'); return c ? {title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\\s+/g,' ').trim(), buttons: [...c.querySelectorAll('button')].map(b => b.textContent.trim()), focus: (document.activeElement||{}).textContent ? document.activeElement.textContent.trim() : null} : null")
def wait_pages(t=30): a.wait(lambda: a.js("return document.querySelectorAll('.rdesk .rpage svg').length > 0"), t, "pages")
def open_tab(path):
    n = os.path.basename(path); a.send("open " + path, timeout=15)
    a.wait(lambda: a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{n}')"), 30, n); wait_pages(); time.sleep(1.5)
def show(name):
    a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.click(); return 1"); time.sleep(1.2); wait_pages(); time.sleep(0.6)
def close_x(name):
    a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.querySelector('.rtab-x').click(); return 1"); time.sleep(1.2)
def answer(label):
    try:
        ok = a.js(f"var b=[...document.querySelectorAll('.closeq button')].find(b => b.textContent.trim().startsWith('{label}')); if (!b) return false; b.click(); return true")
    except Exception: ok = None   # the window can close before the reply
    time.sleep(1.5); return ok
def key(k): h.focus_main(); a.xdo("key", k); time.sleep(0.7)
def alive(): return a.proc.poll() is None
def desk_click():
    r = a.js("var e=document.querySelector('.rdesk') || document.querySelector('.mk-layer') || document.querySelector('main'); var r=e.getBoundingClientRect(); return [r.left, r.top]")
    a.xdo("mousemove", str(int(r[0] + 20)), str(int(r[1] + 20))); a.xdo("click", "1"); time.sleep(0.3)
def to_protect():
    desk_click(); key("4"); key("r")
    a.wait(lambda: a.js("return !!document.querySelector('.mk-layer.drawmode')"), 20, "protect draw mode"); time.sleep(0.8)
boxes = lambda: a.js("return document.querySelectorAll('.mk-box-x').length")
def outline_titles(path):
    out = subprocess.run(["python3", "-c", "import pikepdf,sys\np=pikepdf.open(sys.argv[1])\nwith p.open_outline() as o: print([i.title for i in o.root])", path], capture_output=True, text=True)
    return (out.stdout or out.stderr).strip()[:200]
try:
    a.launch()
    if PART == "bookmarks":
        fa, fb = fresh("bm-a.pdf", "bm-b.pdf"); open_tab(fb); open_tab(fa); before = sha(fa)
        rows = lambda: a.js("return document.querySelectorAll('.bm-row').length")
        key("ctrl+b"); a.xdo("key", "Return"); time.sleep(0.6); n0 = rows()
        P("BOOKMARK added with Ctrl B, Enter -> rows in the panel:", n0, "| file untouched:", sha(fa) == before, "| hold state:", a.send("session-hold"))
        show("bm-b.pdf"); show("bm-a.pdf")
        if not rows(): key("ctrl+shift+o")
        P("  after another tab and back -> rows:", rows())
        a.js("Blazor.navigateTo('/'); return 1"); time.sleep(1.2); show("bm-a.pdf")
        if not rows(): key("ctrl+shift+o")
        drawer = lambda: a.js("var d=document.querySelector('.mdrawer'); if(!d) return 'closed'; var t=d.querySelector('.mdrawer-tab.on'); return t ? t.textContent.trim() : 'open'")
        P("  after Home and back -> rows:", rows(), "| drawer:", drawer())
        if not rows():
            if drawer() == "closed":
                try: a.send("invoke r.pages")
                except Exception as e: P("    invoke r.pages:", str(e)[:80])
                time.sleep(0.8)
            a.js("var t=[...document.querySelectorAll('.mdrawer-tab')].find(b => b.textContent.trim()==='Outline'); if (t) t.click(); return 1"); time.sleep(0.8)
            P("    on the drawer's Outline tab -> rows:", rows(), "| drawer:", drawer())
        close_x("bm-a.pdf"); c = card(); P("CLOSE the tab asks:", json.dumps(c))
        answer("Cancel"); P("  Cancel -> tab kept:", "bm-a.pdf" in tabs(), "| file untouched:", sha(fa) == before, "| rows:", rows())
        close_x("bm-a.pdf"); answer("Discard"); P("  Discard -> tab closed:", "bm-a.pdf" not in tabs(), "| file byte-identical:", sha(fa) == before, "| hold:", a.send("session-hold"))
        open_tab(fa); key("ctrl+b"); a.xdo("key", "Return"); time.sleep(0.6); P("REOPENED, a new bookmark -> rows:", rows())
        close_x("bm-a.pdf"); answer("Save bookmarks"); time.sleep(1.5)
        P("  Save bookmarks -> tab closed:", "bm-a.pdf" not in tabs(), "| file changed:", sha(fa) != before, "| outline in the saved file:", outline_titles(fa), "| other file untouched:", sha(fb) == sha(SRC))
        P("  opens again in qpdf --check:", subprocess.run(["qpdf", "--check", fa], capture_output=True, text=True).stdout.strip().splitlines()[-1:])
    if PART == "redact":
        fa, fb = fresh("rd-a.pdf", "rd-b.pdf"); open_tab(fb); open_tab(fa); before = sha(fa)
        to_protect()
        a.js("window.__ev=[]; for (const t of ['dragstart','selectstart','pointercancel']) document.addEventListener(t, e => window.__ev.push(t), true); return 1")
        L = a.js("var r=document.querySelector('.mk-layer.drawmode').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]")
        for i in range(10):
            x, y = int(L[0] + L[2] * 0.3), int(max(L[1], 140) + 30 + i * 55)
            a.xdo("mousemove", str(x), str(y)); a.xdo("mousedown", "1")
            for s in range(1, 6): a.xdo("mousemove", str(x + 28 * s), str(y + 7 * s)); time.sleep(0.04)
            a.xdo("mouseup", "1"); time.sleep(0.5)
        P("TEN AREAS drawn with the mouse -> kept:", boxes(), "of 10 | text selected:", repr(a.js("return String(getSelection())"))[:60], "| drag or select events:", a.js("return window.__ev"), "| hold:", a.send("session-hold"))
        desk_click(); key("1"); wait_pages(); time.sleep(0.6); to_protect(); P("  after Read and back to Protect -> areas:", boxes())
        a.js("Blazor.navigateTo('/'); return 1"); time.sleep(1); show("rd-a.pdf"); to_protect(); P("  after Home and back -> areas:", boxes())
        desk_click(); key("1"); wait_pages(); time.sleep(0.5)
        close_x("rd-a.pdf"); c = card(); P("CLOSE the tab asks:", json.dumps(c))
        answer("Cancel"); P("  Cancel -> tab kept:", "rd-a.pdf" in tabs())
        key("alt+F4"); time.sleep(1); c = card(); P("APP CLOSE (Alt F4) asks:", json.dumps(c) if c else None, "| alive:", alive())
        answer("Cancel"); P("  Cancel -> alive:", alive(), "| tabs:", tabs())
        close_x("rd-a.pdf"); answer("Discard"); P("  Discard on the tab -> closed:", "rd-a.pdf" not in tabs(), "| file byte-identical:", sha(fa) == before, "| hold:", a.send("session-hold"))
    if PART == "arrange":
        fa, fb, fm = fresh("ar-a.pdf", "ar-b.pdf", "ar-mark.pdf"); open_tab(fa); open_tab(fb)
        key("alt+F4"); time.sleep(1.5); up = alive(); P("NOTHING UNSAVED, Alt F4 -> card:", card() if up else None, "| alive:", up, "(closing at once is right: nothing to lose)")
        if not alive():
            a.launch(); open_tab(fa); open_tab(fb)
        desk_click(); key("3"); time.sleep(2.5)
        P("ARRANGE: shelf files:", a.js("return [...document.querySelectorAll('.shelf-srcname')].map(e => e.textContent.trim())"), "| hold:", a.send("session-hold"))
        a.js("[...document.querySelectorAll('.shelf-tool')].find(b => (b.title||'').startsWith('Weave')).click(); return 1"); time.sleep(0.8)
        sel = a.js("var s=document.querySelectorAll('.shelf-interleave select'); if (s.length < 2) return [s.length]; s[1].selectedIndex = 1; s[1].dispatchEvent(new Event('change')); return [s[0].value, s[1].value]"); time.sleep(0.6)
        a.js("document.querySelector('.shelf-interleave .bt-prime').click(); return 1"); time.sleep(2.5)
        P("  interleaved desk built (selects", sel, ") -> desks:", a.js("return document.querySelectorAll('.desk, .bench-desk').length"), "| hold:", a.send("session-hold"))
        key("alt+F4"); time.sleep(1.5); c = card(); P("APP CLOSE asks:", json.dumps(c), "| page on screen:", a.js("return location.pathname"), "| alive:", alive())
        answer("Cancel"); P("  Cancel -> alive:", alive(), "| card:", card())
        a.js("Blazor.navigateTo('/reader'); return 1"); time.sleep(1.5); open_tab(fm)
        if not a.js("return [...document.querySelectorAll('.srail button')].some(b => b.offsetParent && (b.getAttribute('aria-label')||'').startsWith('Rectangle'))"): desk_click(); key("2")
        h.click_label(".srail", "Rectangle"); h.focus_main()
        pr = a.js("var r=document.querySelector('.rpage-wrap[data-page=\"0\"] .rpage').getBoundingClientRect(); return [r.left,r.top]")
        x, y = int(pr[0] + 120), int(pr[1] + 140); a.xdo("mousemove", str(x), str(y)); a.xdo("mousedown", "1")
        for i in range(1, 9): a.xdo("mousemove", str(x + 14 * i), str(y + 9 * i)); time.sleep(0.04)
        a.xdo("mouseup", "1"); time.sleep(0.7); a.key("Escape"); time.sleep(0.3)
        P("A MARK drawn as well:", a.js("return document.querySelectorAll('.mk-layer .mk-shape').length"))
        key("alt+F4"); time.sleep(1.5); c1 = card(); answer("Discard"); c2 = card()
        P("BOTH UNSAVED, Alt F4 -> first:", c1 and c1["title"], "| after Discard, next:", json.dumps(c2))
        answer("Cancel"); time.sleep(1); P("  Cancel on the file -> alive:", alive(), "| mark kept:", a.js("return document.querySelectorAll('.mk-layer .mk-shape').length"), "| hold:", a.send("session-hold"))
        key("alt+F4"); time.sleep(1.5); c = card(); P("AGAIN -> first:", c and c["title"])
        def kept():
            for d, _, fs in os.walk(a.home):
                if "arrange-kept.json" in fs: p = os.path.join(d, "arrange-kept.json"); return os.path.relpath(p, a.home), os.path.getsize(p)
            return None
        def dlg(): return subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "Save"], env=a.env, capture_output=True, text=True).stdout.split()
        if c and c["title"].startswith("Keep"):   # patch 34, D-203
            P("  card:", json.dumps(c))
            answer("Save"); time.sleep(2)
            c = card(); P("  Save -> kept:", kept(), "| a file dialog opened:", bool(dlg()), "| next:", c and c["title"], "| alive:", alive())
            answer("Discard"); time.sleep(3); P("  Discard on the file -> app exited:", not alive(), "code", a.proc.poll(), "| ar-mark byte-identical:", sha(fm) == sha(SRC), "| ar-a, ar-b untouched:", sha(fa) == sha(SRC) and sha(fb) == sha(SRC))
            def bench():
                a.js("Blazor.navigateTo('/bench'); return 1"); time.sleep(3)
                return a.js("return {desks: document.querySelectorAll('.desk, .bench-desk').length, pages: document.querySelectorAll('.desk .dpage, .bench-desk .dpage, .desk [data-page], .desk img, .desk svg').length}")
            a.launch(); time.sleep(4); P("NEXT START -> Arrange:", bench(), "| hold:", a.send("session-hold"), "| kept:", kept())
            key("alt+F4"); time.sleep(2); up = alive(); P("  unchanged, Alt F4 -> card:", (card() or {}).get("title") if up else None, "| alive:", up)
            if up: answer("Cancel")
            else: a.launch(); time.sleep(4); bench()
            a.js("Blazor.navigateTo('/reader'); return 1"); time.sleep(1.5); open_tab(fa); open_tab(fb); desk_click(); key("3"); time.sleep(2.5)
            a.js("[...document.querySelectorAll('.shelf-tool')].find(b => (b.title||'').startsWith('Weave')).click(); return 1"); time.sleep(0.8)
            a.js("var s=document.querySelectorAll('.shelf-interleave select'); if (s.length >= 2) { s[1].selectedIndex = 1; s[1].dispatchEvent(new Event('change')); } return 1"); time.sleep(0.6)
            a.js("document.querySelector('.shelf-interleave .bt-prime').click(); return 1"); time.sleep(2.5)
            P("  changed again -> Arrange:", a.js("return document.querySelectorAll('.desk, .bench-desk').length"), "desks | hold:", a.send("session-hold"))
            key("alt+F4"); time.sleep(2); up = alive(); c = card() if up else None; P("  Alt F4 -> card:", c and c["title"], "| alive:", up)
            if c: answer("Discard"); time.sleep(3)
            P("  Discard -> app exited:", not alive(), "| kept:", kept())
            a.launch(); time.sleep(4); P("NEXT START after Discard -> Arrange:", bench(), "| kept:", kept())
        else:
            out = os.path.join(WORK, "ar-session.chvbench"); [os.remove(out) for _ in [0] if os.path.exists(out)]
            answer("Save session")
            try: h.file_dialog("Save", out); time.sleep(2.5)
            except Exception as e: P("  session dialog problem:", str(e)[:120])
            c = card(); P("  Save session -> written:", [f for f in os.listdir(WORK) if f.startswith("ar-session")], "| next:", c and c["title"], "| alive:", alive())
            answer("Discard"); time.sleep(3); P("  Discard on the file -> app exited:", not alive(), "code", a.proc.poll(), "| ar-mark byte-identical:", sha(fm) == sha(SRC), "| ar-a, ar-b untouched:", sha(fa) == sha(SRC) and sha(fb) == sha(SRC))
    if PART == "find":
        dst = os.path.join(WORK, "find-top.pdf"); shutil.copyfile(FIND, dst); open_tab(dst)
        key("ctrl+f"); a.xdo("type", "--delay", "60", "topmark"); a.xdo("key", "Return"); time.sleep(3)
        seen = bad = 0; where = []
        probe = """var h=document.querySelector('.rfind-hl.cur'), d=document.querySelector('.rdesk'), f=document.querySelector('.rfind'); if(!h||!f) return null;
          var a=h.getBoundingClientRect(), c=d.getBoundingClientRect(), q=f.getBoundingClientRect();
          return {page: h.closest('[data-page]').getAttribute('data-page'), vis: a.top >= c.top-1 && a.bottom <= c.bottom+1,
                  under: a.left < q.right && a.right > q.left && a.top < q.bottom && a.bottom > q.top, aside: f.classList.contains('aside'), gap: Math.round(a.top - q.bottom)}"""
        for i in range(16):
            r = a.js(probe)
            if r:
                seen += 1; bad += (not r["vis"]) or r["under"]
                where.append(f"p{r['page']}{'A' if r['aside'] else ''}{'!UNDER' if r['under'] else ''}{'' if r['vis'] else '!OFF'}")
            a.xdo("key", "Return"); time.sleep(1.2)
        P("FIND topmark, 16 steps with Enter -> seen:", seen, "| under the bar or off screen:", bad, "|", " ".join(where))
        P("  file untouched:", sha(dst) == sha(FIND))
    if PART == "findfoot":
        dst = os.path.join(WORK, "find-page3-foot.pdf"); shutil.copyfile(FIND, dst); open_tab(dst)
        probe = """var h=document.querySelector('.rfind-hl.cur'), d=document.querySelector('.rdesk'); if(!h) return null;
          var w=h.closest('.rpage-wrap'), a=h.getBoundingClientRect(), c=d.getBoundingClientRect(), r=w.getBoundingClientRect(), on=null, best=0;
          for (const x of d.querySelectorAll('.rpage-wrap')) { const b=x.getBoundingClientRect(); const v=Math.min(b.bottom,c.bottom)-Math.max(b.top,c.top); if (v>best) {best=v; on=+x.getAttribute('data-page')+1;} }
          return {page: +w.getAttribute('data-page')+1, onScreen: on, vis: a.top >= c.top-1 && a.bottom <= c.bottom+1, inside: a.top >= r.top-1 && a.bottom <= r.bottom+1, taller: Math.round(r.height) > Math.round(c.height)}"""
        for mode in ("Fit width", "Single page"):
            h.click_label(".srail", mode); time.sleep(1.5)
            good, seen = 0, []
            for t in range(5):
                a.js("document.querySelector('.rdesk').scrollTop = 0; return 1"); time.sleep(1.2)
                key("Escape"); key("ctrl+f"); a.xdo("key", "ctrl+a"); a.xdo("type", "--delay", "40", "zephyrine"); a.xdo("key", "Return"); time.sleep(3)
                r = a.js(probe)
                if r and r["page"] == 3 and r["onScreen"] == 3 and r["vis"] and r["inside"]: good += 1
                seen.append("none" if not r else f"{r['onScreen']}{'' if r['vis'] else '(hidden)'}{'' if r['inside'] else '(outside its page)'}")
            P(f"FIND zephyrine, {mode}: on page 3, on screen, inside its page: {good} of 5 | page taller than the view: {r and r['taller']} | pages on screen: {', '.join(seen)}")
        P("  file untouched:", sha(dst) == sha(FIND))
    log = open(a.log_path, errors="replace").read()
    P("LOG: 'Chuvadi error' lines:", log.count("Chuvadi error"), "| GLib criticals:", log.count("CRITICAL"))
finally:
    try: a.stop()
    except Exception: pass
