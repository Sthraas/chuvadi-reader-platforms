import sys; sys.path.insert(0, "/home/claude/chuvadi-reader-platforms/docs/linux-test/tools")
import helpers as h
from lt_base import *
a = App(APP, "/tmp/pinchmark", display=":96"); h.bind(a); a.start_display()
n = lambda: a.js("return document.querySelectorAll('.mk-layer .mk-shape, .mk-layer .mk-text, .mk-shape-svg > *').length")
Z = "var z=[...document.querySelectorAll('.rtext,.rzoom')].find(e=>/%$/.test(e.innerText)&&e.offsetParent); return z?z.innerText:''"
try:
    a.launch(); time.sleep(3); a.send("open /home/claude/mk/mark-rot.pdf", timeout=15); time.sleep(3); a.click(".lb-mode", 1); time.sleep(1.3)
    for tool in ("Rectangle", "Draw", "Text"):
        h.click_label(".srail", tool); h.focus_main(); n0 = n(); z0 = a.js(Z)
        a.send("pinch 0 1 1000 500"); a.send("pinch 1 1.2 1000 500"); a.send("pinch 1 1.4 1000 500"); a.send("pinch 2 1 1000 500"); time.sleep(0.8)
        print(f"PINCH in Mark with {tool}: zoom {z0} -> {a.js(Z)} | marks before {n0}, after {n()}", flush=True)
        a.send("pinch 0 1 1000 500"); a.send(f"pinch 1 {1/1.4:.4f} 1000 500"); a.send("pinch 2 1 1000 500"); time.sleep(0.6)
finally: a.stop()
