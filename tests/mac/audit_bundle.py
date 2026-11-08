#!/usr/bin/env python3
"""Mac Test bundle audit (T1.4, T1.5, T1.7, T1.9–T1.12) — TESTING ONLY. Runs on macOS.

  audit_bundle.py <Chuvadi.app> <asm-ids.tsv> <repo-root> <out.json>

Classifies every file in the bundle, checks every Mach-O's architectures, minimum OS and linked libraries,
reads Info.plist, compares the legal texts with the repo, and lists anything that is not Apple, Microsoft
(.NET / MAUI), Arun's own (Chuvadi, LiPicons, the app) or a font named in the notices.
"""
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys

app, asm_tsv, repo, out = sys.argv[1:5]
C = os.path.join(app, "Contents")
R = {"checks": [], "files": {}, "unknown": [], "machos": {}}


def run(*cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def check(cid, ok, note, **kw):
    R["checks"].append({"case": cid, "status": "pass" if ok else "fail", "note": note, **kw})


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---- Info.plist (T1.5)
info = plistlib.load(open(os.path.join(C, "Info.plist"), "rb"))
R["info_plist"] = {k: (v if isinstance(v, (str, int, bool, list, dict)) else str(v)) for k, v in info.items()}
doc_types = info.get("CFBundleDocumentTypes", [])
utis = {u: (d.get("CFBundleTypeRole"), d.get("LSHandlerRank")) for d in doc_types for u in d.get("LSItemContentTypes", [])}
need = {"com.adobe.pdf": "Editor", "org.openxmlformats.wordprocessingml.document": "Viewer",
        "org.openxmlformats.spreadsheetml.sheet": "Viewer"}
miss = [u for u, role in need.items() if utis.get(u, (None,))[0] != role]
ranks = sorted({r for _, r in utis.values()})
minos = info.get("LSMinimumSystemVersion", "")


def ver(s):
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3]) or (99,)


check("T1.5 bundle id", info.get("CFBundleIdentifier") == "in.sthraas.chuvadi.reader", info.get("CFBundleIdentifier", ""))
check("T1.5 copyright", info.get("NSHumanReadableCopyright") == "Copyright © 2026 Sthraas Intelligence Pvt Ltd. All rights reserved.",
      info.get("NSHumanReadableCopyright", ""))
check("T1.5 document types", not miss and ranks == ["Alternate"], f"missing/wrong role: {miss}; ranks {ranks}", utis=utis)
check("T1.5 LSMinimumSystemVersion ≤ 12.0", minos != "" and ver(minos) <= (12, 0, 0), f"LSMinimumSystemVersion={minos!r}")
check("T1.5 UIDeviceFamily 6 (Mac idiom)", info.get("UIDeviceFamily") == [6], str(info.get("UIDeviceFamily")))
check("T1.5 versions", bool(info.get("CFBundleShortVersionString")) and bool(info.get("CFBundleVersion")),
      f"{info.get('CFBundleShortVersionString')} ({info.get('CFBundleVersion')})")
for k in ["UIRequiredDeviceCapabilities", "UISupportedInterfaceOrientations", "UILaunchStoryboardName", "NSAppTransportSecurity"]:
    if k in info:
        R.setdefault("notes", []).append(f"Info.plist has {k} = {info[k]}")

# ---- file inventory
asm = {}
for line in open(asm_tsv, encoding="utf-8"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 4:
        asm[parts[0]] = parts[1:]
MS_TOKENS = {"b03f5f7f11d50a3a", "cc7b13ffcd2ddd51", "7cec85d7bea7798e", "adb9793829ddae60", "31bf3856ad364e35",
             "84e04ff9cfb79065", "0738eb9f132ed756", "b77a5c561934e089"}  # Microsoft / .NET / Xamarin keys
OWN = re.compile(r"^(Chuvadi|ChuvadiReader|LiPicons)")
total = 0
for root, dirs, files in os.walk(C):
    for fn in files:
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, app)
        size = os.path.getsize(p)
        total += size
        kind = "other"
        rc, ft = run("file", "-b", p)
        if "Mach-O" in ft:
            kind = "macho"
        elif fn.endswith(".dll"):
            kind = "assembly"
        R["files"][rel] = {"size": size, "kind": kind}
        # classify
        cls = None
        if kind == "assembly":
            a = asm.get(os.path.relpath(p, os.path.join(C)), None) or asm.get(os.path.relpath(p, app)) or \
                next((v for k, v in asm.items() if p.endswith(k)), None)
            if a:
                name, version, token, company, copy = (a + ["", "", "", "", ""])[:5]
                R["files"][rel].update(name=name, token=token, company=company)
                if OWN.match(name):
                    cls = "own"
                elif token in MS_TOKENS or company.startswith("Microsoft") or name.startswith(("System.", "Microsoft.", "mscorlib", "netstandard", "WindowsBase")):
                    cls = "microsoft"
                elif name in ("Xamarin.MacCatalyst", "Microsoft.MacCatalyst"):
                    cls = "microsoft"
        elif kind == "macho":
            cls = "native"
        elif "/wwwroot/" in rel or rel.startswith("Contents/Resources/wwwroot"):
            cls = "web"
        elif "/legal/" in rel:
            cls = "legal"
        elif fn in ("Info.plist", "PkgInfo", "CodeResources") or "_CodeSignature" in rel:
            cls = "bundle"
        elif fn.endswith((".aotdata", ".aotdata.arm64", ".aotdata.x86_64")) or ".aotdata" in fn:
            cls = "aot-data"
        elif fn.endswith((".car", ".icns", ".png", ".nib", ".storyboardc", ".strings")):
            cls = "bundle-resource"
        elif fn.endswith((".json", ".xml", ".runtimeconfig.json", ".deps.json")) or fn in ("runtimeconfig.bin",):
            cls = "config"
        elif fn.endswith(".pdb"):
            cls = "pdb"
        R["files"][rel]["class"] = cls or "unknown"
        if cls in (None, "pdb"):
            R["unknown"].append(rel)
