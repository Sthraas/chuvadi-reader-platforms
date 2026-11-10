#!/usr/bin/env bash
# Runs the emulator test stages on the one booted emulator and fails if any fails:
#   smoke-test.sh      — install, cold start, Ui (or the WebView update screen) on screen, rotation, no crash
#   then, by the emulator's Android System WebView (D-105: the Ui needs Chromium 128+):
#   128 or newer:
#     gestures.py        — Open with, swipe, double-tap, pinch, Arrange long-press drag (real touch)
#     platform_checks.py — Open with DOCX/XLSX, Share, rotation, keyboards, printing, Back, split screen
#   older:
#     webview_gate.py    — the update screen instead of the Reader; its button leaves for Google Play
#   and last, in both suites:
#     smoke-test.sh on the Release .apk — the trimmed build people get also installs, starts,
#     renders, rotates and doesn't crash (coordinator, 9 Nov; AT-03 was a Release-only crash)
#
#   SUITE=timeline (AT-14): instead of the checks, cold_open_timeline.py — 10 cold Open with runs of the
#     Release as shipped, then of the Chuvadi-only full AOT variant, stage by stage
#
#   [SUITE=smoke|timeline] emulator-tests.sh <debug-apk> <results-dir> [<release-apk>] [<variant-apk>]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APK="$1"
OUT="$2"
RELEASE_APK="${3:-}"
VARIANT_APK="${4:-}"

if [ "${SUITE:-full}" = timeline ]; then
    mkdir -p "$OUT"
    python3 "$HERE/make-test-pdf.py" "$OUT/cold-12p.pdf" 12 >/dev/null
    python3 "$HERE/cold_open_timeline.py" "$RELEASE_APK" shipped "$OUT/cold-12p.pdf" "$OUT/timeline" 10
    a=$?
    b=0
    if [ -f "$VARIANT_APK" ]; then
        python3 "$HERE/cold_open_timeline.py" "$VARIANT_APK" chuvadi-aot "$OUT/cold-12p.pdf" "$OUT/timeline" 10
        b=$?
    fi
    [ $a -eq 0 ] && [ $b -eq 0 ]
    exit
fi
PKG="in.chuvadi.reader"

bash "$HERE/smoke-test.sh" "$APK" "$OUT/smoke"
smoke=$?
word() { [ "$1" -eq 0 ] && echo pass || echo FAIL; }

# The Release build, on a clean install (its own data, as a person installing it would have).
release_launch() {
    [ -n "$RELEASE_APK" ] || { echo "release launch: not asked"; return 0; }
    adb uninstall "$PKG" >/dev/null 2>&1 || true
    bash "$HERE/smoke-test.sh" "$RELEASE_APK" "$OUT/release"
}

# SUITE=smoke: a quick check after a rebase, without spending a full round.
if [ "${SUITE:-full}" = smoke ]; then
    release_launch
    release=$?
    echo "smoke test: $(word $smoke); Release launch: $(word $release) (suite: smoke only)"
    [ $smoke -eq 0 ] && [ $release -eq 0 ]
    exit
fi

VERSION="$(adb shell dumpsys webviewupdate | sed -n 's/.*Current WebView package (name, version): ([^,]*, \([0-9][0-9]*\)\..*/\1/p' | head -1)"
echo "Android System WebView major version: ${VERSION:-unknown}"

if [ -n "$VERSION" ] && [ "$VERSION" -lt 128 ]; then
    python3 "$HERE/webview_gate.py" "$OUT/webview-gate"
    gate=$?
    release_launch
    release=$?
    echo "smoke test: $(word $smoke); WebView $VERSION < 128: update screen: $(word $gate) (Reader checks not applicable here); Release launch: $(word $release)"
    [ $smoke -eq 0 ] && [ $gate -eq 0 ] && [ $release -eq 0 ]
    exit
fi

python3 "$HERE/gestures.py" "$OUT/gestures"
gestures=$?
python3 "$HERE/platform_checks.py" "$OUT/platform"
platform=$?
release_launch
release=$?

echo "smoke test: $(word $smoke); gestures: $(word $gestures); platform: $(word $platform); Release launch: $(word $release)"
[ $smoke -eq 0 ] && [ $gestures -eq 0 ] && [ $platform -eq 0 ] && [ $release -eq 0 ]
