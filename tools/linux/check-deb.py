#!/usr/bin/env python3
"""Checks a built chuvadi-reader .deb (test-only, never shipped).

  tools/linux/check-deb.py <package.deb> [...]

Fails when:
  B-01  lintian --pedantic reports anything not overridden (E, W, I or P); a file's mode is wrong (files 0644,
        executable only the apphost and .NET's createdump; folders 0755)
  B-13  IntelliSense XML or precompressed .gz/.br copies are in /usr/lib/chuvadi-reader
  B-17  the runtime is told to show resource keys instead of .NET's messages (UseSystemResourceKeys)
  B-02  a font file isn't in a copyright stanza of its own (not Files: *), or that stanza's Copyright doesn't
        name the holder in the font's own metadata (name ID 0), or its licence isn't OFL-1.1, or the OFL-1.1
        text is missing
Needs: lintian, python3-fonttools, python3-brotli (test tools).
"""
import fnmatch, os, re, stat, subprocess, sys, tarfile, tempfile

from fontTools.ttLib import TTFont

LIB = "usr/lib/chuvadi-reader/"
EXECUTABLE = {LIB + "chuvadi-reader", LIB + "createdump"}
failures = []


def fail(deb, msg):
    failures.append(f"{os.path.basename(deb)}: {msg}")


def stanzas(text):
    """DEP-5 paragraphs as dicts (continuation lines joined with newlines)."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        fields, key = {}, None
        for line in para.splitlines():
            if line.startswith((" ", "\t")) and key:
                fields[key] += "\n" + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        if fields:
            out.append(fields)
    return out


def holder_of(stanza_copyright):
    return re.sub(r"\s+", " ", stanza_copyright)


for deb in sys.argv[1:]:
    # ── lintian ──
    lint = subprocess.run(["lintian", "--pedantic", "--display-info", deb], capture_output=True, text=True)
    for line in (lint.stdout + lint.stderr).splitlines():
        if re.match(r"^[EWIPX]: ", line):
            fail(deb, "lintian: " + line)

    with tempfile.TemporaryDirectory() as root:
        subprocess.run(["dpkg-deb", "-x", deb, root], check=True)
        # ── modes ──
        for dirpath, dirs, files in os.walk(root):
            for d in dirs:
                p = os.path.join(dirpath, d)
                if not os.path.islink(p) and stat.S_IMODE(os.lstat(p).st_mode) != 0o755:
                    fail(deb, f"folder mode {oct(stat.S_IMODE(os.lstat(p).st_mode))}: {os.path.relpath(p, root)}")
            for f in files:
                p = os.path.join(dirpath, f)
                if os.path.islink(p):
                    continue
                rel = os.path.relpath(p, root)
                want = 0o755 if rel in EXECUTABLE else 0o644
                mode = stat.S_IMODE(os.lstat(p).st_mode)
                if mode != want:
                    fail(deb, f"file mode {oct(mode)} (want {oct(want)}): {rel}")
                if rel.startswith(LIB) and (rel.endswith(".xml") or ((rel.endswith(".gz") or rel.endswith(".br"))
                                                                      and os.path.exists(p.rsplit(".", 1)[0]))):
                    fail(deb, "not needed at run time: " + rel)
        # ── .NET's messages (B-17) ──
        rc = open(os.path.join(root, LIB, "chuvadi-reader.runtimeconfig.json"), encoding="utf-8").read()
        if re.search(r'"System\.Resources\.UseSystemResourceKeys"\s*:\s*true', rc):
            fail(deb, "runtimeconfig turns .NET's messages into resource keys (UseSystemResourceKeys)")
        # ── fonts and their licence ──
        copyright_text = open(os.path.join(root, "usr/share/doc/chuvadi-reader/copyright"), encoding="utf-8").read()
        paras = stanzas(copyright_text)
        if not any(p.get("License", "").startswith("OFL-1.1") and "PREAMBLE" in p.get("License", "")
                   and "DISCLAIMER" in p.get("License", "") for p in paras):
            fail(deb, "the full OFL-1.1 text is missing from the copyright file")
        file_paras = [p for p in paras if "Files" in p]
        fonts = []
        for dirpath, _, files in os.walk(os.path.join(root, LIB, "wwwroot")):
            fonts += [os.path.join(dirpath, f) for f in files if f.endswith((".woff2", ".woff", ".ttf", ".otf"))]
        if not fonts:
            fail(deb, "no fonts found (layout changed?)")
        for font in fonts:
            rel = os.path.relpath(font, root)
            match = None
            for p in file_paras:  # DEP-5: the last matching stanza wins
                if any(fnmatch.fnmatchcase(rel, pat) for pat in p["Files"].split()):
                    match = p
            if match is None or match["Files"].strip() == "*":
                fail(deb, "font has no stanza of its own: " + rel)
                continue
            meta = TTFont(font)["name"].getDebugName(0) or ""
            holder = re.sub(r"^Copyright\s+(\(c\)\s*|©\s*)?", "", meta.strip()).replace(" All rights reserved.", "")
            holder = re.sub(r"\s+", " ", holder)
            if holder not in holder_of(match["Copyright"]):
                fail(deb, f"font holder {holder!r} not in its stanza's Copyright: {rel}")
            if match.get("License", "").split("\n")[0].strip() != "OFL-1.1":
                fail(deb, "font stanza licence isn't OFL-1.1: " + rel)
        print(f"{os.path.basename(deb)}: lintian checked, {len(fonts)} fonts checked")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("all package checks passed")
