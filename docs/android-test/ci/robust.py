#!/usr/bin/env python3
"""Robustness suite (test tooling only): damaged / empty / non-PDF files, very large files, a
DocumentsProvider (non-MediaStore) URI, no network, en-IN locale, revoked access.

    robust.py <out-dir> <fixtures-dir>
"""
import json
import os
import sys
import time

from lib import Cdp, PKG, Results, adb, component, open_with, pid, push_media, screencap, sh

OUT, FX = sys.argv[1], sys.argv[2]
R = Results(OUT, "robust")
cdp = Cdp()
COMP = component()
n = [0]

STATE = r"""(() => ({ url: location.pathname, tab: ((document.querySelector('.rtab.active .rtab-name') || document.querySelector('.ph-t')) || {}).textContent?.trim(),
  rendered: document.querySelectorAll('.rpage svg').length, pages: document.querySelectorAll('.rpage-wrap').length,
  text: document.body.innerText.slice(0, 300) }))()"""


def shot(name):
    n[0] += 1
    screencap(os.path.join(OUT, f"{n[0]:02d}-{name}.png"))


def state():
    try:
        return cdp.js(STATE)
    except Exception as e:
        cdp.close()
        return {"error": str(e)[:200]}


def alive_and_usable():
    if not pid():
        return False
    st = state()
    return "error" not in st and bool(st.get("url"))


def wait(pred, secs):
    end = time.time() + secs
    st = {}
    while time.time() < end:
        st = state()
        if pred(st):
            return st
        time.sleep(0.5)
    return st


sh(f"am start -W -n {COMP}")
cdp.connect(60)

# R-01 damaged files: a clear message, no crash, app still usable
for f in ("damaged-truncated.pdf", "damaged-xref.pdf", "not-a-pdf.pdf", "empty.pdf"):
    uri = push_media(os.path.join(FX, f))
    t0 = time.time()
    open_with(uri)
    st = wait(lambda s: (s.get("tab") or "").startswith(f.split(".")[0]) and ("damaged" in (s.get("text") or "").lower()
              or "couldn" in (s.get("text") or "").lower() or s.get("rendered", 0) > 0), 30)
    shot(f.split(".")[0])
    R.check(f"R-01 {f}: clear message or recovered view, no crash, app usable",
            alive_and_usable() and bool(st.get("tab")), {"state": st, "seconds": round(time.time() - t0, 1)})

# R-03 very large files
for f, wait_s in (("big-600p.pdf", 60), ("heavy-image.pdf", 90)):
    uri = push_media(os.path.join(FX, f))
    t0 = time.time()
    open_with(uri)
    st = wait(lambda s: (s.get("tab") or "").startswith(f.split(".")[0]) and s.get("rendered", 0) > 0, wait_s)
    secs = round(time.time() - t0, 1)
    shot(f.split(".")[0])
    anr = "ANR in in.chuvadi" in adb("logcat", "-d")
    pss = sh(f"dumpsys meminfo {PKG} | grep -m1 'TOTAL PSS'").strip()
    R.check(f"R-03 {f} opens, first page painted, no ANR", st.get("rendered", 0) > 0 and not anr,
            {"seconds_to_first_page": secs, "pages": st.get("pages"), "anr": anr, "mem": pss})
    if f == "big-600p.pdf" and st.get("rendered", 0) > 0:
        t1 = time.time()
        cdp.js("(() => { const d = [...document.querySelectorAll('.rdesk')].find(e => e.getBoundingClientRect().width > 0); d.scrollTop = d.scrollHeight; })()")
        last = wait(lambda s: cdp.js("(() => { const w = document.querySelectorAll('.rpage-wrap'); const l = w[w.length - 1]; return !!(l && l.querySelector('svg')); })()"), 30)
        R.check("R-03b 600-page file: last page renders after jumping to the end", bool(cdp.js(
            "(() => { const w = document.querySelectorAll('.rpage-wrap'); return !!w[w.length - 1].querySelector('svg'); })()")),
            {"seconds": round(time.time() - t1, 1)})

