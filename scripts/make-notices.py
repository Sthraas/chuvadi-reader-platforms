#!/usr/bin/env python3
"""Rebuilds legal/THIRD-PARTY-NOTICES.txt from ci/packages (each package's own licence field) and the
verbatim licence texts in legal/licenses/. Run from the repository root after any package change:
    python3 scripts/make-notices.py
Testing/maintenance tool only; nothing here ships except its output."""
import glob, json, os, re, zipfile

def nuspec(path):
    z = zipfile.ZipFile(path)
    name = next(n for n in z.namelist() if n.endswith('.nuspec'))
    return z.read(name).decode('utf-8-sig')

def tag(s, t):
    m = re.search(f'<{t}>([^<]*)</{t}>', s)
    return m.group(1) if m else ''

rows = {}
for p in sorted(glob.glob('ci/packages/*.nupkg')):
    s = nuspec(p)
    lic = (re.search(r'<license type="expression">([^<]*)', s) or [None, 'not stated'])[1]
    repo = (re.search(r'<repository[^>]*url="([^"]+)"', s) or [None, ''])[1]
    who = tag(s, 'copyright') or tag(s, 'authors')
    rows.setdefault((lic, repo, who), []).append(f"{tag(s, 'id')} {tag(s, 'version')}")

def text(name):
    return open(f'legal/licenses/{name}', encoding='utf-8-sig').read().strip() + '\n'

fonts = [('Fraunces', 'OFL-fraunces.txt'), ('IBM Plex Mono', 'OFL-ibmplexmono.txt'),
         ('Instrument Serif', 'OFL-instrumentserif.txt'), ('Tiro Tamil', 'OFL-tirotamil.txt')]

# ── Android app only (D-143): the libraries .NET MAUI bundles, listed by scripts/resolve-android-packages.py ──
ANDROID_FILE = 'legal/android/maui-android-packages.json'
ANDROID = json.load(open(ANDROID_FILE, encoding='utf-8')) if os.path.exists(ANDROID_FILE) else None

# Upstream copyright holders (neither the packages nor the Java binaries carry a copyright line). Each group's
# licence is as Microsoft's notice in every one of its packages states it. [confirm] = for counsel to confirm.
ANDROID_GROUPS = [
    ('AndroidX (Jetpack) libraries', lambda i: i.startswith('Xamarin.AndroidX.'), 'Apache License 2.0', 'Copyright The Android Open Source Project'),
    ('Material Components for Android', lambda i: i == 'Xamarin.Google.Android.Material', 'Apache License 2.0', 'Copyright The Android Open Source Project'),
    ('Kotlin standard library, kotlinx.coroutines, kotlinx.serialization', lambda i: i.startswith(('Xamarin.Kotlin.', 'Xamarin.KotlinX.')), 'Apache License 2.0', 'Copyright JetBrains s.r.o. and Kotlin Programming Language contributors'),
    ('JetBrains Java annotations', lambda i: i == 'Xamarin.Jetbrains.Annotations', 'Apache License 2.0', 'Copyright JetBrains s.r.o.'),
    ('Google Tink (through AndroidX Security, for MAUI SecureStorage)', lambda i: i == 'Xamarin.Google.Crypto.Tink.Android', 'Apache License 2.0', 'Copyright Google LLC'),
    ("Glide (MAUI's image loader), with its DiskLruCache, GifDecoder and annotations", lambda i: i.startswith('Xamarin.Android.Glide'), 'Simplified BSD License and Apache License 2.0', "Copyright 2014 Google, Inc. (Glide); DiskLruCache: Copyright Jake Wharton and The Android Open Source Project; GifDecoder: as stated in Glide's LICENSE [confirm]"),
    ('Gson', lambda i: i == 'GoogleGson', 'Apache License 2.0', 'Copyright 2008 Google Inc.'),
    ('Guava ListenableFuture', lambda i: i == 'Xamarin.Google.Guava.ListenableFuture', 'Apache License 2.0', 'Copyright The Guava Authors'),
    ('Error Prone annotations', lambda i: i == 'Xamarin.Google.ErrorProne.Annotations', 'Apache License 2.0', 'Copyright The Error Prone Authors'),
    ('JSR 305 annotations (FindBugs)', lambda i: i == 'Xamarin.Google.Code.FindBugs.JSR305', 'Apache License 2.0', 'Copyright the JSR 305 contributors [confirm]'),
    ('JSpecify annotations', lambda i: i == 'Xamarin.JSpecify', 'Apache License 2.0', 'Copyright The JSpecify Authors'),
]