R["total_mb"] = round(total / 1e6, 1)

# ---- Mach-O (T1.4, T1.9, T1.11)
single_arch, high_minos, foreign_libs = [], [], []
for rel, f in R["files"].items():
    if f["kind"] != "macho":
        continue
    p = os.path.join(app, rel)
    _, archs = run("lipo", "-archs", p)
    _, lc = run("otool", "-l", p)
    mins = sorted(set(re.findall(r"minos (\S+)", lc)))
    plats = sorted(set(re.findall(r"platform (\S+)", lc)))
    _, libs = run("otool", "-L", p)
    linked = [l.strip().split(" (")[0] for l in libs.splitlines()[1:]]
    R["machos"][rel] = {"archs": archs, "minos": mins, "platform": plats, "linked": sorted(set(linked))}
    if not ("arm64" in archs and "x86_64" in archs):
        single_arch.append(f"{rel}: {archs}")
    for m in mins:
        # Mac Catalyst minos is the iOS-numbered version: 15.0 = macOS 12.
        if ver(m) > (15, 0, 0):
            high_minos.append(f"{rel}: minos {m}")
    for l in linked:
        if not (l.startswith(("/System/", "/usr/lib/", "@rpath/", "@executable_path/", "@loader_path/"))):
            foreign_libs.append(f"{rel} → {l}")
check("T1.4 universal (every Mach-O)", not single_arch, "; ".join(single_arch) or f"{len(R['machos'])} Mach-O files, all arm64 + x86_64")
check("T1.9 minimum OS (LC_BUILD_VERSION)", not high_minos, "; ".join(high_minos) or "every Mach-O minos ≤ maccatalyst 15.0 (= macOS 12)")
check("T1.11 linked libraries", not foreign_libs, "; ".join(foreign_libs) or "only /System, /usr/lib and in-bundle (@rpath) libraries")

# ---- assemblies
by_class = {}
for rel, f in R["files"].items():
    by_class.setdefault(f["class"], []).append(rel)
R["by_class_count"] = {k: len(v) for k, v in by_class.items()}
third = [f"{rel} ({f.get('name')}, token {f.get('token')}, {f.get('company')})" for rel, f in R["files"].items()
         if f["kind"] == "assembly" and f["class"] not in ("own", "microsoft")]
check("T1.11 no third-party assemblies", not third, "; ".join(third) or
      f"{sum(1 for f in R['files'].values() if f['kind'] == 'assembly')} assemblies: Microsoft/.NET or Arun's own")
check("T1.11 unclassified files", not R["unknown"], f"{len(R['unknown'])} files: {R['unknown'][:30]}")
own = sorted({f.get("name") for f in R["files"].values() if f.get("class") == "own"})
R["own_assemblies"] = own
check("T1.12 no test/preview code", not [n for n in own if re.search(r"Test|Preview", n or "")],
      f"own assemblies: {own}")
check("T1.12 no .pdb", not [r for r in R["files"] if r.endswith(".pdb")], "no symbol files")
devtools = [rel for rel in R["files"] if "DevTools" in rel or "WebView.Maui.DevTools" in rel]
check("T1.12 no Blazor developer tools", not devtools, str(devtools))

# ---- legal (T1.10)
L = os.path.join(C, "Resources", "legal")
pairs = {"LICENSE.txt": "LICENSE", "EULA.txt": "legal/EULA.txt", "THIRD-PARTY-NOTICES.txt": "legal/THIRD-PARTY-NOTICES.txt"}
bad = []
for f, src in pairs.items():
    p = os.path.join(L, f)
    if not os.path.exists(p) or sha(p) != sha(os.path.join(repo, src)):
        bad.append(f)
for f in ["DOTNET-RUNTIME-THIRD-PARTY-NOTICES.txt", "DOTNET-MACCATALYST-LICENSE.txt"]:
    if not os.path.exists(os.path.join(L, f)) or os.path.getsize(os.path.join(L, f)) < 1000:
        bad.append(f)
drafts = [f for f in ["LICENSE.txt", "EULA.txt"] if os.path.exists(os.path.join(L, f)) and not open(os.path.join(L, f), encoding="utf-8").readline().startswith("DRAFT")]
check("T1.10 legal texts in the bundle", not bad and not drafts, f"missing/different: {bad}; lost DRAFT line: {drafts}")
# fonts in the bundle vs notices
fonts = sorted({os.path.basename(r) for r in R["files"] if r.endswith((".woff2", ".woff", ".ttf", ".otf"))})
notices = open(os.path.join(repo, "legal/THIRD-PARTY-NOTICES.txt"), encoding="utf-8").read()
families = ["LiPi Sans", "Fraunces", "IBM Plex Mono", "Instrument Serif", "Tiro Tamil"]
R["fonts"] = fonts
check("T1.11 fonts covered by notices", all(f in notices for f in families), f"{len(fonts)} font files; families in notices: "
      + ", ".join(f for f in families if f in notices))

json.dump(R, open(out, "w"), indent=1, ensure_ascii=False)
for c in R["checks"]:
    print(f"[{c['status'].upper()}] {c['case']}: {c['note'][:300]}")
print("by class:", R["by_class_count"], "total", R["total_mb"], "MB")
