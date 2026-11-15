# Pinch as far as the runner allows (the host's test verb, patch 27 form "phase scale x y"): on Home, on a PDF page,
# and on the Word and Excel viewers. The bars must never scale. Usage: t_pinch.py
import helpers as h
from lt_base import *
a = App(APP, EV + "/pinch", display=":88"); h.bind(a); a.start_display()
M = "return [Math.round(document.querySelector('.topbar').getBoundingClientRect().height), Math.round(document.querySelector('.leftbar').getBoundingClientRect().width), visualViewport.scale, innerWidth]"
Z = "var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)&&e.offsetParent); return z?z.innerText:''"
V = "var e=document.querySelector('.xv-canvas')||document.querySelector('.dv-page, .docx-page, .dv-body, .dv'); if(!e) return 'no viewer'; var b=e.getBoundingClientRect(); return (e.className.split(' ')[0])+' zoom='+(e.style.zoom||getComputedStyle(e).zoom)+' w='+Math.round(b.width)"
def pinch(x, y, scales):
    a.send(f"pinch 0 1 {x} {y}")
    for s in scales: a.send(f"pinch 1 {s:.5f} {x} {y}"); time.sleep(0.05)
    a.send(f"pinch 2 1 {x} {y}"); time.sleep(0.4)
try:
    a.launch(); time.sleep(3); b = a.js(M); pinch(900, 500, [1.1, 1.3, 1.6])
    print("HOME pinch:", b, "->", a.js(M), flush=True)
    a.send("open /home/claude/lt/five-pages.pdf", timeout=15); time.sleep(3); z0 = a.js(Z); b = a.js(M)
    pinch(1000, 500, [1.1, 1.25, 1.4]); z1 = a.js(Z); pinch(1000, 500, [0.9, 0.8, 1 / 1.4])
    print("PDF pinch out then in:", z0, "->", z1, "->", a.js(Z), "| bars", b, "->", a.js(M), flush=True)
    for f in ("/home/claude/exact/exact.xlsx", "/home/claude/exact/exact.docx"):
        a.send("open " + f, timeout=20); time.sleep(4); v0 = a.js(V); z0 = a.js(Z); b = a.js(M)
        pinch(1000, 500, [1.1, 1.25, 1.4]); v1 = a.js(V); z1 = a.js(Z); pinch(1000, 500, [0.9, 0.8, 1 / 1.4])
        print(os.path.basename(f), "pinch out then in:", (z0, v0), "->", (z1, v1), "->", (a.js(Z), a.js(V)), "| bars", b, "->", a.js(M), flush=True)
finally: a.stop()
