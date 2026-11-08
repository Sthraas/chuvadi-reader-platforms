import helpers as h
from lt_base import *
a=App(APP, EV+"/form", display=":93"); h.bind(a); a.start_display()
def vis(): return [b for b in a.js("return [...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>b.innerText.trim().replace(/\\s+/g,' '))") if b][12:]
try:
    a.launch("/home/claude/fm/form.pdf"); time.sleep(5); a.shot("form-read")
    print("form inputs in Read:", a.js("return [...document.querySelectorAll('input,select,textarea')].filter(e=>e.offsetParent).map(e=>(e.name||e.getAttribute('aria-label')||e.placeholder)+'|'+e.type)"))
    print("invoke m.form:", a.send("invoke m.form", timeout=20)); time.sleep(3); a.shot("form-mode")
    print("status:", a.text(".statusbar").replace("\n"," ")[:150])
    print("form inputs now:", a.js("return [...document.querySelectorAll('input,select,textarea')].filter(e=>e.offsetParent).map(e=>(e.name||e.getAttribute('aria-label')||e.placeholder)+'|'+e.type+'|'+e.value)"))
    print("buttons:", vis()[-12:])
finally: a.stop()
