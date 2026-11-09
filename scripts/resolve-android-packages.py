#!/usr/bin/env python3
"""Lists the third-party Android libraries MAUI bundles into the Android app (D-143), for the notices.

Resolves the NuGet dependency closure of Microsoft.Maui.Controls and Microsoft.AspNetCore.Components.WebView.Maui
at the MAUI version the Android workload installs, for net10.0-android, as NuGet does (lowest applicable
version, highest wins). For every package that isn't Microsoft's or .NET's own it records the version, the
licence(s) stated in the package's own THIRD-PARTY-NOTICES.txt (Microsoft's account of the Java library inside)
and the package's SHA-256. Writes legal/android/maui-android-packages.json; scripts/make-notices.py reads it.
Run again when MAUI moves:  scripts/resolve-android-packages.py 10.0.110
Dev tool only (nuget.org's public metadata); nothing here ships.
"""
import hashlib, io, json, re, sys, urllib.request, zipfile

MAUI = sys.argv[1] if len(sys.argv) > 1 else '10.0.110'
FC = 'https://api.nuget.org/v3-flatcontainer'
get = lambda u: urllib.request.urlopen(u, timeout=120).read()
cache = {}

def nuspec(pid, ver):
    k = (pid.lower(), ver.lower())
    if k not in cache:
        cache[k] = get(f'{FC}/{k[0]}/{k[1]}/{k[0]}.nuspec').decode('utf-8', 'replace')
    return cache[k]

def vkey(v):
    return [int(x) if x.isdigit() else x for x in re.split(r'[.\-]', v)]

def minver(rng):
    m = re.match(r'^[\[(]\s*([^,\])]*)', rng.strip())
    return (m.group(1) if m else rng).strip()

def score(tf):
    t = tf.lower()
    for i, p in enumerate(('net10.0-android', 'net9.0-android', 'net8.0-android')):
        if t.startswith(p):
            return 5 - i
    if 'monoandroid' in t: return 2
    if t.startswith(('net10.0', 'net9.0', 'net8.0')) and '-' not in t: return 1
    if 'netstandard' in t: return 0.5
    return -1

def deps(pid, ver):
    s = nuspec(pid, ver)
    groups = re.findall(r'<group targetFramework="([^"]*)"\s*(?:/>|>(.*?)</group>)', s, re.S)
    if not groups:
        return re.findall(r'<dependency id="([^"]+)" version="([^"]+)"', s)
    best = max(groups, key=lambda g: score(g[0]))
    return [] if score(best[0]) < 0 else re.findall(r'<dependency id="([^"]+)" version="([^"]+)"', best[1] or '')

resolved, queue = {}, [('Microsoft.Maui.Controls', MAUI), ('Microsoft.AspNetCore.Components.WebView.Maui', MAUI)]
while queue:
    pid, ver = queue.pop()
    k = pid.lower()
    if k in resolved and vkey(resolved[k][1]) >= vkey(ver):
        continue
    resolved[k] = (pid, ver)
    queue += [(d, minver(r)) for d, r in deps(pid, ver)]

out = []
for k, (pid, ver) in sorted(resolved.items()):
    if k.startswith(('microsoft.', 'system.', 'runtime.', 'netstandard')):
        continue
    data = get(f'{FC}/{k}/{ver.lower()}/{k}.{ver.lower()}.nupkg')
    z = zipfile.ZipFile(io.BytesIO(data))
    notice = next((z.read(n).decode('utf-8', 'replace') for n in z.namelist() if n.upper().endswith('THIRD-PARTY-NOTICES.TXT')), '')
    licences = [h.strip() for h in re.findall(r'^# (?!http)(.+)$', notice, re.M)]
    out.append({'id': pid, 'version': ver, 'licences': licences, 'sha256': hashlib.sha256(data).hexdigest()})

json.dump({'maui': MAUI, 'target': 'net10.0-android', 'packages': out}, open('legal/android/maui-android-packages.json', 'w'), indent=1)
print(f'MAUI {MAUI}: {len(out)} third-party Android packages -> legal/android/maui-android-packages.json')
