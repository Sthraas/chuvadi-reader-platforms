# The Excel grid as the file holds it (patch 26): what layout.xlsx shows. Usage: t_grid.py <layout.xlsx>
import helpers as h, json
from lt_base import *
F = sys.argv[1]
a = App(APP, EV + "/grid", display=":84"); h.bind(a); a.start_display()
CELLS = "return [...document.querySelectorAll('.xv-cell[data-a]')].map(c=>{var b=c.getBoundingClientRect(); return [c.getAttribute('data-a'), c.innerText.trim().slice(0,30), Math.round(b.width), Math.round(b.height), c.className.replace('xv-cell','').trim(), c.getAttribute('data-n')||'', c.getAttribute('data-l')||'']})"
try:
    a.launch(); time.sleep(4); a.send("open " + F, timeout=20); time.sleep(5)
    print("TABS", a.js("return [...document.querySelectorAll('.xv-tab')].map(t=>t.innerText.replace(/\\s+/g,' ').trim()+(t.classList.contains('hidden-sheet')?' [dimmed]':''))"), flush=True)
    print("COLHDR", a.js("return [...document.querySelectorAll('.xv-colhdr')].slice(0,8).map(e=>e.innerText+':'+Math.round(e.getBoundingClientRect().width))"), flush=True)
    print("ROWHDR", a.js("return [...new Set([...document.querySelectorAll('.xv-rowhdr')].map(e=>e.innerText+':'+Math.round(e.getBoundingClientRect().height)))].slice(0,9)"), flush=True)
    for c in a.js(CELLS)[:24]: print("CELL", json.dumps(c, ensure_ascii=False), flush=True)
    wrap = a.js("var w=document.querySelector('.xv-gridwrap'), c=document.querySelector('.xv-canvas'); return [w.className, w.getAttribute('dir'), c.style.zoom]")
    print("SHEET1", wrap, flush=True)
    h.focus_main(); a.key("ctrl+f"); time.sleep(0.6); a.type("hidden"); a.key("Return"); time.sleep(1.5)
    print("FIND 'hidden'", a.js("return [[...document.querySelectorAll('.xv-cell.hit')].map(c=>c.getAttribute('data-a')), [...document.querySelectorAll('.xv-tab')].map(t=>t.innerText.replace(/\\s+/g,' ').trim())]"), a.text(".statusbar").replace("\n", " ")[:100], flush=True)
    a.key("Escape"); a.key("ctrl+f"); time.sleep(0.5); a.key("ctrl+a"); a.type("42"); a.key("Return"); time.sleep(1.5)
    print("FIND '42'", a.js("return [...document.querySelectorAll('.xv-tab')].map(t=>t.innerText.replace(/\\s+/g,' ').trim())"), flush=True)
    a.key("Escape"); a.js("document.querySelectorAll('.xv-tab')[1].click(); return 1"); time.sleep(1.5)
    print("SHEET2", a.js("var w=document.querySelector('.xv-gridwrap'), c=document.querySelector('.xv-canvas'); return [w.className, w.getAttribute('dir'), c.style.zoom]"), a.js(CELLS), flush=True)
    a.js("document.querySelectorAll('.xv-tab')[2].click(); return 1"); time.sleep(1.5)
    print("SHEET3 (hidden)", a.js(CELLS), flush=True)
finally: a.stop()
