#!/usr/bin/env bash
# Runs the emulator test stages on the one booted emulator and fails if any fails:
#   smoke-test.sh      — install, cold start, Ui (or the WebView update screen) on screen, rotation, no crash
#   then, by the emulator's Android System WebView (D-105: the Ui needs Chromium 128+):
#   128 or newer:
#     gestures.py        — Open with, swipe, double-tap, pinch, Arrange long-press drag (real touch)
#     platform_checks.py — Open with DOCX/XLSX, Share, rotation, keyboards, printing, Back, split screen
#   older:
#     webview_gate.py    — the update screen instead of the Reader; its button leaves for Google Play
#
#   emulator-tests.sh <apk> <results-dir>
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APK="$1"
OUT="$2"

bash "$HERE/smoke-test.sh" "$APK" "$OUT/smoke"
smoke=$?
word() { [ "$1" -eq 0 ] && echo pass || echo FAIL; }

VERSION="$(adb shell dumpsys webviewupdate | sed -n 's/.*Current WebView package (name, version): ([^,]*, \([0-9][0-9]*\)\..*/\1/p' | head -1)"
echo "Android System WebView major version: ${VERSION:-unknown}"

if [ -n "$VERSION" ] && [ "$VERSION" -lt 128 ]; then
    python3 "$HERE/webview_gate.py" "$OUT/webview-gate"
    gate=$?
    echo "smoke test: $(word $smoke); WebView $VERSION < 128: update screen: $(word $gate) (Reader checks not applicable here)"
    [ $smoke -eq 0 ] && [ $gate -eq 0 ]
    exit
fi

python3 "$HERE/gestures.py" "$OUT/gestures"
gestures=$?
python3 "$HERE/platform_checks.py" "$OUT/platform"
platform=$?

echo "smoke test: $(word $smoke); gestures: $(word $gestures); platform: $(word $platform)"
[ $smoke -eq 0 ] && [ $gestures -eq 0 ] && [ $platform -eq 0 ]
