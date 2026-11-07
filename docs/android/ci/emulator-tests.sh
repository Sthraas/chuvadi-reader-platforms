#!/usr/bin/env bash
# Runs the emulator test stages on the one booted emulator and fails if any fails:
#   smoke-test.sh — install, cold start, Ui on screen, real rotation, no crash / console error
#   gestures.py   — Open with, swipe, double-tap, pinch, Arrange long-press drag (real touch)
#   platform_checks.py — Open with DOCX/XLSX, Share to, rotation with a document, hardware and soft
#                   keyboard, printing (PrintManager → saved PDF), back, split screen
#
#   emulator-tests.sh <apk> <results-dir>
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APK="$1"
OUT="$2"

bash "$HERE/smoke-test.sh" "$APK" "$OUT/smoke"
smoke=$?
python3 "$HERE/gestures.py" "$OUT/gestures"
gestures=$?
python3 "$HERE/platform_checks.py" "$OUT/platform"
platform=$?

word() { [ "$1" -eq 0 ] && echo pass || echo FAIL; }
echo "smoke test: $(word $smoke); gestures: $(word $gestures); platform: $(word $platform)"
[ $smoke -eq 0 ] && [ $gestures -eq 0 ] && [ $platform -eq 0 ]
