# Page images by address (D-158, 36d), independently: hash the decoded pixels of every sheet the page shows, at fit and
# after zooming in and back out, so two builds (inline data URL vs _chvd/pages/<token>.png) can be compared.
# Usage: t_pages.py <file.pdf> <label>   -> prints one JSON line per step. Only hashes and sizes are printed.
import helpers as h, json
from lt_base import *
F, LABEL = sys.argv[1], sys.argv[2]
HASH = """var w=document.querySelector('.rpage-wrap[data-page="I"]'); var im=w&&w.querySelector('svg image'); if(!im) return null;
var href=im.getAttribute('href')||im.getAttribute('xlink:href')||'';
return new Promise(res=>{var i=new Image(); i.onload=()=>{var c=document.createElement('canvas'); c.width=i.naturalWidth; c.height=i.naturalHeight;
 var x=c.getContext('2d'); x.drawImage(i,0,0); var d=x.getImageData(0,0,c.width,c.height).data, h=2166136261>>>0, ink=0;
 for (var k=0;k<d.length;k++){h^=d[k]; h=Math.imul(h,16777619)>>>0;} for (var k=0;k<d.length;k+=4){ if(d[k]<200||d[k+1]<200||d[k+2]<200) ink++; }
 res([c.width,c.height,h.toString(16),ink, href.startsWith('data:')?'inline':href.slice(0,12), w.innerHTML.length]);};
 i.onerror=()=>res(['decode-error',href.slice(0,40)]); i.src=href;})"""
def info(i): return a.js(HASH.replace('"I"', f'"{i}"'))
def href(i): return a.js(f"var w=document.querySelector('.rpage-wrap[data-page=\"{i}\"]'); var im=w&&w.querySelector('svg image'); return im?(im.getAttribute('href')||'').slice(0,64)+(im.getAttribute('href')||'').length:''")
def goto(n): a.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{n}'; b.dispatchEvent(new Event('change')); return 1")
def zoom(d): a.js(f"var b=[...document.querySelectorAll('button,[role=button]')].find(b=>b.getAttribute('aria-label')=='Zoom {d}' && b.offsetParent); b.click(); return 1")
def zpct(): return a.js("var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)); return z?z.innerText:''")
def settle(i, prev, limit=90):
    t0 = time.time()
    while time.time() - t0 < limit:
        cur = href(i)
        if cur and cur != prev:
            time.sleep(1.0)
            if href(i) == cur: return time.time() - t0
        time.sleep(0.2)
    return None
a = App(APP, EV + f"/pages-{LABEL}", display=":71"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(4); a.send("open " + F, timeout=15)
    settle(0, ""); time.sleep(1.5); out = {}
    for n in range(1, 6):
        if n > 1: prev = href(n - 1); goto(n); settle(n - 1, prev) if not prev else time.sleep(1.5)
        out[f"fit sheet {n}"] = info(n - 1)
    goto(1); time.sleep(2)
    for step, d in (("in", "in"), ("in", "in"), ("in", "in"), ("out", "out"), ("out", "out"), ("out", "out")):
        prev = href(0); zoom(d); t = settle(0, prev)
        out[f"zoom {d} -> {zpct()} ({'redrawn %.1f s' % t if t else 'no redraw'})"] = info(0)
    for k, v in out.items(): print(json.dumps({"build": LABEL, "step": k, "img": v}), flush=True)
finally: a.stop()
