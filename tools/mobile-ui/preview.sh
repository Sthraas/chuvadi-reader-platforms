#!/usr/bin/env bash
# TESTING ONLY. Runs the Ui at a phone, tablet or desktop layout in a local Blazor Server page so it
# can be screenshotted in a headless browser. The proposed MainLayout hooks
# (docs/mobile-ui/proposal/mobile-ui-hooks-*.patch) are applied to a scratch copy of the tree;
# this branch itself never carries an edit to an existing file.
#
#   tools/mobile-ui/preview.sh phone  [port]     # also: tablet, desktop, desktop-base
#
# <layout>-base (desktop-base, phone-base, tablet-base) runs the UNCHANGED foundation tree (CHVD_BASE, default origin/platform/foundation)
# with only this preview host added — the "before" picture for the desktop pixel-identical check
# (tools/mobile-ui/compare.py compares it with "desktop").
set -euo pipefail
FF="${1:-phone}"; PORT="${2:-5180}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${CHVD_SCRATCH:-${TMPDIR:-/tmp}/chvd-mobile-preview}/$FF"
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
HOST="$SCRATCH/tests/ChuvadiReader.MobileUi.Preview"
case "$FF" in *-base)
  # The base tree as it is (CHVD_BASE, default origin/platform/foundation) with this branch's preview
  # host on top: the "before" picture for desktop pixel checks and the gesture tests.
  (cd "$ROOT" && git archive "${CHVD_BASE:-origin/platform/foundation}" | tar -x -C "$SCRATCH")
  rm -rf "$HOST" && mkdir -p "$HOST" && cp -r "$ROOT/tests/ChuvadiReader.MobileUi.Preview/." "$HOST/"
  rm -rf "$HOST/bin" "$HOST/obj"
  export CHVD_FF="${FF%-base}"
  ;;
*)
  # Copy the working tree (tracked + new files), not .git.
  (cd "$ROOT" && git ls-files -co --exclude-standard -z | xargs -0 -I{} sh -c 'if [ -e "$1" ]; then cp --parents "$1" "$0"; fi' "$SCRATCH" {})
  # Each mobile-ui-hooks-N.patch is the full set; apply only the highest N (as Android's compose.sh does).
  p=$(ls "$ROOT"/docs/mobile-ui/proposal/mobile-ui-hooks-*.patch | sort -V | tail -1)
  (cd "$SCRATCH" && git apply "$p")
  export CHVD_FF="$FF"
  ;;
esac
cd "$HOST"
dotnet build -c Release --configfile "$SCRATCH/ci/nuget.config" -warnaserror -nologo -v quiet
ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS="http://127.0.0.1:$PORT" \
  exec dotnet run -c Release --no-build
