#!/usr/bin/env bash
# On a booted API 36 emulator: pull its Android System WebView (and Trichrome library, if split)
# so the API 35 emulators can be updated to a WebView >= 128, as real Android 15 devices are through
# Play (D-105). Test tooling only.   webview-donor.sh <out-dir>
set -uo pipefail
OUT="$1"; mkdir -p "$OUT"
adb shell dumpsys webviewupdate > "$OUT/webviewupdate-36.txt"
for p in com.google.android.trichromelibrary com.google.android.webview; do
  i=0
  for path in $(adb shell pm path "$p" 2>/dev/null | sed 's/package://' | tr -d '\r'); do
    adb pull "$path" "$OUT/$p-$i.apk" && i=$((i+1))
  done
done
# Trichrome library is a static shared library: list its exact versioned package too.
adb shell pm list packages -f --show-versioncode | grep -i -E "webview|trichrome" > "$OUT/packages-36.txt"
ls -la "$OUT"
