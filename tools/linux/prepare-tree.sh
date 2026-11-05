#!/usr/bin/env bash
# Builds a complete Chuvadi Reader source tree for Linux:
#   1. checks out arunshivab/chuvadi-reader at the pinned commit (unchanged),
#   2. adds this branch's NEW files (src/ChuvadiReader.Linux) on top,
#   3. fills the git-ignored ./localpackages feed from the Reader's committed ci/packages,
#   4. proves no existing Reader file was modified (git status shows only new files).
#
#   tools/linux/prepare-tree.sh [target-dir]      (default: ./reader)
set -euo pipefail

READER_REPO="https://github.com/arunshivab/chuvadi-reader.git"
READER_COMMIT="c7b9e4456a8d2a8ff7f25a50d76db9cfd7cd0e29" # main, 6 Nov 2026: chuvadi-pdf 3.31.1 + Chuvadi.Fonts 1.0.0

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
target="${1:-$here/reader}"

if [ ! -d "$target/.git" ]; then
    git init -q "$target"
    git -C "$target" remote add origin "$READER_REPO"
fi

git -C "$target" fetch -q --depth 1 origin "$READER_COMMIT"
git -C "$target" checkout -q --force "$READER_COMMIT"
git -C "$target" clean -q -fdx -e localpackages

cp -R "$here/src/ChuvadiReader.Linux" "$target/src/"

mkdir -p "$target/localpackages"
cp "$target"/ci/packages/*.nupkg "$target/localpackages/"

# Guard: only new, untracked files may differ from the pinned commit.
if [ -n "$(git -C "$target" status --porcelain --untracked-files=no)" ]; then
    echo "error: an existing chuvadi-reader file was modified:" >&2
    git -C "$target" status --short --untracked-files=no >&2
    exit 1
fi

echo "Reader tree ready at $target (chuvadi-reader $READER_COMMIT + src/ChuvadiReader.Linux)"