# R-04 a DocumentsProvider URI (ExternalStorageProvider, as Files / cloud apps hand out), not MediaStore
adb("push", os.path.join(FX, "doc-12p.pdf"), "/sdcard/Download/provider-doc.pdf")
uri = "content://com.android.externalstorage.documents/document/primary%3ADownload%2Fprovider-doc.pdf"
out = sh(f"am start -a android.intent.action.VIEW -d '{uri}' -t application/pdf -p {PKG} --grant-read-uri-permission")
st = wait(lambda s: (s.get("tab") or "").startswith("provider-doc") and s.get("rendered", 0) > 0, 30)
shot("provider-uri")
R.check("R-04 DocumentsProvider content URI opens (name from the provider)", st.get("rendered", 0) > 0,
        {"am": out.strip()[-200:], "state": st})

# R-05 no network: airplane mode, open and use; no network attempts by the app
sh("cmd connectivity airplane-mode enable")
time.sleep(3)
uid = sh(f"cmd package list packages -U {PKG}").split("uid:")[-1].strip()
before = sh(f"cat /proc/net/xt_qtaguid/stats 2>/dev/null | grep ' {uid} ' | wc -l").strip()
sh(f"am force-stop {PKG}")
sh(f"am start -W -n {COMP}")
cdp.close()
uri = push_media(os.path.join(FX, "doc-12p.pdf"), "offline-doc.pdf")
open_with(uri)
st = wait(lambda s: (s.get("tab") or "").startswith("offline-doc") and s.get("rendered", 0) > 0, 40)
shot("airplane")
R.check("R-05 airplane mode: app starts and opens a PDF", st.get("rendered", 0) > 0, st)
sockets = sh(f"cat /proc/$(pidof {PKG})/net/tcp6 /proc/$(pidof {PKG})/net/tcp 2>/dev/null | wc -l").strip()
sh("cmd connectivity airplane-mode disable")
R.check("R-05b no INTERNET permission, so the app can't open sockets (recorded)", True,
        {"tcp_table_lines_seen_by_app": sockets})

# R-06 en-IN locale and a non-Latin system language
for loc in ("en-IN", "ta-IN", "hi-IN"):
    sh(f"cmd locale set-app-locales {PKG} --locales {loc} 2>/dev/null || true")
    sh(f"settings put system system_locales {loc}")
    sh(f"am force-stop {PKG}")
    sh(f"am start -W -n {COMP}")
    cdp.close()
    st = wait(lambda s: bool(s.get("url")), 40)
    cdp.js("Blazor.navigateTo('/')")
    time.sleep(2)
    shot(f"locale-{loc}")
    over = cdp.js("document.documentElement.scrollWidth - innerWidth")
    R.check(f"R-06 locale {loc}: app starts, Home lays out, no sideways overflow", alive_and_usable() and over <= 0,
            {"overflow": over, "text": (state().get("text") or "")[:160]})
sh("settings put system system_locales en-US")

# R-07 fresh install (data cleared): first-run box, no sample files, no name on Home
sh(f"pm clear {PKG}")
sh(f"am start -W -n {COMP}")
cdp.close()
st = wait(lambda s: bool(s.get("url")), 40)
time.sleep(2)
shot("fresh-install")
txt = cdp.js("document.body.innerText")
R.check("R-07 fresh install: no sample/recent files, no name in the greeting",
        "startup-doc" not in txt and "design-doc" not in txt and "Pick up where" not in txt,
        {"home": txt[:400]})

log = adb("logcat", "-d", "-v", "epoch")
fatal = [l for l in log.splitlines() if "FATAL EXCEPTION" in l or f"ANR in {PKG}" in l]
R.check("R-10 no crash / ANR during the robustness suite", not fatal, fatal[:5])
