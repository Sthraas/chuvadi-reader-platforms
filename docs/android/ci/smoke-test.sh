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
# The Ui's mode labels, or (WebView older than 128, D-105) the host's update screen.
MARKERS='text="(Read|Mark|Arrange|Protect)( [0-9])?"|text="Settings"|text="One small update first"'
mkdir -p "$OUT"
fail=0

adb wait-for-device
# "device" is reported before Android has finished booting; wait until the package manager answers.
for i in $(seq 1 60); do
  if [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = "1" ] && adb shell pm path android >/dev/null 2>&1; then break; fi
  sleep 5
done
adb shell settings put system accelerometer_rotation 0
adb shell settings put system user_rotation 0
adb logcat -c

echo "Installing $APK"
installed=0
for attempt in 1 2 3; do
  if adb install -r "$APK"; then installed=1; break; fi
  echo "install attempt $attempt failed; retrying"
  sleep 10
done
[ "$installed" -eq 1 ] || { echo "::error::install failed"; exit 1; }

echo "Cold start"
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null

# The CI emulators render in software and their own System UI sometimes stops responding, which
# covers the screen with "System UI isn't responding" (not our app). Tap "Wait" whenever it shows.
dismiss_system_anr() {
  local xml="$1" b
  grep -qE "isn.t responding" "$xml" || return 1
  b="$(grep -oE 'text="Wait"[^>]*bounds="\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]"' "$xml" | grep -oE '\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]' | head -1)"
  [ -n "$b" ] || return 1
  read -r x1 y1 x2 y2 <<<"$(echo "$b" | tr -c '0-9' ' ')"
  echo "System UI ANR dialog on screen (emulator); tapping Wait"
  adb shell input tap $(((x1 + x2) / 2)) $(((y1 + y2) / 2))
  sleep 2
  return 0
}

# Dumps the screen's UI tree to $1, first clearing any System UI ANR dialog.
dump_ui() {
  local xml="$1" i
  for i in 1 2 3; do
    adb exec-out uiautomator dump /dev/tty > "$xml" 2>/dev/null || true
    dismiss_system_anr "$xml" || return 0
  done
}

# Wait for the Ui to render.
rendered=0
for i in $(seq 1 24); do
  sleep 5
  dump_ui "$OUT/ui-portrait.xml"
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

# Width x height of a PNG screenshot, read from its header (stdlib only).
png_size() { python3 -c 'import struct,sys; d=open(sys.argv[1],"rb").read(24); print("%dx%d" % struct.unpack(">II", d[16:24]))' "$1"; }

echo "Rotate (activity must survive: no restart, Ui still there)"
# A quarter turn from the natural orientation (phones start portrait, tablets landscape), through the
# window manager's own rotation lock; the screenshot size must then change.
rot=1
adb shell cmd window user-rotation lock "$rot" 2>/dev/null || adb shell settings put system user_rotation "$rot"
sleep 10
pid_after="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
adb exec-out screencap -p > "$OUT/rotated.png" || true
dump_ui "$OUT/ui-rotated.xml"
echo "before $(png_size "$OUT/portrait.png"), after $(png_size "$OUT/rotated.png")"
if [ "$(png_size "$OUT/portrait.png")" = "$(png_size "$OUT/rotated.png")" ]; then
  echo "::error::the screen did not rotate (still $(png_size "$OUT/rotated.png")); rotation was not tested"
  fail=1
fi
if [ -z "$pid_after" ] || [ "$pid_before" != "$pid_after" ]; then
  echo "::error::the app did not survive rotation (pid $pid_before -> $pid_after)"
  fail=1
elif ! grep -qE "$MARKERS" "$OUT/ui-rotated.xml"; then
  echo "::error::the Ui is gone after rotation"
  fail=1
fi
adb shell cmd window user-rotation lock 0 2>/dev/null || adb shell settings put system user_rotation 0

adb logcat -d > "$OUT/logcat.txt"
# Only our app's own failures count: a managed crash ("Process: <pkg>"), a native crash
# ("Fatal signal … (<pkg>)") or an ANR. Other processes' crashes (e.g. the uiautomator tool itself)
# are kept as evidence but don't fail the test.
grep -E "AndroidRuntime: Process: $PKG|Fatal signal .*\($PKG\)|ANR in $PKG" "$OUT/logcat.txt" > "$OUT/crashes.txt"
grep -E "FATAL EXCEPTION|Fatal signal|ANR in " "$OUT/logcat.txt" > "$OUT/other-process-crashes.txt" || true
grep -E "chromium: \[INFO:CONSOLE" "$OUT/logcat.txt" | grep -iE "error|failed|uncaught" > "$OUT/console-errors.txt"
if [ -s "$OUT/crashes.txt" ]; then echo "::error::crash in logcat"; cat "$OUT/crashes.txt"; fail=1; fi
if [ -s "$OUT/console-errors.txt" ]; then echo "::error::WebView console errors"; cat "$OUT/console-errors.txt"; fail=1; fi

exit "$fail"
