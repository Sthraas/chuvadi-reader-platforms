import helpers as h
from lt_base import *
a=App(APP, EV+"/tmp", display=":76"); h.bind(a); a.start_display()
before=set(subprocess.run("find /tmp -newer /home/claude/lt/t_tmp.py 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split())
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(4)
    a.click(".lb-mode",3); time.sleep(1.5); h.click_label(".srail","Password"); time.sleep(1.5); a.shot("password-card")
    print("card:", a.js("var s=[...document.querySelectorAll('section,aside')].find(e=>e.offsetParent&&/password/i.test(e.getAttribute('aria-label')||e.innerText.slice(0,40))); return s?s.innerText.replace(/\\s+/g,' ').slice(0,400):''"))
    after=set(subprocess.run("find /tmp -newer /home/claude/lt/t_tmp.py -type f 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split())
    for f in sorted(after-before):
        if any(x in f for x in ("xvfb","claude-0",".X","uitest","bus","NuGet")): continue
        st=os.stat(f); print("NEW", oct(st.st_mode&0o777), st.st_size, f)
    print("dirs:", subprocess.run("find /tmp -maxdepth 2 -newer /home/claude/lt/t_tmp.py -type d -iname '*chuvadi*' -exec stat -c '%a %n' {} +",shell=True,capture_output=True,text=True).stdout)
finally: a.stop()
print("left after exit:", subprocess.run("find /tmp -maxdepth 3 -iname '*chuvadi*' 2>/dev/null",shell=True,capture_output=True,text=True).stdout)
