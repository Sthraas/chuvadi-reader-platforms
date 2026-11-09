#!/usr/bin/env bash
# AT-02: the shipped manifest declares only what the app uses. Reads the built package's manifest
# with aapt2 (Android SDK build tools) and fails if a removed MAUI Essentials entry is back, or if
# something the app needs is missing.
#
#   manifest-check.sh <apk-or-aab-base-apk>
set -euo pipefail
PKG_FILE="$1"
AAPT2="$(ls -d "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"/build-tools/*/aapt2 2>/dev/null | sort -V | tail -1)"
[ -x "$AAPT2" ] || { echo "aapt2 not found under \$ANDROID_HOME/build-tools"; exit 1; }

TREE="$("$AAPT2" dump xmltree --file AndroidManifest.xml "$PKG_FILE")"
fail=0

# Must be gone (AT-02): web sign-in, Essentials' file provider, connectivity / battery / energy-saver receivers.
for name in WebAuthenticatorIntermediateActivity '\.IntermediateActivity' microsoft.maui.essentials.fileProvider \
            ConnectivityBroadcastReceiver BatteryBroadcastReceiver EnergySaverBroadcastReceiver; do
    if grep -Eq "android:name\(0x01010003\)=\"[^\"]*${name}\"" <<<"$TREE"; then
        echo "FAIL still declared: $name"; fail=1
    else
        echo "PASS not declared: $name"
    fi
done

# Must stay: our own file provider (Share / clipboard), the main activity with Open-with and Share filters.
for need in 'chuvadi.reader.SharedFileProvider' 'MainActivity' 'android.intent.action.VIEW' 'android.intent.action.SEND' \
            'application/pdf' 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' \
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'; do
    if grep -Fq "$need" <<<"$TREE"; then
        echo "PASS declared: $need"
    else
        echo "FAIL missing: $need"; fail=1
    fi
done

# No permissions requested (Play data safety: the app collects nothing). The app's own signature
# permission that AndroidX defines to keep its receivers private (<package>.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION)
# isn't a request to the person. Run this on the Release package: Debug builds add INTERNET for the debugger.
PERMS="$(grep -A1 'E: uses-permission' <<<"$TREE" | sed -n 's/.*android:name(0x01010003)="\([^"]*\)".*/\1/p' | grep -v '^in\.chuvadi\.reader\.' || true)"
if [ -n "$PERMS" ]; then
    echo "FAIL permissions requested: $PERMS"; fail=1
else
    echo "PASS no permissions requested"
fi
exit $fail
