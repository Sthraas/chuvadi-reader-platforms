import helpers as h
from lt_base import *
a=App(APP, EV+"/stack", display=":62"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(4)
    try: a.send("open /tmp/chvd-stall/slow.pdf", timeout=8)
    except Exception as e: print("open send:", str(e)[:60])
    time.sleep(8)
    out=subprocess.run(["dotnet-stack","report","-p",str(a.proc.pid)],capture_output=True,text=True,timeout=60,env=dict(os.environ,PATH=os.environ["PATH"]+":/root/.dotnet/tools")).stdout
    open(EV+"/stack/stacks.txt","w").write(out)
    print("threads:", out.count("Thread (0x"))
finally: a.stop()
