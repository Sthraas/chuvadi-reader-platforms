import helpers as h
from lt_base import *
a=App(APP, EV+"/far", display=":65"); h.bind(a); a.start_display()
def rss(): return int(open(f"/proc/{a.proc.pid}/status").read().split("VmRSS:")[1].split()[0])//1024
try:
    a.launch(); time.sleep(2); t=time.time()
    a.send("open /home/claude/rx/far-cell.xlsx")
    time.sleep(5); a.send("open /home/claude/lt/five-pages.pdf"); t2=time.time()
    for i in range(36):
        time.sleep(5)
        tb=tabs(a); op=a.js("return document.body.innerText.includes('Opening')")
        print(f"t+{time.time()-t:5.0f}s rss={rss()}MB opening={op} tabs={tb} cpu={subprocess.run(['ps','-o','pcpu=','-p',str(a.proc.pid)],capture_output=True,text=True).stdout.strip()}", flush=True)
        if 'five-pages.pdf' in tb and not op: break
    a.shot("far-end")
    # is UI responsive? click Home
    a.js("[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='Home').click()"); time.sleep(1); print("home responsive:", a.js("return location.pathname"))
finally: a.stop()
