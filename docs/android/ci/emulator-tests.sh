#!/usr/bin/env bash
# Runs both emulator test stages on the one booted emulator and fails if either fails:
#   smoke-test.sh — install, cold start, Ui on screen, real rotation, no crash / console error
#   gestures.py   — Open with, swipe, double-tap, pinch, Arrange long-press drag (real touch)
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

echo "smoke test: $([ $smoke -eq 0 ] && echo pass || echo FAIL); gestures: $([ $gestures -eq 0 ] && echo pass || echo FAIL)"
[ $smoke -eq 0 ] && [ $gestures -eq 0 ]