def android_section():
    """The Android-only part of the notices: each group, its packages and versions, licence and holder."""
    if not ANDROID:
        return ['(no Android package list: run scripts/resolve-android-packages.py)']
    pkgs = ANDROID['packages']
    lines = [f".NET MAUI {ANDROID['maui']} brings these Java and Kotlin libraries into the Android app, each through",
             "Microsoft's .NET binding package of the same name (the bindings: MIT, Copyright (c) Microsoft Corporation).",
             'None of them collects data or reaches the network; the app has no INTERNET permission. Licence texts below.', '']
    used = set()
    for title, match, lic, who in ANDROID_GROUPS:
        group = [p for p in pkgs if match(p['id'])]
        if not group:
            continue
        used.update(p['id'] for p in group)
        lines.append(f'* {title}  -  {lic}  -  {who}')
        lines += [f"    {p['id']} {p['version']}" for p in group]
        lines.append('')
    rest = [p['id'] for p in pkgs if p['id'] not in used]
    if rest:
        raise SystemExit('Android packages with no group in make-notices.py: ' + ', '.join(rest))
    return lines

rule = '=' * 92
out = ["""DRAFT, to be reviewed by counsel. Check against the final package list before each release.

CHUVADI READER - THIRD-PARTY NOTICES

Copyright © 2026 Sthraas Intelligence Pvt Ltd. All rights reserved.

Chuvadi Reader is proprietary software of Sthraas Intelligence Pvt Ltd (see LICENSE and the EULA). It
includes the components below, each licensed by its owner under the terms named. Those terms apply to
those components; nothing in Chuvadi Reader's licence limits them.

Generated by scripts/make-notices.py from the packages in ci/packages (each package's own licence
field) and the verbatim licence texts in legal/licenses/.
""", rule, 'COMPONENTS', rule, '']
for (lic, repo, who), ids in sorted(rows.items()):
    out.append(f"* {lic}  -  {who or 'copyright not stated in the package'}  -  {repo or 'no repository stated'}")
    out += [f'    {i}' for i in ids]
    if ids[0].startswith('LiPicons.Blazor'):
        out.append('    Known item: the package names imagiQa Healthcare Services Pvt Ltd and states no licence. Its')
        out.append('    copyright is being transferred to Sthraas Intelligence Pvt Ltd (Arun, 7 Nov 2026); the package')
        out.append('    will be updated by its own repository.')
    out.append('')
out += ["""* MIT  -  Copyright (c) .NET Foundation and Contributors  -  https://github.com/dotnet
    Microsoft.AspNetCore.Components.Web, Microsoft.AspNetCore.Components.WebView.Wpf (Windows),
    and the .NET runtime and libraries where a host ships them self-contained (Linux, macOS,
    Android). Such hosts also ship .NET's own ThirdPartyNotices.txt from the runtime they bundle.

* Microsoft Edge WebView2 Runtime (Windows) - not included: Windows provides it.

* SIL Open Font License 1.1  -  display fonts in the app's interface (wwwroot/fonts/google)
    Fraunces, IBM Plex Mono, Instrument Serif, Tiro Tamil - each with its own copyright, below.

* SIL Open Font License 1.1  -  LiPi Sans (Inter + Noto Sans), in the interface
  (wwwroot/lipi-sans) and in Chuvadi.Fonts / Chuvadi.Pdf.Fonts.Bundled
""", rule, 'ANDROID APP ONLY - libraries .NET MAUI bundles (D-143)', rule, *android_section(), '', rule, 'MIT LICENSE (Chuvadi.Docs, Chuvadi.Sheets, Chuvadi.Zip, Chuvadi.Print, Chuvadi.Print.Ipp, Chuvadi.Fonts code,\nMicrosoft and .NET components; each with the copyright line shown above)', rule, text('MIT-dotnet.txt'),
        rule, 'APACHE LICENSE 2.0 (chuvadi-pdf: Chuvadi.Pdf.* and Chuvadi.Cryptography, Copyright © 2025 Chuvadi Contributors;\nand in the Android app the AndroidX, Material, Kotlin, Tink, Glide, Gson and annotation libraries, each with the copyright line shown above)', rule, text('Apache-2.0.txt'),
        rule, 'SIL OPEN FONT LICENSE 1.1 - LiPi Sans', rule, text('OFL-lipi-sans.txt')]
for family, f in fonts:
    out += [rule, f'SIL OPEN FONT LICENSE 1.1 - {family}', rule, text(f)]
if ANDROID:
    out += [rule, 'SIMPLIFIED BSD LICENSE (Glide, Android app only)', rule, text('BSD-2-Clause-glide.txt')]
open('legal/THIRD-PARTY-NOTICES.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('legal/THIRD-PARTY-NOTICES.txt:', sum(len(v) for v in rows.values()), 'packages,', len(fonts) + 1, 'font licences')
