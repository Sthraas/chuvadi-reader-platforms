#!/usr/bin/env bash
# Builds the Android test composition (sandbox and CI only — nothing here is shipped as-is):
#   1. a checkout of platform/foundation at FOUNDATION_REF (Core, Ui with the combined hooks, kit)
#   2. + platform/mobile-ui at MOBILEUI_REF, merged in (not committed). The Mobile UI branch is based on
#        an earlier Foundation; the merge brings its phone components, mobile.css and mobile.js.
#   3. + the Mobile UI chat's pending hook patch (docs/mobile-ui/proposal/mobile-ui-hooks-*.patch, the
#        highest number). PENDING Foundation's next combined patch; skipped when already applied.
#   4. + this branch's src/ChuvadiReader.Android
#
#   compose.sh <foundation-checkout (full history)> <mobile-ui-ref> <android-branch-checkout>
set -euo pipefail

READER="$(cd "$1" && pwd)"
MOBILEUI_REF="$2"
ANDROID="$(cd "$3" && pwd)"
G=(git -C "$READER" -c user.name=compose -c user.email=compose@localhost)

echo "Merge platform/mobile-ui $MOBILEUI_REF into Foundation $("${G[@]}" rev-parse --short HEAD)"
"${G[@]}" cat-file -e "$MOBILEUI_REF^{commit}" 2>/dev/null || "${G[@]}" fetch -q origin "$MOBILEUI_REF"
"${G[@]}" merge --no-commit --no-ff "$MOBILEUI_REF" >/dev/null \
    || { echo "platform/mobile-ui does not merge cleanly into Foundation"; "${G[@]}" diff --name-only --diff-filter=U; exit 1; }

PATCH="$(ls "$READER"/docs/mobile-ui/proposal/mobile-ui-hooks-*.patch 2>/dev/null | sort -V | tail -1 || true)"
if [ -n "$PATCH" ]; then
    if "${G[@]}" apply --check --whitespace=nowarn "$PATCH" 2>/dev/null; then
        echo "Mobile UI hooks: $(basename "$PATCH")"
        "${G[@]}" apply --whitespace=nowarn "$PATCH"
    elif "${G[@]}" apply --check --reverse --whitespace=nowarn "$PATCH" 2>/dev/null; then
        echo "Mobile UI hooks already in Foundation: $(basename "$PATCH")"
    else
        echo "$(basename "$PATCH") does not apply"; exit 1
    fi
fi

echo "Android host"
rm -rf "$READER/src/ChuvadiReader.Android"
mkdir -p "$READER/src/ChuvadiReader.Android"
( cd "$ANDROID/src/ChuvadiReader.Android" && tar --exclude=./bin --exclude=./obj -cf - . ) | tar -xf - -C "$READER/src/ChuvadiReader.Android"

echo "Composed in $READER"
