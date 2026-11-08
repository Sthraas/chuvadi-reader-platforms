import helpers as h
from lt_base import *
a=App(APP, EV+"/reveal-warm", display=":85"); h.bind(a); a.start_display()
X=lambda *c: subprocess.run(["xdotool",*c],env=a.env,capture_output=True,text=True).stdout.strip()
try:
    subprocess.Popen(["nautilus","--gapplication-service"],env=a.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(10)
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    print("invoke doc.reveal:", a.send("invoke doc.reveal", timeout=20)); time.sleep(12)
    print("windows:", [x for x in X("search","--onlyvisible","--name",".").split()[:0]] or "")
    names=[X("getwindowname",w) for w in X("search","--onlyvisible","--name",".").split()]
    print("visible window titles:", [n for n in names if n])
    print("nautilus running:", subprocess.run("pgrep -a nautilus",shell=True,capture_output=True,text=True).stdout.strip()[:120])
    a.shot("nautilus")
    print("toasts:", toasts(a))
finally:
    subprocess.run("pkill -f nautilus",shell=True); a.stop()
