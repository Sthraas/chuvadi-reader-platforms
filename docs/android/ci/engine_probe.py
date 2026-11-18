#!/usr/bin/env python3
"""D-202: what a second ":engine" process of the app costs and how it fails, on the booted emulator.

Uses the test-only probe build (-p:ChuvadiEngineProbe=true; src/ChuvadiReader.Android/Platform/EngineProbe).
With the app already running (E2: the engine starts when the first document opens):
  1. start the engine N times (the first half after dropping the page cache), timing each stage from
     bindService to the first answer, and reading the engine's memory (dumpsys meminfo);
  2. pages over a pipe the engine hands back through Binder (MB/s);
  3. runaway allocation in the engine;
  4. a stack overflow on a new thread, then on the Binder thread;
and after 3 and 4 whether the app's own process lived on. Logs of each crash are saved.

    engine_probe.py <apk> <label> <results-dir> [runs=10]
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time

APK, LABEL, OUT = sys.argv[1:4]
RUNS = int(sys.argv[4]) if len(sys.argv) > 4 else 10
PKG = "in.chuvadi.reader"
ENGINE = PKG + ":engine"
PROBE = f"{PKG}/in.chuvadi.reader.EngineProbeActivity"
os.makedirs(OUT, exist_ok=True)


def adb(*args, check=False, timeout=120):
    r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        sys.exit(f"adb {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def pidof(name):
    out = adb("shell", "pidof", name).split()
    # pidof matches the exact process name; the main process is "in.chuvadi.reader"
    return out[0] if out else None


def probe(cmd, arg=None, wait_for=None, seconds=60):
    adb("logcat", "-c")
    extra = ["--es", "cmd", cmd] + (["--ei", "arg", str(arg)] if arg is not None else [])
    adb("shell", "am", "start", "-n", PROBE, *extra)
    end = time.time() + seconds
    lines = []
    while time.time() < end:
        time.sleep(0.5)
        lines = [ln.split("ChuvadiProbe: ", 1)[1].strip() for ln in adb("logcat", "-d", "-s", "ChuvadiProbe:I").splitlines()
                 if "ChuvadiProbe: " in ln]
        if any(re.match(wait_for or cmd, ln) for ln in lines):
            break
    return lines


def meminfo(name):
    text = adb("shell", "dumpsys", "meminfo", name)
    pss = re.search(r"TOTAL PSS:\s+(\d+)", text) or re.search(r"^\s*TOTAL\s+(\d+)", text, re.M)
    rss = re.search(r"TOTAL RSS:\s+(\d+)", text)
    native = re.search(r"Native Heap\s+(\d+)", text)
    return {"pssKb": int(pss.group(1)) if pss else None, "rssKb": int(rss.group(1)) if rss else None,
            "nativeHeapPssKb": int(native.group(1)) if native else None}


adb("root")
time.sleep(3)
adb("wait-for-device")
adb("uninstall", PKG)
adb("install", "-r", APK, check=True)
adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
for _ in range(30):
    if pidof(PKG):
        break
    time.sleep(1)
time.sleep(12)   # the Ui up, as when a person opens their first document
app_pid = pidof(PKG)
report = {"label": LABEL, "apk": os.path.basename(APK), "appPid": app_pid, "app": meminfo(PKG), "starts": []}
print(f"{LABEL}: app pid {app_pid}, app memory {report['app']}", flush=True)

STAGES = ["fork", "runtime", "app", "service", "bound", "connected", "answered"]
for i in range(RUNS):
    cold = i < RUNS // 2
    if cold:
        adb("shell", "sync; echo 3 > /proc/sys/vm/drop_caches")
        time.sleep(1)
    lines = probe("start", wait_for=r"start (pid|failed)")
    line = next((ln for ln in lines if ln.startswith("start ")), "")
    nums = dict(re.findall(r"(\w+) (-?\d+)", line))
    run = {k: int(v) for k, v in nums.items()}
    run["pageCache"] = "dropped" if cold else "warm"
    time.sleep(1)
    run["meminfo"] = meminfo(ENGINE)
    report["starts"].append(run)
    print(f"{LABEL} start {i + 1} ({run['pageCache']}): " + "  ".join(f"{s} {run.get(s, '—')}" for s in STAGES)
          + f"  engine PSS {run['meminfo']['pssKb']} kB RSS {run['meminfo']['rssKb']} kB", flush=True)
    probe("stop")
    time.sleep(1)


def summary(rows):
    out = {}
    for s in STAGES + ["rssKb", "heapKb"]:
        v = [r[s] for r in rows if s in r]
        if v:
            out[s] = {"median": int(statistics.median(v)), "worst": max(v), "n": len(v)}
    for s in ("pssKb", "rssKb"):
        v = [r["meminfo"][s] for r in rows if r.get("meminfo", {}).get(s)]
        if v:
            out["meminfo." + s] = {"median": int(statistics.median(v)), "worst": max(v), "n": len(v)}
    return out


report["summary"] = {"dropped": summary([r for r in report["starts"] if r["pageCache"] == "dropped"]),
                     "warm": summary([r for r in report["starts"] if r["pageCache"] == "warm"])}

# Pages over a pipe handed back through Binder.
probe("start", wait_for=r"start (pid|failed)")
report["pipe"] = [next((ln for ln in probe("pipe", 64, wait_for=r"pipe \d+ MB|pipe not") if ln.startswith("pipe")), "")
                  for _ in range(3)]
print(f"{LABEL} pipe: {report['pipe']}", flush=True)


def crash(cmd):
    probe("stop")
    start = probe("start", wait_for=r"start (pid|failed)")
    epid = (re.search(r"start pid (\d+)", " ".join(start)) or [None, None])[1]
    adb("logcat", "-c")
    lines = probe(cmd, wait_for=rf"{cmd} (answered|engine gone|not)", seconds=180)
    time.sleep(3)
    log = adb("logcat", "-d", "-v", "threadtime")
    with open(os.path.join(OUT, f"{LABEL}-{cmd}.log"), "w") as f:
        f.write(log)
    engine_lines = [ln for ln in log.splitlines()
                    if epid and (f" {epid} " in ln or f"pid {epid}" in ln or f"pid: {epid}" in ln or "lowmemorykiller" in ln)]
    keys = [ln for ln in engine_lines if re.search(r"(?i)stack ?overflow|SIGSEGV|SIGABRT|Fatal signal|abort|Kill|OutOfMemory|"
                                                   r"mono|crash|signal \d+|backtrace|died|max-heap|heap", ln)]
    now_pid = pidof(PKG)
    res = {"enginePid": epid, "result": [ln for ln in lines if ln.startswith(cmd) or "engine" in ln],
           "engineStillRunning": bool(epid) and pidof(ENGINE) == epid,
           "appPidBefore": app_pid, "appPidAfter": now_pid, "appLived": now_pid == app_pid,
           "keyLogLines": [ln[:300] for ln in keys[:40]]}
    print(f"{LABEL} {cmd}: {json.dumps(res, indent=1)}", flush=True)
    return res


report["alloc"] = crash("alloc")
report["overflowThread"] = crash("overflow-thread")
report["overflowBinder"] = crash("overflow-binder")
probe("stop")
report["appAtEnd"] = {"pid": pidof(PKG), "lived": pidof(PKG) == app_pid}

print(f"\n{LABEL}: ms after bindService (median / worst)")
for cache in ("dropped", "warm"):
    s = report["summary"][cache]
    print(f"  page cache {cache}: " + "  ".join(f"{k} {s[k]['median']}/{s[k]['worst']}" for k in STAGES if k in s))
    for k in ("meminfo.pssKb", "meminfo.rssKb", "rssKb", "heapKb"):
        if k in s:
            print(f"    {k}: {s[k]['median']} / {s[k]['worst']}")
with open(os.path.join(OUT, f"engine-probe-{LABEL}.json"), "w") as f:
    json.dump(report, f, indent=2)
adb("uninstall", PKG)
ok = all(r.get("answered") for r in report["starts"]) and report["appAtEnd"]["lived"]
sys.exit(0 if ok else 1)
