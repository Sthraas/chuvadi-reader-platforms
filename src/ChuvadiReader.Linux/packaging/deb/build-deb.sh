#!/usr/bin/env bash
# Builds the Chuvadi Reader .deb for the machine's own architecture (amd64 or arm64).
#
#   src/ChuvadiReader.Linux/packaging/deb/build-deb.sh <out dir> [--framework-dependent]
#
# Default: self-contained (the .NET runtime inside the package; decision pending with the
# coordinator — see docs/linux/README.md). --framework-dependent depends on Ubuntu's
# dotnet-runtime-10.0 package instead.
#
# Layout:
#   /usr/lib/chuvadi-reader/                 the published app (ReadyToRun) + libchvdhost.so
#   /usr/bin/chuvadi-reader                  symlink to the app
#   /usr/share/applications/in.chuvadi.Reader.desktop   menu entry, PDF/DOCX/XLSX associations
#   /usr/share/icons/hicolor/<n>x<n>/apps/in.chuvadi.Reader.png   from the Windows app's chuvadi.ico
#   /usr/share/metainfo/in.chuvadi.Reader.metainfo.xml  software-centre description
#   /etc/apparmor.d/chuvadi-reader           lets WebKit's sandbox start (Ubuntu 24.04+)
#
# Needs: the .NET 10 SDK, gcc, GTK 4 / WebKitGTK 6.0 dev packages, dpkg-dev (dpkg-shlibdeps), python3.
set -euo pipefail

out="${1:?out dir}"
mode="self-contained"
[ "${2:-}" = "--framework-dependent" ] && mode="framework-dependent"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$here/../.." && pwd)"           # src/ChuvadiReader.Linux
root="$(cd "$project/../.." && pwd)"           # repository root
version="1.0.0~preview"                        # the Ui shows v1.0.0-preview; '~' sorts before 1.0.0
pkg="chuvadi-reader"
appid="in.chuvadi.Reader"                      # placeholder until Arun's final domain (as Mac/Android IDs)

case "$(uname -m)" in
    x86_64) arch=amd64; rid=linux-x64 ;;
    aarch64) arch=arm64; rid=linux-arm64 ;;
    *) echo "error: unsupported machine $(uname -m)" >&2; exit 1 ;;
esac

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
stage="$work/root"
lib="$stage/usr/lib/$pkg"
mkdir -p "$lib" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/metainfo" \
         "$stage/usr/share/doc/$pkg" "$stage/etc/apparmor.d" "$stage/DEBIAN"

# 1. Publish (ReadyToRun, D-50).
selfc=$([ "$mode" = "self-contained" ] && echo true || echo false)
dotnet publish "$project/ChuvadiReader.Linux.csproj" -c Release -r "$rid" --self-contained "$selfc" \
    -p:PublishReadyToRun=true -o "$lib" -warnaserror -nologo -v quiet
