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

# The shipped Release package, as Play would deliver it (universal .apk from the same build).
adb install -r "$PKGS/chuvadi-reader-release.apk" | tee "$OUT/install-release.txt"
COMP="$(adb shell cmd package resolve-activity --brief in.chuvadi.reader | tail -1 | tr -d '\r')"
adb shell am start -W -n "$COMP" > /dev/null
sleep 6
PID="$(adb shell pidof in.chuvadi.reader | tr -d '\r')"
if adb shell cat /proc/net/unix | grep -q "webview_devtools_remote_$PID"; then
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
if [[ $SUITES == *,design,* ]]; then
  python3 "$HERE/design.py" "$OUT/design" "$OUT/fixtures/doc-12p.pdf" || rc=1
fi
if [[ $SUITES == *,function,* ]] && [ -f "$HERE/function.py" ]; then
  python3 "$HERE/function.py" "$OUT/function" "$OUT/fixtures" || rc=1
fi
if [[ $SUITES == *,robust,* ]] && [ -f "$HERE/robust.py" ]; then
  python3 "$HERE/robust.py" "$OUT/robust" "$OUT/fixtures" || rc=1
fi
adb logcat -d -v epoch > "$OUT/logcat.txt"
adb shell dumpsys dropbox --print > "$OUT/dropbox.txt" 2>/dev/null
grep -c -E "FATAL EXCEPTION|ANR in in.chuvadi" "$OUT/logcat.txt" > "$OUT/crash-count.txt"
exit $rc
