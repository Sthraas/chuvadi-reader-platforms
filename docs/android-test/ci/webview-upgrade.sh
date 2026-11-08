#!/usr/bin/env bash
# On an API 35 emulator: install the API 36 image's WebView (see webview-donor.sh) as an update.
# Prints the WebView version before and after. Test tooling only.   webview-upgrade.sh <donor-dir> <out-dir>
set -uo pipefail
DONOR="$1"; OUT="$2"; mkdir -p "$OUT"
adb shell dumpsys webviewupdate > "$OUT/webviewupdate-before.txt"
for f in "$DONOR"/com.google.android.trichromelibrary-*.apk; do
  [ -e "$f" ] && adb install -r -d "$f" >> "$OUT/install.txt" 2>&1
done
WV=( "$DONOR"/com.google.android.webview-*.apk )
if [ ${#WV[@]} -gt 1 ]; then adb install-multiple -r -d "${WV[@]}" >> "$OUT/install.txt" 2>&1
elif [ -e "${WV[0]}" ]; then adb install -r -d "${WV[0]}" >> "$OUT/install.txt" 2>&1; fi
sleep 3
adb shell dumpsys webviewupdate > "$OUT/webviewupdate-after.txt"
cat "$OUT/install.txt"
grep -h "Current WebView package" "$OUT"/webviewupdate-*.txt
