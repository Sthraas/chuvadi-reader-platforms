#!/usr/bin/env bash
# Runs the Android Test suites on the one booted emulator (test tooling only).
#   run-emulator.sh <packages-dir> <donor-dir> <out-dir> <suites: comma list of startup,design,function,robust>
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKGS="$1"; DONOR="$2"; OUT="$3"; SUITES=",$4,"
mkdir -p "$OUT"
export PYTHONUNBUFFERED=1
adb root >/dev/null 2>&1; sleep 2; adb wait-for-device
# Emulator noise off: stylus handwriting (Gboard), animations already off by the runner.
adb shell settings put secure stylus_handwriting_enabled 0
adb shell settings put system screen_off_timeout 1800000
adb shell svc power stayon true

API="$(adb shell getprop ro.build.version.sdk | tr -d '\r')"
if [ "$API" -lt 36 ] && [ -d "$DONOR" ]; then
  bash "$HERE/webview-upgrade.sh" "$DONOR" "$OUT/webview-upgrade"
fi
adb shell dumpsys webviewupdate | grep "Current WebView package" | tee "$OUT/webview.txt"

python3 "$HERE/fixtures.py" "$OUT/fixtures" > "$OUT/fixtures.txt"
# API 35 (decision (c), 9 Nov): only the WebView update screen is tested there.
if [ "$API" -lt 36 ]; then SUITES=",gate,"; fi

# 1. The Release package exactly as built (same build as the .aab): does it start? (AT-03)
adb install -r "$PKGS/chuvadi-reader-release.apk" | tee "$OUT/install-release-as-built.txt"
COMP="$(adb shell cmd package resolve-activity --brief in.chuvadi.reader | tail -1 | tr -d '\r')"
adb logcat -c
for i in 1 2 3; do adb shell am start -W -n "$COMP" >> "$OUT/as-built-launch.txt" 2>&1; sleep 4; adb shell am force-stop in.chuvadi.reader; done
adb logcat -d -v epoch > "$OUT/as-built-logcat.txt"
echo "as-built Release: $(grep -c 'FATAL EXCEPTION' "$OUT/as-built-logcat.txt") crashes in 3 launches; TotalTime lines: $(grep -c TotalTime "$OUT/as-built-launch.txt")" | tee "$OUT/as-built.txt"
adb uninstall in.chuvadi.reader >/dev/null

# 2. Release with the AT-03 test-only fix (ChuvadiReader.Platform rooted), used for every suite below until AT-03 is fixed.
REL="$PKGS/chuvadi-reader-release-at03.apk"; [ -f "$REL" ] || REL="$PKGS/chuvadi-reader-release.apk"
echo "suites run on: $(basename "$REL")" | tee "$OUT/package-under-test.txt"
adb install -r "$REL" | tee "$OUT/install-release.txt"
adb shell am start -W -n "$COMP" > /dev/null
sleep 6
PID="$(adb shell pidof in.chuvadi.reader | tr -d '\r')"
if [ -n "$PID" ] && adb shell cat /proc/net/unix | grep -q "webview_devtools_remote_$PID"; then
  echo "release build is inspectable on this image" | tee "$OUT/inspect.txt"
else
  echo "release build NOT inspectable: page-level checks use the Debug x64 build of the same composition" | tee "$OUT/inspect.txt"
  RELEASE_ONLY=1
fi

rc=0
if [[ $SUITES == *,startup,* ]]; then
  python3 "$HERE/startup.py" "$OUT/startup-release" "$OUT/fixtures/doc-12p.pdf" 12 || rc=1
fi
if [ "${RELEASE_ONLY:-0}" = 1 ]; then
  adb uninstall in.chuvadi.reader >/dev/null
  adb install -r "$PKGS/chuvadi-reader-debug-x64.apk" | tee "$OUT/install-debug.txt"
  if [[ $SUITES == *,startup,* ]]; then
    python3 "$HERE/startup.py" "$OUT/startup-debug" "$OUT/fixtures/doc-12p.pdf" 12 || rc=1
  fi
fi
adb logcat -c   # suites judge crashes from here on (the as-built AT-03 crashes are recorded above)
if [[ $SUITES == *,design,* ]]; then
  python3 "$HERE/design.py" "$OUT/design" "$OUT/fixtures/doc-12p.pdf" || rc=1
fi
if [[ $SUITES == *,function,* ]] && [ -f "$HERE/function.py" ]; then
  python3 "$HERE/function.py" "$OUT/function" "$OUT/fixtures" || rc=1
fi
if [[ $SUITES == *,function2,* ]]; then
  python3 "$HERE/function2.py" "$OUT/function2" "$OUT/fixtures" || rc=1
fi
if [[ $SUITES == *,licence,* ]]; then
  python3 "$HERE/licence.py" "$OUT/licence" "$PKGS/assemblies.txt" || rc=1
fi
if [[ $SUITES == *,drift,* ]]; then
  python3 "$HERE/drift.py" "$OUT/drift" "$OUT/fixtures" || rc=1
fi
if [[ $SUITES == *,at13,* ]]; then
  python3 "$HERE/at13.py" "$OUT/at13" "$OUT/fixtures" 5 || rc=1
fi
if [[ $SUITES == *,gate,* ]]; then
  python3 "$HERE/gate.py" "$OUT/gate" || rc=1
fi
if [[ $SUITES == *,robust,* ]] && [ -f "$HERE/robust.py" ]; then
  python3 "$HERE/robust.py" "$OUT/robust" "$OUT/fixtures" || rc=1
fi
adb logcat -d -v epoch > "$OUT/logcat.txt"
adb shell dumpsys dropbox --print > "$OUT/dropbox.txt" 2>/dev/null
grep -c -E "FATAL EXCEPTION|ANR in in.chuvadi" "$OUT/logcat.txt" > "$OUT/crash-count.txt"
exit $rc
