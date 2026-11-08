#!/usr/bin/env bash
# On a booted API 36 emulator: pull its Android System WebView (and Trichrome library, if split)
# so the API 35 emulators can be updated to a WebView >= 128, as real Android 15 devices are through
# Play (D-105). Test tooling only.   webview-donor.sh <out-dir>
set -uo pipefail
OUT="$1"; mkdir -p "$OUT"
adb root >/dev/null 2>&1; sleep 2; adb wait-for-device
adb shell dumpsys webviewupdate > "$OUT/webviewupdate-36.txt"
for p in com.google.android.trichromelibrary com.google.android.webview; do
  i=0
  for path in $(adb shell pm path "$p" 2>/dev/null | sed 's/package://' | tr -d '\r'); do
    adb pull "$path" "$OUT/$p-$i.apk" && i=$((i+1))
  done
done
# Trichrome library is a static shared library (pm hides it): find its .apk on disk.
i=0
for path in $(adb shell 'find /data/app /product /system /system_ext -name "*.apk" 2>/dev/null' | tr -d '\r' | grep -i trichrome); do
  adb pull "$path" "$OUT/com.google.android.trichromelibrary-$i.apk" && i=$((i+1))
done
adb shell pm list libraries > "$OUT/libraries-36.txt"
# Packages, for the record.
adb shell pm list packages -f --show-versioncode | grep -i -E "webview|trichrome" > "$OUT/packages-36.txt"
ls -la "$OUT"
