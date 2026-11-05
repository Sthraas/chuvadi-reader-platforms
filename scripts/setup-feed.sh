#!/usr/bin/env bash
# Builds the local NuGet feed the solution's nuget.config expects at ./localpackages.
#
#   * chuvadi-pdf 3.31.1: packed from the UNCHANGED tag v3.31.1 (chuvadi-pdf has no release assets).
#   * Other Chuvadi packages: downloaded from github.com/arunshivab/chuvadi releases, SHA-256 checked
#     against the library coordinator's report (6 Nov 2026) where it gives one.
#   * LiPicons.Blazor 1.1.0: copied from the repo's own ci/packages (Arun's package, committed there).
#
# Usage: scripts/setup-feed.sh            (run from anywhere; needs git, curl, sha256sum, dotnet 10)
# Never modifies library code. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FEED="$ROOT/localpackages"
WORK="${CHUVADI_FEED_WORK:-${TMPDIR:-/tmp}/chuvadi-feed-work}"
PDF_TAG="v3.31.1"
PDF_VERSION="3.31.1"
REL="https://github.com/arunshivab/chuvadi/releases/download"

mkdir -p "$FEED" "$WORK"

# --- chuvadi-pdf, packed from the tag -------------------------------------------------------
if [ ! -f "$FEED/Chuvadi.Pdf.Documents.$PDF_VERSION.nupkg" ]; then
  rm -rf "$WORK/chuvadi-pdf"
  git clone -q --depth 1 --branch "$PDF_TAG" https://github.com/arunshivab/chuvadi-pdf "$WORK/chuvadi-pdf"
  # Same as chuvadi-pdf's build/fetch-fonts.ps1: Chuvadi.Fonts into its git-ignored .fonts-feed, SHA-256 checked.
  mkdir -p "$WORK/chuvadi-pdf/.fonts-feed"
  curl -sSfL -o "$WORK/chuvadi-pdf/.fonts-feed/Chuvadi.Fonts.1.0.0.nupkg" "$REL/fonts-v1.0.0/Chuvadi.Fonts.1.0.0.nupkg"
  echo "c15a82d1caa3d70f3e2abe16dd94201ea1d3dae91764735a19ffa7398c37f5fe  $WORK/chuvadi-pdf/.fonts-feed/Chuvadi.Fonts.1.0.0.nupkg" | sha256sum -c --quiet -
  # Same command as chuvadi-pdf's own build/pack.ps1.
  dotnet pack "$WORK/chuvadi-pdf/Chuvadi.slnx" -c Release -p:Version="$PDF_VERSION" -o "$FEED" --nologo -v quiet
  if [ -n "$(git -C "$WORK/chuvadi-pdf" status --porcelain)" ]; then
    echo "chuvadi-pdf working tree changed during pack — refusing to continue" >&2
    exit 1
  fi
fi

# --- released Chuvadi packages ---------------------------------------------------------------
# tag | file | sha256 (empty = not published in the coordinator's report; recorded in BUILD-LOG)
PACKAGES=(
  "fonts-v1.0.0|Chuvadi.Fonts.1.0.0.nupkg|c15a82d1caa3d70f3e2abe16dd94201ea1d3dae91764735a19ffa7398c37f5fe"
  "sheets-v2.0.1|Chuvadi.Sheets.2.0.1.nupkg|417f537f74826deeb8cd14492441800243b45df9e714cd9ce6daf9138571c253"
  "zip-v1.0.0|Chuvadi.Zip.1.0.0.nupkg|e019f9b61d48d705e9b8e81e3ca8bcbb3114056b2127f4e9ea2af0aa51110104"
  "markup-v1.0.0|Chuvadi.Markup.1.0.0.nupkg|3257478005d2a159e8cf9d88899876dd75a419b8d2cd7d7d6b6754f9213a4192"
  "print-v1.0.0-rc.2|Chuvadi.Print.1.0.0-rc.2.nupkg|"
  "print-v1.0.0-rc.2|Chuvadi.Print.Ipp.1.0.0-rc.2.nupkg|"
  "print-v1.0.0-rc.2|Chuvadi.Print.Windows.1.0.0-rc.2.nupkg|"
  "print-v1.0.0-rc.2|Chuvadi.Print.Remote.1.0.0-rc.2.nupkg|"
)
for entry in "${PACKAGES[@]}"; do
  IFS='|' read -r tag file sha <<< "$entry"
  if [ ! -f "$FEED/$file" ]; then
    curl -sSfL -o "$FEED/$file.part" "$REL/$tag/$file"
    mv "$FEED/$file.part" "$FEED/$file"
  fi
  if [ -n "$sha" ]; then
    echo "$sha  $FEED/$file" | sha256sum -c --quiet - || { echo "checksum mismatch: $file" >&2; exit 1; }
  fi
done

# --- packages the current app pins that only exist in the repo's committed CI feed ----------
# LiPicons.Blazor (Arun's icon package) and, until the Reader chat moves to Docs 2.0 / Sheets 2.0.1,
# the Docs 1.1.0 and Sheets 1.1.2 that ChuvadiReader.Core pins today.
for f in LiPicons.Blazor.1.1.0.nupkg Chuvadi.Docs.1.1.0.nupkg Chuvadi.Sheets.1.1.2.nupkg; do
  [ -f "$FEED/$f" ] || cp "$ROOT/ci/packages/$f" "$FEED/$f"
done

echo "Feed ready: $(ls "$FEED"/*.nupkg | wc -l) packages in $FEED"
