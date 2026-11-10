# Hunt the intermittent fresh-open stall (Linux, bf60da9): a fresh open of a drawing keeps the previous zoom, never
# fits, shows sheet 1 as a portrait placeholder and never draws it. Each try is a freshly started app.
# Usage: t_stall.py <file.pdf> <tries per way>   -> one line per try; only states and numbers are printed.
import helpers as h
from lt_base import *
F, N = sys.argv[1], int(sys.argv[2]); FIVE = "/home/claude/lt/five-pages.pdf"
def drawn(i): return a.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{i}\"]'); return !!w && [...w.querySelectorAll('svg')].some(s=>+((s.getAttribute('viewBox')||'').split(' ')[2])>100)")
def zpct(): return a.js("var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)&&e.offsetParent); return z?z.innerText:''")
def zvar(): return a.js("var d=document.querySelector('.rdesk'); return d ? d.style.getPropertyValue('--rpage-zoom') : ''")
def box0(): return a.js("var w=document.querySelector('.rpage-wrap[data-page=\"0\"]'); if(!w) return 'none'; var b=w.getBoundingClientRect(); return Math.round(b.width)+'x'+Math.round(b.height)")
def zoom(d, n=1):
    for _ in range(n):
        a.js(f"var b=[...document.querySelectorAll('button,[role=button]')].find(b=>b.getAttribute('aria-label')=='Zoom {d}' && b.offsetParent); if(b) b.click(); return 1"); time.sleep(0.4)
def close(): a.js("var x=document.querySelector('.rtab.active .rtab-x'); if (x) x.click(); return 1"); time.sleep(1)
def name_open(p): return a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{os.path.basename(p)}')")
def watch(t0, limit=int(os.environ.get("LIMIT", "30"))):
    states = []
    while time.time() - t0 < limit:
        if name_open(F) and drawn(0): return f"drawn {time.time()-t0:.1f} s, zoom label {zpct()} / view {zvar()}, sheet 1 box {box0()}", True
        s = (zpct(), zvar(), box0()); states = states if states and states[-1] == s else states + [s]
        time.sleep(0.25)
    return f"NOT drawn in {limit} s; zoom/box seen {states[-4:]}, tab open {name_open(F)}", False
WAYS = {
    "cli":       "launched with the file on the command line",
    "early":     "open sent 0.5 s after the window appears",
    "afterzoom": "five-pages opened, zoomed in 2 steps, closed; then open",
    "aftermid":  "the drawing opened and closed mid-render; then open again",
}
fails = 0
for way in WAYS:
    for k in range(N):
        a = App(APP, EV + f"/stall-{way}-{k}", display=f":{80 + len(WAYS) * 0 + list(WAYS).index(way) * 10 + k}"); h.bind(a); a.start_display()
        try:
            if way == "cli":
                t0 = time.time(); a.launch(F)
            else:
                a.launch()
                if way == "early": time.sleep(0.5)
                else: time.sleep(3)
                if way == "afterzoom":
                    a.send("open " + FIVE, timeout=15); time.sleep(3); zoom("in", 2); close()
                if way == "aftermid":
                    a.send("open " + F, timeout=15); time.sleep(0.4); close()
                t0 = time.time(); a.send("open " + F, timeout=20)
            msg, ok = watch(t0); fails += not ok
            print(f"STALL {way} try {k+1}: {msg}", flush=True)
            if not ok: a.shot(f"stall-{way}-{k}")   # local only; never committed for Arun's file
        except Exception as e:
            print(f"STALL {way} try {k+1}: error {str(e)[:120]}", flush=True); fails += 1
        finally: a.stop()
print(f"STALL total: {fails} not drawn of {N*len(WAYS)}", flush=True)
