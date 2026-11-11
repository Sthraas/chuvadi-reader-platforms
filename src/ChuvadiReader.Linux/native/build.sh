#!/usr/bin/env bash
# Builds libchvdhost.so (the GTK 4 + WebKitGTK 6.0 shim) with the system C compiler.
#   build.sh <output .so path> [Debug|Release]
# Cross build: CC=aarch64-linux-gnu-gcc PKG_CONFIG_PATH=/usr/lib/aarch64-linux-gnu/pkgconfig build.sh ...
set -euo pipefail

out="${1:?output path}"
config="${2:-Release}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cc="${CC:-gcc}"

if ! pkg-config --exists gtk4 gtk4-unix-print webkitgtk-6.0; then
    echo "error: GTK 4 and WebKitGTK 6.0 development files are missing." >&2
    echo "       sudo apt install libgtk-4-dev libwebkitgtk-6.0-dev" >&2
    exit 1
fi

opt="-O2 -DNDEBUG"
if [ "$config" = "Debug" ]; then opt="-O0 -g"; fi

mkdir -p "$(dirname "$out")"
# shellcheck disable=SC2046
"$cc" -std=c11 $opt -fPIC -shared -fvisibility=hidden \
    -Wall -Wextra -Werror -Wno-unused-parameter \
    -Wl,--as-needed -Wl,-z,relro,-z,now -Wl,-soname,libchvdhost.so \
    -o "$out" "$here/chvdhost.c" \
    $(pkg-config --cflags --libs gtk4 gtk4-unix-print webkitgtk-6.0) -lm
