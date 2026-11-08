import helpers as h
from lt_base import *
a=App(APP, EV+"/tabs", display=":80"); h.bind(a); a.start_display()
def rss(): return int(open(f"/proc/{a.proc.pid}/status").read().split("VmRSS:")[1].split()[0])//1024
def wk(): return sum(int(x) for x in subprocess.run("ps -o rss= -C WebKitWebProcess",shell=True,capture_output=True,text=True).stdout.split())//1024
try:
    a.launch(); time.sleep(3); print("start app", rss(), "MB  webkit", wk(), "MB")
    for i in range(1,31):
        a.send(f"open /home/claude/tabs/doc-{i:02d}.pdf"); time.sleep(1.5)
        if i in (10,20,30): print(f"{i} tabs: app {rss()} MB  webkit {wk()} MB  tabs shown {len(tabs(a))}")
    time.sleep(3); a.shot("30-tabs")
    t=time.time(); a.js("document.querySelectorAll('.rtab')[0].click()"); a.wait(lambda: a.js("return document.querySelector('.rtab.active, .rtab[aria-selected=true]')?.innerText.includes('doc-01')"),10,"switch"); print(f"switch to tab 1: {1000*(time.time()-t):.0f} ms")
    for i in range(30): 
        a.js("var x=document.querySelector('.rtab .rtab-close, .rtab button'); if(x) x.click()"); time.sleep(0.3)
    time.sleep(5); print("after closing all: tabs", len(tabs(a)), " app", rss(), "MB  webkit", wk(), "MB"); a.shot("closed-all")
finally: a.stop()
