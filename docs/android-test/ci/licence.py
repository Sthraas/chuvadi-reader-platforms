#!/usr/bin/env python3
"""AT-01 / B-10: About › Licences lists every third-party component that ships (test tooling only).
    licence.py <out-dir> [assemblies.txt]"""
import json
import os
import sys
import time

from lib import Cdp, Results, component, screencap, sh

OUT = sys.argv[1]
R = Results(OUT, "licence")
cdp = Cdp()
sh(f"am start -W -n {component()}")
cdp.connect(60)
cdp.wait("!!(window.Blazor && Blazor.navigateTo) && document.getElementById('app').children.length > 0", 60)
cdp.js("Blazor.navigateTo('/licence')")
time.sleep(2)
tabs = cdp.js("[...document.querySelectorAll('button, [role=tab], a')].filter(b => b.getBoundingClientRect().width > 0).map(b => (b.innerText || '').trim()).filter(t => t)")
texts = {}
for want in ("Third-party notices", ".NET runtime", "EULA", "Licence", "License"):
    hit = cdp.js("((w) => { const b = [...document.querySelectorAll('button, [role=tab], a')].find(e => (e.innerText || '').trim().toLowerCase().startsWith(w.toLowerCase()) && e.getBoundingClientRect().width > 0); if (b) { b.click(); return true; } return false; })(%s)" % json.dumps(want))
    if hit:
        time.sleep(1.5)
        texts[want] = cdp.js("document.body.innerText")
        screencap(os.path.join(OUT, f"licence-{want.strip('.').replace(' ', '-').lower()}.png"))
notices = texts.get("Third-party notices", "")
open(os.path.join(OUT, "notices-in-app.txt"), "w").write(notices)
need = ["AndroidX", "Material", "Kotlin", "kotlinx", "Glide", "Tink", "Gson", "JetBrains"]
missing = [n for n in need if n.lower() not in notices.lower()]
R.check("AT-01 About › Licences › Third-party notices names AndroidX, Material, Kotlin, kotlinx, Glide, Tink, Gson, JetBrains",
        bool(notices) and not missing, {"tabs": tabs[:20], "missing": missing, "chars": len(notices)})
# Every Xamarin.* binding in the Release app appears in the notices
if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
    shipped = [l.strip()[:-4] for l in open(sys.argv[2]) if l.strip().startswith(("Xamarin.", "GoogleGson", "Square."))]
    absent = [a for a in shipped if a.lower() not in notices.lower()]
    R.check("AT-01 every Xamarin.* / third-party binding assembly in the Release app is named in the in-app notices", not absent,
            {"shipped": len(shipped), "absent": absent})
R.check("B-10 .NET runtime notices tab present", ".NET runtime" in texts or any(".net" in t.lower() for t in tabs), {"tabs": tabs[:20]})
