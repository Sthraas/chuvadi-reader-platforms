import helpers as h, sys
from lt_base import *
mode=sys.argv[1]
def remote_files(): return subprocess.run("docker exec cupsrv sh -c 'ls /root/PDF /var/spool/cups-pdf/ANONYMOUS 2>/dev/null'",shell=True,capture_output=True,text=True).stdout.split()
env={"CUPS_SERVER":"localhost:6631"} if mode=="env" else {}
a=App(APP, EV+"/remote-"+mode, display=":6%d"%(1 if mode=="env" else 2), env=env); h.bind(a); a.start_display()
if mode=="conf":
    os.makedirs(a.home+"/.cups",exist_ok=True); open(a.home+"/.cups/client.conf","w").write("ServerName localhost:6631\n")
before=set(remote_files())
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    h.focus_main(); a.key("ctrl+p"); time.sleep(1.2); a.click("section[aria-label=Print] button.primary"); time.sleep(4)
    dl=[x for x in h.native_windows() if x[1].startswith("Print")]
    print(mode, "| GTK dialog:", bool(dl), "| app message:", [t for t in toasts(a)][:1])
    if dl:
        subprocess.run(["xdotool","windowactivate","--sync",dl[0][0]],env=a.env,capture_output=True); time.sleep(3); a.shot("dialog"); a.key("Return")
        t0=time.time()
        while time.time()-t0<60 and not (set(remote_files())-before): time.sleep(2)
        new=sorted(set(remote_files())-before); print(mode, "| new output on the REMOTE server:", new)
        if new:
            n=new[-1]; subprocess.run(f"docker exec cupsrv sh -c 'cat /root/PDF/{n} 2>/dev/null || cat /var/spool/cups-pdf/ANONYMOUS/{n}' > {EV}/remote-{mode}/{n}",shell=True)
            p=f"{EV}/remote-{mode}/{n}"
            print(mode, "| pages", h.pdfinfo(p).get("Pages"), "| fonts", len(subprocess.run(["pdffonts",p],capture_output=True,text=True).stdout.splitlines())-2, "| images", len(subprocess.run(["pdfimages","-list",p],capture_output=True,text=True).stdout.splitlines())-2)
finally: a.stop()
