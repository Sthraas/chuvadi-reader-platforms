import helpers as h
from lt_base import *
PDF="/home/claude/lt/five-pages.pdf"; h.PDF=PDF
a=App(APP, EV+"/explore", display=":62"); h.bind(a); a.start_display()
try:
    a.launch(PDF); time.sleep(3)
    for m,name in [(1,"mark"),(2,"arrange"),(3,"protect")]:
        a.click(".lb-mode", m); time.sleep(2)
        print(name, "rail:", h.visible(".srail button")); a.shot("mode-"+name)
finally: a.stop()
