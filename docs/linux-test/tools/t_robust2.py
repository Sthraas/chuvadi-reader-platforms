import helpers as h
from lt_base import *
a=App(APP, EV+"/robust2", display=":81"); h.bind(a); a.start_display()
def rss(): 
    try: return int(open(f"/proc/{a.proc.pid}/status").read().split("VmRSS:")[1].split()[0])//1024
    except Exception: return -1
files=sorted(glob.glob("/home/claude/rx2/*"))
try:
    a.launch(); time.sleep(2)
    for f in files:
        n=os.path.basename(f); t=time.time()
        try: r=a.send("open "+f, timeout=60)
        except Exception as e: r="ERR "+str(e)[:80]
        peak=rss()
        for _ in range(16):
            time.sleep(0.5); peak=max(peak,rss())
            if not a.alive(): break
        alive=a.alive()
        msg=a.js("return [...document.querySelectorAll('[class*=toast],[class*=error],[class*=empty],.chvd-card,[role=alert],[role=dialog]')].filter(e=>e.offsetParent).map(e=>e.innerText.trim().replace(/\\s+/g,' ')).filter(x=>x).slice(0,3).join(' || ').slice(0,300)") if alive else "-"
        a.shot("open-"+n)
        print(f"{n:24} open->{str(r)[:20]:20} alive={alive} rss_peak={peak}MB tabs={tabs(a) if alive else '-'}\n    msg: {msg}", flush=True)
        if not alive:
            print("    APP DIED; log tail:", open(a.log_path).read()[-600:]); a.launch()
        else:
            a.key("Escape"); time.sleep(0.5)
finally: a.stop()
