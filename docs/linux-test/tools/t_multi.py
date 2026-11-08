from lt_base import *
a = App(APP, EV+"/multi", display=":61"); a.start_display()
try:
    a.launch("/home/claude/lt/five-pages.pdf", "/home/claude/lt/second.pdf", "/home/claude/lt/sample.docx")
    time.sleep(4); print("T4.11a TABS after CLI with 3 files:", tabs(a))
    p = subprocess.Popen([APP+"/chuvadi-reader", "/home/claude/lt/sample.xlsx"], env=a.env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8)
    print("T4.11b second launch still running as its own process:", p.poll() is None)
    out = subprocess.run(["xdotool","search","--onlyvisible","--name","Chuvadi"], env=a.env, capture_output=True, text=True).stdout.split()
    print("visible windows named Chuvadi:", len(out))
    print("TABS in first window after second launch:", tabs(a)); a.shot("second-launch"); p.terminate()
finally:
    a.stop()
