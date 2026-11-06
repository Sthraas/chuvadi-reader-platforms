#!/usr/bin/env bash
# TESTING ONLY. Runs the Ui at a phone, tablet or desktop layout in a local Blazor Server page so it
# can be screenshotted in a headless browser. The proposed MainLayout hooks
# (docs/mobile-ui/proposal/mobile-ui-hooks-*.patch) are applied to a scratch copy of the tree;
# this branch itself never carries an edit to an existing file.
#
#   tools/mobile-ui/preview.sh phone  [port]     # also: tablet, desktop, desktop-base
#
# desktop-base runs the UNCHANGED foundation tree (CHVD_BASE, default origin/platform/foundation)
# with only this preview host added — the "before" picture for the desktop pixel-identical check
# (tools/mobile-ui/compare.py compares it with "desktop").
set -euo pipefail
FF="${1:-phone}"; PORT="${2:-5180}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${CHVD_SCRATCH:-${TMPDIR:-/tmp}/chvd-mobile-preview}/$FF"
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
HOST="$SCRATCH/tests/ChuvadiReader.MobileUi.Preview"
if [ "$FF" = "desktop-base" ]; then
  # The base tree as it is, plus the preview host (which links css/mobile.css: absent in the base,
  # so that link is dropped here).
  (cd "$ROOT" && git archive "${CHVD_BASE:-origin/platform/foundation}" | tar -x -C "$SCRATCH")
  mkdir -p "$HOST" && cp -r "$ROOT/tests/ChuvadiReader.MobileUi.Preview/." "$HOST/"
  sed -i '/<link rel="stylesheet" href="_content\/ChuvadiReader.Ui\/css\/mobile.css" \/>/d' "$HOST/Components/HostPage.razor"
  export CHVD_FF=desktop
else
  # Copy the working tree (tracked + new files), not .git.
  (cd "$ROOT" && git ls-files -co --exclude-standard -z | xargs -0 -I{} sh -c 'if [ -e "$1" ]; then cp --parents "$1" "$0"; fi' "$SCRATCH" {})
  for p in "$ROOT"/docs/mobile-ui/proposal/mobile-ui-hooks-*.patch; do (cd "$SCRATCH" && git apply "$p"); done
  export CHVD_FF="$FF"
fi
cd "$HOST"
dotnet build -c Release --configfile "$SCRATCH/ci/nuget.config" -warnaserror -nologo -v quiet
ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS="http://127.0.0.1:$PORT" \
  exec dotnet run -c Release --no-build
