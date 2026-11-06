#!/usr/bin/env bash
# Android smoke test (CI only). Proves the app really works, not just that it didn't crash:
#   1. install and cold-start;
#   2. wait (up to 120 s) until the Ui's own text is on screen — read from the accessibility tree,
#      which includes the WebView's content once Blazor has rendered;
#   3. rotate; the same process must survive (no activity restart) and the Ui must still be there;
#   4. fail on any crash or WebView console error in logcat.
# Evidence (timed screenshots, UI dumps, logcat) goes to the results folder.
#
#   smoke-test.sh <apk> <results-dir>
set -uo pipefail

APK="$1"
OUT="$2"
PKG="in.chuvadi.reader"
MARKERS='(text|content-desc)="(Read|Mark|Arrange|Protect|Recent|Pinned)"'
mkdir -p "$OUT"
fail=0

adb wait-for-device
adb shell settings put system accelerometer_rotation 0
adb shell settings put system user_rotation 0
adb logcat -c

echo "Installing $APK"
adb install -r "$APK" || { echo "::error::install failed"; exit 1; }

echo "Cold start"
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null

# Wait for the Ui to render.
rendered=0
for i in $(seq 1 24); do
  sleep 5
  adb exec-out uiautomator dump /dev/tty > "$OUT/ui-portrait.xml" 2>/dev/null || true
  if grep -qE "$MARKERS" "$OUT/ui-portrait.xml"; then rendered=1; echo "Ui rendered after $((i*5)) s"; break; fi
  case $i in 2|6|12) adb exec-out screencap -p > "$OUT/portrait-$((i*5))s.png" || true ;; esac
done
adb exec-out screencap -p > "$OUT/portrait.png" || true
if [ "$rendered" -ne 1 ]; then
  echo "::error::the Ui did not appear within 120 s (see screenshots and ui-portrait.xml)"
  fail=1
fi

pid_before="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
if [ -z "$pid_before" ]; then
  echo "::error::$PKG is not running after launch"
  fail=1
fi

echo "Rotate (activity must survive: no restart, Ui still there)"
adb shell settings put system user_rotation 1
sleep 10
pid_after="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
adb exec-out screencap -p > "$OUT/rotated.png" || true
adb exec-out uiautomator dump /dev/tty > "$OUT/ui-rotated.xml" 2>/dev/null || true
if [ -z "$pid_after" ] || [ "$pid_before" != "$pid_after" ]; then
  echo "::error::the app did not survive rotation (pid $pid_before -> $pid_after)"
  fail=1
elif ! grep -qE "$MARKERS" "$OUT/ui-rotated.xml"; then
  echo "::error::the Ui is gone after rotation"
  fail=1
fi
adb shell settings put system user_rotation 0

adb logcat -d > "$OUT/logcat.txt"
grep -E "FATAL EXCEPTION|AndroidRuntime: Process: $PKG" "$OUT/logcat.txt" > "$OUT/crashes.txt"
grep -E "chromium: \[INFO:CONSOLE" "$OUT/logcat.txt" | grep -iE "error|failed|uncaught" > "$OUT/console-errors.txt"
if [ -s "$OUT/crashes.txt" ]; then echo "::error::crash in logcat"; cat "$OUT/crashes.txt"; fail=1; fi
if [ -s "$OUT/console-errors.txt" ]; then echo "::error::WebView console errors"; cat "$OUT/console-errors.txt"; fail=1; fi

exit "$fail"
