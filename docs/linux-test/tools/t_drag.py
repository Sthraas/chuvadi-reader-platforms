import helpers as h
from lt_base import *
a=App(APP, EV+"/drag", display=":83"); h.bind(a); a.start_display()
X=lambda *c: subprocess.run(["xdotool",*c],env=a.env,capture_output=True,text=True).stdout.strip()
try:
    a.launch(); time.sleep(4)
    w=X("search","--name","Chuvadi").split()[-1]
    subprocess.run(["wmctrl","-i","-r",w,"-b","remove,maximized_vert,maximized_horz"],env=a.env); time.sleep(1)
    X("windowsize",w,"1100","800"); X("windowmove",w,"400","50"); time.sleep(1)
    src=subprocess.Popen(["/usr/bin/python3.12","/home/claude/lt2/dragsrc.py","/home/claude/lt/five-pages.pdf","/home/claude/lt/second.pdf"],env=a.env,stdout=open("/tmp/dragsrc.log","w"),stderr=subprocess.STDOUT)
    time.sleep(3); sw=X("search","--name","DragSource").split()[-1]; X("windowmove",sw,"20","100"); time.sleep(1)
    a.shot("before")
    for c in [["mousemove","140","200"],["mousedown","1"],["mousemove","160","210"],["mousemove","300","250"],["mousemove","600","300"],["mousemove","900","400"],["mousemove","950","420"]]:
        X(*c); time.sleep(0.3)
    time.sleep(1); a.shot("hovering"); print("drop overlay shown:", a.js("return !!document.querySelector('[class*=drop]:not([hidden])') && [...document.querySelectorAll('[class*=drop]')].some(e=>e.offsetParent)"))
    X("mouseup","1"); time.sleep(5); a.shot("after-drop")
    print("TABS after dropping 2 files:", tabs(a))
    src.terminate()
finally: a.stop()
