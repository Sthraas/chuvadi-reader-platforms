import helpers as h
from lt_base import *
a=App(APP, EV+"/cancel-pdf", display=":67"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(3); t0=time.time(); a.send("open /tmp/fifo/slow.pdf")
    seen=None; log=[]
    while time.time()-t0<25:
        st=a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/^Cancel/.test(b.innerText.trim())); var t=document.body.innerText; return [!!b, t.includes('Opening'), /Results|Grid/.test(t)]")
        log.append((round(time.time()-t0,1),st))
        if st[0] and seen is None:
            seen=round(time.time()-t0,1); a.shot("cancel-shown")
            a.js("[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/^Cancel/.test(b.innerText.trim())).click()"); time.sleep(2)
            print(f"Cancel shown at {seen}s, clicked | tabs after: {tabs(a)}"); a.shot("after-cancel"); break
        time.sleep(0.2)
    if seen is None: print("Cancel never shown; state timeline:", [l for i,l in enumerate(log) if i==0 or l[1]!=log[i-1][1]])
    try:
        a.send("open /home/claude/lt/five-pages.pdf", timeout=20); time.sleep(5); print("next open after:", tabs(a))
    except Exception as e: print("next open: driver open did not return in 20 s:", str(e)[:80], "| tabs now:", tabs(a))
    a.shot("end")
finally: a.stop()
