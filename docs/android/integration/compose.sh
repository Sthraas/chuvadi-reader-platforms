#!/usr/bin/env bash
# Builds the Android test composition (sandbox and CI only — nothing here is shipped as-is):
#   1. a checkout of platform/foundation at FOUNDATION_REF   (Core, Ui, Platform, Hosting)
#   2. + the Mobile app UI chat's NEW Ui files from platform/mobile-ui at MOBILEUI_REF
#        (Components/Platform/Phone/*, wwwroot/css/mobile.css, wwwroot/js/mobile.js)
#   3. + mobile-ui-on-foundation.patch: the Mobile UI hooks (MainLayout H-1/H-2) re-based on current
#        Foundation, and TouchSupport moved off the removed PlatformState cascade. PENDING: these
#        belong in Foundation's combined patch (D-26) and the Mobile UI chat's branch; this file only
#        lets Android test them now. Remove it once both have landed.
#   4. + this branch's src/ChuvadiReader.Android
#
#   compose.sh <foundation-checkout> <mobile-ui-checkout> <android-branch-checkout>
set -euo pipefail

FOUNDATION="$(cd "$1" && pwd)"
MOBILEUI="$(cd "$2" && pwd)"
ANDROID="$(cd "$3" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"

UI="$FOUNDATION/src/ChuvadiReader.Ui"
MUI="$MOBILEUI/src/ChuvadiReader.Ui"

echo "Mobile UI files → Ui"
mkdir -p "$UI/Components/Platform/Phone"
cp "$MUI"/Components/Platform/Phone/* "$UI/Components/Platform/Phone/"
cp "$MUI/wwwroot/css/mobile.css" "$UI/wwwroot/css/mobile.css"
cp "$MUI/wwwroot/js/mobile.js" "$UI/wwwroot/js/mobile.js"

echo "Hooks re-based on Foundation"
git -C "$FOUNDATION" apply --whitespace=nowarn "$HERE/mobile-ui-on-foundation.patch"

echo "Android host"
rm -rf "$FOUNDATION/src/ChuvadiReader.Android"
mkdir -p "$FOUNDATION/src/ChuvadiReader.Android"
( cd "$ANDROID/src/ChuvadiReader.Android" && tar --exclude=./bin --exclude=./obj -cf - . ) | tar -xf - -C "$FOUNDATION/src/ChuvadiReader.Android"

echo "Composed in $FOUNDATION"
