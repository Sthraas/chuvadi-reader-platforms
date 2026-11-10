# Excel number formats as the file holds them (D-161): label | shown text | stored value (title / data-v) | colour.
# Usage: t_formats.py <file.xlsx> [first-row last-row]
import helpers as h, json
from lt_base import *
F = sys.argv[1]
a = App(APP, EV + "/formats", display=":76"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(4); a.send("open " + F, timeout=20); time.sleep(5)
    rows = a.js("""return [...document.querySelectorAll('td.xv-cell[data-a]')].map(td=>{var f=td.querySelector('.xv-fill'); var t=f?[...f.children].filter(s=>!s.classList.contains('xv-rep')).map(s=>s.textContent).join('⟷'):td.textContent;
      return [td.getAttribute('data-a'), t, td.getAttribute('data-v'), td.getAttribute('title'), getComputedStyle(td).color, getComputedStyle(td).textAlign]})""")
    cells = {r[0]: r for r in rows}
    for r in rows:
        if r[0].startswith("B"):
            lab = cells.get("A" + r[0][1:], [None, ""])[1]
            print("FMT", json.dumps({"cell": r[0], "label": lab, "shown": r[1], "stored": r[2], "title_is_stored": r[2] == r[3], "color": r[4], "align": r[5]}, ensure_ascii=False), flush=True)
    for r in rows:
        if r[0].startswith("A") and ("B" + r[0][1:]) not in cells: print("TXT", json.dumps({"cell": r[0], "shown": r[1], "stored": r[2]}, ensure_ascii=False), flush=True)
    # value bar on click, and copy
    a.js("var td=document.querySelector('td.xv-cell[data-a=\"B23\"]')||document.querySelector('td.xv-cell[data-a=\"B5\"]'); td.click(); return 1"); time.sleep(0.5)
    print("BAR", a.js("var b=document.querySelector('.xv-valbar'); return [b.hidden, b.innerText]"), flush=True)
finally: a.stop()
