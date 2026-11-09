import helpers as h, sys
from lt_base import *
cold=sys.argv[1]=="cold"; res=[]
for run in range(int(sys.argv[2])):
    if cold: subprocess.run("sync; echo 3 > /proc/sys/vm/drop_caches",shell=True)
    a=App(APP, EV+f"/cadt{run}", display=f":7{run}"); h.bind(a); a.start_display()
    try:
        t0=time.time(); a.launch("/home/claude/cad/cad.pdf")
        t_launch=time.time()-t0
        while 'Opening' in (a.js("return document.body.innerText") or 'Opening') and time.time()-t0<60: time.sleep(0.1)
        t_gone=time.time()-t0
        prev=None; stable_since=None; last_change=time.time()
        while time.time()-t0<60:
            subprocess.run(["import","-window","root","-crop","1920x1030+0+0","-resize","25%","/tmp/cadt.png"],env=a.env)
            cur=open("/tmp/cadt.png","rb").read()
            if cur!=prev: prev=cur; last_change=time.time()
            elif time.time()-last_change>3: break
            time.sleep(0.2)
        res.append((t_gone, last_change-t0)); print(f"run {run}: 'Opening…' gone at {t_gone:.2f}s, page drawn (last change) at {last_change-t0:.2f}s (incl. driver launch {t_launch:.2f}s)", flush=True)
    finally: a.stop()
import statistics as st
print("CADTIME", sys.argv[1], "median gone %.2f s, median drawn %.2f s, worst drawn %.2f s"%(st.median(r[0] for r in res), st.median(r[1] for r in res), max(r[1] for r in res)))
