import helpers as h
from lt_base import *
a=App(APP, EV+"/nocups", display=":82"); h.bind(a); a.start_display()
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    h.focus_main(); a.key("ctrl+p"); time.sleep(1.5); a.shot("card")
    a.click("section[aria-label=Print] button.primary"); time.sleep(6)
    dlg=[x for x in h.native_windows() if x[1].startswith("Print")]; print("GTK dialog:", dlg, "| app alive:", a.alive())
    a.shot("dialog"); print("app text:", [t for t in toasts(a)][:3])
    if dlg:
        subprocess.run(["xdotool","windowactivate","--sync",dlg[0][0]],env=a.env,capture_output=True); time.sleep(1); a.key("Return"); time.sleep(5); a.shot("after-return")
        print("after Return — dialog still:", bool([x for x in h.native_windows() if x[1].startswith("Print")]), "| alive:", a.alive(), "| toasts:", toasts(a)[:3])
finally: a.stop()
