import helpers as h
from lt_base import *
def lat():
    t=time.time()
    try: a.send("open /tmp/does-not-exist.pdf", timeout=30)   # goes through Dispatcher.InvokeAsync
    except Exception as e: return 30000
    return (time.time()-t)*1000
a=App(APP, EV+"/freeze", display=":63"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(3)
    idle=[lat() for _ in range(5)]
    a.js("[...document.querySelectorAll('.rtab')].forEach(t=>{var x=t.querySelector('button'); if(x) x.click()})"); time.sleep(1)
    t0=time.time(); a.send("open /home/claude/cad/cad.pdf")
    busy=[]; 
    while time.time()-t0<12: busy.append((round(time.time()-t0,1), round(lat())))
    print("UIFREEZE idle dispatcher latency ms:", [round(x) for x in idle])
    print("UIFREEZE while CAD opens/draws (t s, latency ms):", busy)
    print("UIFREEZE worst while drawing: %d ms" % max(b[1] for b in busy))
finally: a.stop()
