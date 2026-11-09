import helpers as h
from lt_base import *
a=App(APP, EV+"/b24", display=":62"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(3); t0=time.time()
    try: a.send("open /tmp/chvd-stall/slow.pdf", timeout=5)
    except Exception as e: print("send:", str(e)[:40])
    op=None; cn=None
    while time.time()-t0<15:
        t=a.js("return document.body.innerText") or ''
        if op is None and 'Opening' in t: op=round(time.time()-t0,1)
        if a.js("return [...document.querySelectorAll('button')].some(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim()))"): cn=round(time.time()-t0,1); break
        time.sleep(0.3)
    try: a.send("open /home/claude/lt/five-pages.pdf", timeout=10); time.sleep(3); nxt='five-pages.pdf' in tabs(a)
    except Exception as e: nxt="blocked"
    print(f"B-24 e242d92 slow.pdf: Opening at {op}s, Cancel at {cn}s, next open: {nxt}")
finally: a.stop()