rm -f "$lib"/*.pdb
# .NET's optional LTTng tracing hook: it links liblttng-ust.so.0, which Ubuntu 24.04+ no longer ships, and
# .NET runs without it (Microsoft's guidance: remove it when LTTng tracing isn't used).
rm -f "$lib/libcoreclrtraceptprovider.so"
ln -s "../lib/$pkg/chuvadi-reader" "$stage/usr/bin/chuvadi-reader"

# 2. Desktop integration.
install -m 644 "$project/packaging/desktop/$appid.desktop" "$stage/usr/share/applications/"
install -m 644 "$project/packaging/desktop/$appid.metainfo.xml" "$stage/usr/share/metainfo/"
install -m 644 "$here/copyright" "$stage/usr/share/doc/$pkg/copyright"

# Icons: the PNG images inside the Windows app's icon, copied byte for byte (no re-encoding).
python3 -I - "$root/src/ChuvadiReader.Windows/chuvadi.ico" "$stage/usr/share/icons/hicolor" "$appid" <<'PY'
import os, struct, sys
ico, dest, name = sys.argv[1:4]
data = open(ico, "rb").read()
_, kind, count = struct.unpack_from("<HHH", data, 0)
assert kind == 1, "not an icon file"
for i in range(count):
    w, h, _, _, _, _, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
    w, h = w or 256, h or 256
    png = data[offset:offset + size]
    assert png[:8] == b"\x89PNG\r\n\x1a\n", f"{w}x{h} entry is not PNG"
    folder = os.path.join(dest, f"{w}x{h}", "apps")
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, name + ".png"), "wb").write(png)
PY

# 3. AppArmor profile for the installed path.
sed "s#@CHUVADI_BINARY@#/usr/lib/$pkg/chuvadi-reader#" "$project/packaging/apparmor/chuvadi-reader" \
    > "$stage/etc/apparmor.d/chuvadi-reader"
chmod 644 "$stage/etc/apparmor.d/chuvadi-reader"
echo "/etc/apparmor.d/chuvadi-reader" > "$stage/DEBIAN/conffiles"

# 4. Dependencies: what the native libraries link to (dpkg-shlibdeps), plus what .NET loads at run time.
mkdir -p "$work/shlib/debian"
printf 'Source: %s\n\nPackage: %s\nArchitecture: any\n' "$pkg" "$pkg" > "$work/shlib/debian/control"
mapfile -t natives < <(find "$lib" -maxdepth 1 -name '*.so' -type f)
[ -f "$lib/chuvadi-reader" ] && natives+=("$lib/chuvadi-reader")
if ! shlibs="$(cd "$work/shlib" && dpkg-shlibdeps -O "${natives[@]/#/-e}" 2>"$work/shlibdeps.log" | sed -n 's/^shlibs:Depends=//p')" || [ -z "$shlibs" ]; then
    echo "error: dpkg-shlibdeps failed:" >&2
    grep -v warning "$work/shlibdeps.log" >&2 || true
    exit 1
fi
if [ "$mode" = "self-contained" ]; then
    # ICU and OpenSSL are loaded by .NET at run time (not linked): 24.04 has ICU 74, 26.04 ICU 78.
    runtime="libicu74 | libicu78, libssl3t64"
else
    runtime="dotnet-runtime-10.0"
fi
depends="$shlibs, $runtime"

# 5. Maintainer scripts: load / unload the AppArmor profile (desktop, MIME and icon caches are
#    refreshed by dpkg triggers of desktop-file-utils, shared-mime-info and hicolor-icon-theme).
cat > "$stage/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
if [ "$1" = "configure" ] && command -v apparmor_parser >/dev/null 2>&1 && [ -d /sys/kernel/security/apparmor ]; then
    apparmor_parser -r -T -W /etc/apparmor.d/chuvadi-reader || true
fi
SH
cat > "$stage/DEBIAN/postrm" <<'SH'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v apparmor_parser >/dev/null 2>&1 && [ -d /sys/kernel/security/apparmor ] && [ ! -e /etc/apparmor.d/chuvadi-reader ]; then
        echo "profile chuvadi-reader {}" | apparmor_parser -R 2>/dev/null || true
    fi
fi
SH
chmod 755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/postrm"

size="$(du -sk --exclude=DEBIAN "$stage" | cut -f1)"
cat > "$stage/DEBIAN/control" <<EOF
Package: $pkg
Version: $version
Architecture: $arch
Maintainer: Sthraas Intelligence Pvt Ltd <maintainer@chuvadi.in>
Installed-Size: $size
Depends: $depends
Recommends: cups, xdg-desktop-portal-gtk | xdg-desktop-portal-kde
Section: graphics
Priority: optional
Homepage: https://chuvadi.in
Description: PDF viewer and editor, Word and Excel viewer
 Chuvadi Reader reads, marks, arranges and protects PDF documents and views
 Word and Excel files. Everything is processed on this device.
 .
 Build: $mode, ReadyToRun, GTK 4 + WebKitGTK 6.0.
EOF

mkdir -p "$out"
deb="$out/${pkg}_${version}_${arch}.deb"
dpkg-deb --root-owner-group -Zxz --build "$stage" "$deb" >/dev/null
echo "$deb"
dpkg-deb --info "$deb" | sed -n '/Package:/,/Description:/p'
