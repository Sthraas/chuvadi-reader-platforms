import helpers as h
from lt_base import *
PDF="/home/claude/lt/five-pages.pdf"; h.PDF=PDF
a=App(APP, EV+"/redact", display=":63"); h.bind(a); a.start_display()
OUTF=os.path.join(a.home,"Documents","redacted.pdf")
try:
    a.launch(PDF); time.sleep(3); a.click(".lb-mode",3); time.sleep(2)
    h.click_label(".srail","Find & redact"); time.sleep(1.5)
    h.type_into("input[placeholder='Find text…']", "print test"); time.sleep(0.5)
    a.js("[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='Find' && b.offsetParent).click()"); time.sleep(3)
    a.shot("found"); print("status:", a.text(".statusbar").replace("\n"," "))
    print("panel:", a.js("var p=[...document.querySelectorAll('*')].find(e=>e.innerText&&e.innerText.startsWith('Find & redact')&&e.offsetParent&&e.children.length>2); return p?p.innerText.slice(0,500):''"))
    btns=a.js("return [...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>b.innerText.trim()).filter(t=>t)")
    print("buttons:", btns)
finally: a.stop()
