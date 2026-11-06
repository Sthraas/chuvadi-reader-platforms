#!/usr/bin/env bash
# Builds the Android test composition (sandbox and CI only — nothing here is shipped as-is):
#   1. a checkout of platform/mobile-ui at MOBILEUI_REF. That branch already contains
#      platform/foundation (merged; checked below) plus the Mobile app UI chat's NEW Ui files.
#   2. + the Mobile UI chat's own hook patch (docs/mobile-ui/proposal/mobile-ui-hooks-2.patch:
#        MainLayout H-1, Reader H-3). PENDING: it belongs in Foundation's combined patch (D-26); the
#        Mobile UI branch keeps it as a proposal, so it is applied here only to test. Drop this step
#        once Foundation has applied it.
#   3. + this branch's src/ChuvadiReader.Android
#
#   compose.sh <mobile-ui-checkout> <android-branch-checkout> [foundation-ref]
set -euo pipefail

MOBILEUI="$(cd "$1" && pwd)"
ANDROID="$(cd "$2" && pwd)"
FOUNDATION_REF="${3:-}"

if [ -n "$FOUNDATION_REF" ]; then
    git -C "$MOBILEUI" merge-base --is-ancestor "$FOUNDATION_REF" HEAD \
        || { echo "platform/mobile-ui does not contain Foundation $FOUNDATION_REF"; exit 1; }
    echo "Foundation $FOUNDATION_REF is in platform/mobile-ui"
fi

PATCH="$MOBILEUI/docs/mobile-ui/proposal/mobile-ui-hooks-2.patch"
if git -C "$MOBILEUI" apply --check --whitespace=nowarn "$PATCH" 2>/dev/null; then
    echo "Mobile UI hooks (H-1, H-3)"
    git -C "$MOBILEUI" apply --whitespace=nowarn "$PATCH"
elif git -C "$MOBILEUI" apply --check --reverse --whitespace=nowarn "$PATCH" 2>/dev/null; then
    echo "Mobile UI hooks already applied"
else
    echo "mobile-ui-hooks-2.patch does not apply"; exit 1
fi

echo "Android host"
rm -rf "$MOBILEUI/src/ChuvadiReader.Android"
mkdir -p "$MOBILEUI/src/ChuvadiReader.Android"
( cd "$ANDROID/src/ChuvadiReader.Android" && tar --exclude=./bin --exclude=./obj -cf - . ) | tar -xf - -C "$MOBILEUI/src/ChuvadiReader.Android"

echo "Composed in $MOBILEUI"
