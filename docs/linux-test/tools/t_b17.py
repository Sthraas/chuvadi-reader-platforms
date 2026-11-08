import helpers as h
from lt_base import *
a=App(APP, EV+"/b17", display=":63"); h.bind(a); a.start_display()
try:
    a.launch("/home/claude/rx/notzip.xlsx"); time.sleep(5)
    print("notzip visible:", a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&e.innerText.trim().length>15).map(e=>e.innerText.trim()).filter(t=>/open|damag|workbook|Details|Central/i.test(t)).slice(0,4)"))
    d=a.js("var s=[...document.querySelectorAll('details,summary,button')].find(e=>e.offsetParent&&/Details/i.test(e.innerText)); if(!s) return 'no Details control'; s.click(); return 'clicked '+s.tagName"); time.sleep(1)
    print("Details:", d, "|", a.js("return [...document.querySelectorAll('details,pre,code,[class*=detail]')].map(e=>e.innerText.trim().replace(/\\s+/g,' ')).filter(t=>t).slice(0,2)")); a.shot("notzip")
finally: a.stop()
