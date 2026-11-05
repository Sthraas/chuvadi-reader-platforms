#!/usr/bin/env bash
# Android smoke test (CI only): install the app, cold-start it, let the Blazor UI load, and fail
# on any crash. Saves logcat and screenshots in portrait and landscape as evidence.
#
#   smoke-test.sh <apk> <results-dir>
set -euo pipefail

APK="$1"
OUT="$2"
PKG="in.chuvadi.reader"
mkdir -p "$OUT"

adb wait-for-device
adb shell settings put system accelerometer_rotation 0
adb logcat -c

echo "Installing $APK"
adb install -r "$APK"

echo "Cold start"
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 30

fail=0
if ! adb shell pidof "$PKG" >/dev/null; then
  echo "::error::$PKG is not running 30 s after launch"
  fail=1
fi

adb exec-out screencap -p > "$OUT/portrait.png" || true

echo "Rotate to landscape (activity must survive: no restart, no crash)"
pid_before="$(adb shell pidof "$PKG" || true)"
adb shell settings put system user_rotation 1
sleep 8
pid_after="$(adb shell pidof "$PKG" || true)"
adb exec-out screencap -p > "$OUT/landscape.png" || true
if [ -z "$pid_after" ] || [ "$pid_before" != "$pid_after" ]; then
  echo "::error::the app did not survive rotation (pid $pid_before -> $pid_after)"
  fail=1
fi
adb shell settings put system user_rotation 0

adb logcat -d > "$OUT/logcat.txt"
if grep -E "FATAL EXCEPTION|AndroidRuntime: Process: $PKG|Unhandled(Exception)?" "$OUT/logcat.txt" | grep -v "^--------- beginning" > "$OUT/crashes.txt"; then
  echo "::error::crash lines found in logcat"
  cat "$OUT/crashes.txt"
  fail=1
fi

exit "$fail"
