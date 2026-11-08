import helpers as h
from lt_base import *
a=App(APP, EV+"/reveal-mon", display=":89", env={"PATH":"/tmp/stub:"+os.environ["PATH"]}); h.bind(a); a.start_display()
X=lambda *c: subprocess.run(["xdotool",*c],env=a.env,capture_output=True,text=True).stdout.strip()
try:
    subprocess.Popen(["nautilus","--gapplication-service"],env=a.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(10)
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    mon=subprocess.Popen(["dbus-monitor","--session","interface=org.freedesktop.FileManager1","type=error","type=method_return"],env=a.env,stdout=open("/tmp/dbusmon.log","w"),stderr=subprocess.STDOUT); time.sleep(1)
    print("invoke doc.reveal:", a.send("invoke doc.reveal", timeout=20)); time.sleep(12)
    print("windows:", [x for x in X("search","--onlyvisible","--name",".").split()[:0]] or "")
    names=[X("getwindowname",w) for w in X("search","--onlyvisible","--name",".").split()]
    print("visible window titles:", [n for n in names if n])
    print("nautilus running:", subprocess.run("pgrep -a nautilus",shell=True,capture_output=True,text=True).stdout.strip()[:120])
    a.shot("nautilus"); mon.terminate()
    print("toasts:", toasts(a))
finally:
    subprocess.run("pkill -f nautilus",shell=True); a.stop()
