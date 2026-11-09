# Render re-verification (D-152, patches 14-16): 36a fast paging, 36b close mid-render, 36c CAD time + memory.
# Usage: t_render.py <cad.pdf> <label> [runs]   (Arun's real CAD file is never committed; only numbers are.)
import helpers as h, threading
from lt_base import *
CAD, LABEL = sys.argv[1], sys.argv[2]; RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 1
HEAVY = "/home/claude/heavy10"; GC = os.environ.get("GC") == "1"; FIVE = "/home/claude/lt/five-pages.pdf"

def ping():
    t0 = time.time(); a.js("return 1"); return time.time() - t0
def rendered(i):
    """The page's real drawing: an svg whose viewBox is the page (the 24x24 svg is the loading icon)."""
    return a.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{i}\"]'); return !!w && [...w.querySelectorAll('svg')].some(s=>{{var v=(s.getAttribute('viewBox')||'').split(' '); return +v[2]>100}})")
def icon(i): return a.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{i}\"]'); return !!w && [...w.querySelectorAll('svg')].some(s=>s.getAttribute('viewBox')=='0 0 24 24')")
def page(): return int(a.js("var b=document.querySelector('.tb-pg-box'); return b ? b.value : 0") or 0)
def goto(n): a.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{n}'; b.dispatchEvent(new Event('change')); return 1")
def mem():
    procs = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try: procs[int(pid)] = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[1])
        except OSError: pass
    tree, todo = set(), [a.proc.pid]
    while todo:
        p = todo.pop(); tree.add(p); todo += [c for c, par in procs.items() if par == p and c not in tree]
    def rss(p):
        try: return int(next(l for l in open(f"/proc/{p}/status") if l.startswith("VmRSS")).split()[1]) // 1024
        except (OSError, StopIteration): return 0
    return rss(a.proc.pid), sum(rss(p) for p in tree if p != a.proc.pid)
def open_tab(path):
    n = os.path.basename(path); a.send("open " + path, timeout=15)
    a.wait(lambda: a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{n}')"), 30, n)
def close_tab(): a.js("var x=document.querySelector('.rtab.active .rtab-x'); if (x) x.click(); return 1"); time.sleep(1)
def wait_drawn(i, limit=240):
    """Wait for page i to draw, pinging the page every ~0.1 s; returns (seconds, worst ping)."""
    t0, worst = time.time(), 0
    while not rendered(i):
        worst = max(worst, ping()); time.sleep(0.1)
        if time.time() - t0 > limit: raise AssertionError(f"page {i+1} not drawn in {limit} s")
    return time.time() - t0, worst
def errors(): return [l.strip()[:160] for l in open(a.log_path).read().splitlines() if re.search(r"xception|rror", l) and "a11y" not in l][:5] if os.path.exists(a.log_path) else []
import re

def t36a():
    open_tab(HEAVY + "/big.pdf"); wait_drawn(0); h.focus_main(); pings = []
    for _ in range(6):
        subprocess.run(["xdotool", "key", "--repeat", "25", "--delay", "10", "Next"], env=a.env, capture_output=True); pings.append(ping())
    tk = time.time(); last, since = page(), time.time()
    while time.time() - since < 1.0 and time.time() - tk < 60:
        time.sleep(0.1); p = page()
        if p != last: last, since = p, time.time()
    landed = page(); d, w = wait_drawn(landed - 1)
    print(f"36a PageDown x150: page answers ≤ {max(pings):.2f} s; view settled on p{landed} {since-tk:.1f} s after last key; drawn {d:.2f} s after the 1 s settle window", flush=True)
    # independent angle, no smooth scroll: 40 jumps through the page box 50 ms apart, then time the landed page
    import random; random.seed(7); targets = [random.randint(2, 399) for _ in range(40)]
    for n in targets: goto(n); time.sleep(0.05)
    d, w = wait_drawn(targets[-1] - 1)
    others = sum(1 for n in set(targets[:-1]) if abs(n - targets[-1]) > 3 and rendered(n - 1))
    print(f"36a 40 page-box jumps 50 ms apart: landed p{targets[-1]} drawn {d:.2f} s after the last jump (ping ≤ {w:.2f} s); "
          f"jumped-past pages left drawn: {others}/{len(set(targets[:-1]))}", flush=True)
    goto(400); d, w = wait_drawn(399); print(f"36a jump to 400: drawn in {d:.2f} s", flush=True); close_tab()

def t36b(path, tag):
    out = []
    for i in range(3):
        open_tab(path); mid = not rendered(0); close_tab(); t0 = time.time(); open_tab(FIVE)
        d, w = wait_drawn(0); out.append(f"{'mid' if mid else 'after'}-render → next drawn {time.time()-t0:.2f} s (ping ≤ {w:.2f})")
        close_tab()
    print(f"36b {tag}: " + "; ".join(out) + f"; tabs now {tabs(a)}", flush=True)

def t36c(path, tag):
    base = mem(); t0 = time.time(); open_tab(path); d, worst = wait_drawn(0); first = time.time() - t0; m1 = mem(); times = []
    for n in range(2, 6):
        goto(n); dn, w = wait_drawn(n - 1); worst = max(worst, w); times.append(dn)
    for n in range(4, 0, -1):  # page back: already-drawn sheets
        goto(n); dn, w = wait_drawn(n - 1); worst = max(worst, w)
    m5 = mem(); close_tab(); tc = time.time(); after = {}
    for s in (2, 10, 30, 60):
        time.sleep(max(0, tc + s - time.time())); after[s] = mem()
    print(f"36c {tag}: sheet 1 {first:.2f} s, sheets 2-5 {', '.join(f'{t:.2f}' for t in times)} s; worst page answer {worst:.2f} s; "
          f"memory app/web MB: before {base[0]}/{base[1]}, sheet 1 {m1[0]}/{m1[1]}, 5 sheets {m5[0]}/{m5[1]}, after close "
          + ", ".join(f"+{s}s {v[0]}/{v[1]}" for s, v in after.items()) + (f"; gc verb: {a.send('gc', timeout=60)}" if GC else ""), flush=True)

for r in range(RUNS):
    a = App(APP, EV + f"/render-{LABEL}-{r}", display=":64"); h.bind(a); a.start_display()
    try:
        a.launch(); time.sleep(4)
        if LABEL == "full":
            t36a(); t36b(HEAVY + "/cad.pdf", "stand-in"); t36b(CAD, "real CAD"); t36c(HEAVY + "/cad.pdf", "stand-in, after 36a/b"); t36c(CAD, "real CAD, after the rest")
        else:
            t36c(CAD, f"real CAD on its own, run {r+1}")
            if LABEL == "twice": t36c(CAD, f"real CAD second open, run {r+1}")
        print("ERR", errors(), flush=True)
    finally: a.stop()
