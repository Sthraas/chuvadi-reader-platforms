# Patch 28 spot checks: Find on a turned page highlights the word where it is shown; Fit page fits each page;
# Ctrl+F opens the viewer's Find on Excel; Find matches in hidden rows and columns are named above the sheet.
# Usage: t_patch28.py <rot4.pdf> <layout.xlsx>
import helpers as h, json
from lt_base import *
a = App(APP, EV + "/patch28", display=":89"); h.bind(a); a.start_display()
def goto(n): a.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{n}'; b.dispatchEvent(new Event('change')); return 1"); time.sleep(1.5)
def btn(lab): a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')=='{lab}'&&b.offsetParent); b.click(); return 1"); time.sleep(1)
HL = """var w=document.querySelector('.rpage-wrap[data-page="I"]'); var p=w.querySelector('.rpage'); var pb=p.getBoundingClientRect();
var hs=[...w.querySelectorAll('[class*=hit],[class*=find],mark,[class*=match]')].filter(e=>e.getBoundingClientRect().width>2).map(e=>{var b=e.getBoundingClientRect(); return [e.tagName+'.'+(e.getAttribute('class')||''), +((b.left+b.width/2-pb.left)/pb.width).toFixed(3), +((b.top+b.height/2-pb.top)/pb.height).toFixed(3), Math.round(b.width), Math.round(b.height)]});
return {page:[Math.round(pb.width),Math.round(pb.height)], desk:(function(){var d=document.querySelector('.rdesk').getBoundingClientRect(); return [Math.round(d.width),Math.round(d.height)]})(), hits:hs.slice(0,4)}"""
try:
    a.launch(); time.sleep(3); h.focus_main()
    a.xdo("key", "ctrl+f"); time.sleep(0.8); print("KEYS with no PDF opened: Ctrl+F focus ->", a.js("var e=document.activeElement; return e.tagName+'.'+e.className"), "| path", a.js("return location.pathname"), flush=True); a.key("Escape")
    a.send("open " + sys.argv[1], timeout=15); time.sleep(3); btn("Fit page")
    for i in range(4):
        goto(i + 1); r = a.js(HL.replace('"I"', f'"{i}"')); print("FIT page", i + 1, r["page"], "in view", r["desk"], flush=True)
    h.focus_main(); a.xdo("mousemove", "1000", "500"); a.xdo("key", "ctrl+f"); time.sleep(0.8); a.type("ROT"); a.key("Return"); time.sleep(2)
    # the text "ROT page n" is drawn at (200,450) pt on a 595x842 page: where should it be shown after the turn?
    exp = {0: (0.36, 0.46), 1: (0.54, 0.36), 2: (0.64, 0.54), 3: (0.46, 0.64)}
    for i in range(4):
        goto(i + 1); r = a.js(HL.replace('"I"', f'"{i}"')); print("FIND page", i + 1, "highlight centre (fractions of the shown page)", [x[1:3] for x in r["hits"]][:2], "sizes", [x[3:5] for x in r["hits"]][:2], "expected about", exp[i], "| el", [x[0] for x in r["hits"]][:1], flush=True)
    a.key("Escape")
    a.send("open " + sys.argv[2], timeout=20); time.sleep(4); h.focus_main(); a.xdo("mousemove", "1000", "500"); a.xdo("click", "1"); a.xdo("key", "ctrl+f"); time.sleep(1)
    print("EXCEL Ctrl+F focus ->", a.js("var e=document.activeElement; return e.tagName+'.'+e.className+' ph='+(e.placeholder||'')"), flush=True)
    a.type("hidden"); a.key("Return"); t0 = time.time(); line = None
    while time.time() - t0 < 12 and not line:
        line = a.js("var e=document.querySelector('.xv-hiddenhits'); return e ? e.innerText : null"); time.sleep(0.5)
    print(f"EXCEL find 'hidden' ({time.time()-t0:.1f} s):", a.js("return [...document.querySelectorAll('.xv-tab')].map(t=>t.innerText.replace(/\\s+/g,' ').trim())"), "| line above the sheet:", line, flush=True)
finally: a.stop()
