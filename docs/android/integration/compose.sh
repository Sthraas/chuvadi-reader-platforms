#!/usr/bin/env bash
# Builds the Android test composition (sandbox and CI only — nothing here is shipped as-is):
#   1. a checkout of platform/foundation at FOUNDATION_REF (Core, Ui with the combined hooks, kit)
#   2. + platform/mobile-ui at MOBILEUI_REF, merged in (not committed). The Mobile UI branch is based on
#        an earlier Foundation; the merge brings its phone components, mobile.css and mobile.js.
#   (Mobile UI's hook patches are Foundation's to take into its combined patches; not applied here — coordinator, 9 Nov.)
#   4. + Android's pending proposals (docs/android/proposal/*.patch), PENDING Foundation's combined patch
#   5. + this branch's src/ChuvadiReader.Android
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

# 4. Android's own pending proposals for Foundation's combined patch (docs/android/proposal/*.patch),
#    so the emulators test them; skipped once Foundation has applied them.
for P in "$ANDROID"/docs/android/proposal/*.patch; do
    [ -e "$P" ] || continue
    if "${G[@]}" apply --check --whitespace=nowarn "$P" 2>/dev/null; then
        echo "Android proposal: $(basename "$P")"
        "${G[@]}" apply --whitespace=nowarn "$P"
    elif "${G[@]}" apply --check --reverse --whitespace=nowarn "$P" 2>/dev/null; then
        echo "Android proposal already in Foundation: $(basename "$P")"
    else
        echo "$(basename "$P") does not apply"; exit 1
    fi
done

echo "Android host"
rm -rf "$READER/src/ChuvadiReader.Android"
mkdir -p "$READER/src/ChuvadiReader.Android"
( cd "$ANDROID/src/ChuvadiReader.Android" && tar --exclude=./bin --exclude=./obj -cf - . ) | tar -xf - -C "$READER/src/ChuvadiReader.Android"

echo "Composed in $READER"
