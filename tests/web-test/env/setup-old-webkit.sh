#!/bin/bash
# Old WebKit 17.4 (Safari 17 engine) for M-27-type checks: Playwright 1.44 in its own venv, its WebKit in /tmp/oldpw-browsers,
# with the two Ubuntu 22.04 libraries it needs (ICU 70, libvpx 7) copied into the bundle. Test tooling only, never in the product.
set -e
python3 -m venv /tmp/oldpw && /tmp/oldpw/bin/pip install -q playwright==1.44.0 pypdf
PLAYWRIGHT_BROWSERS_PATH=/tmp/oldpw-browsers PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 /tmp/oldpw/bin/python -m playwright install webkit
mkdir -p /tmp/oldlibs && cd /tmp/oldlibs
# the two .debs come from the Ubuntu 22.04 (jammy) archive; if the shell can't reach it, attach them by hand:
#   libicu70_70.1-2_amd64.deb, libvpx7_1.11.0-2ubuntu2_amd64.deb
for d in libicu70_70.1-2_amd64.deb libvpx7_1.11.0-2ubuntu2_amd64.deb; do [ -f $d ] || apt-get download ${d%%_*} ; done
for d in *.deb; do dpkg-deb -x $d x; done
for b in /tmp/oldpw-browsers/webkit-*/minibrowser-wpe/lib /tmp/oldpw-browsers/webkit-*/minibrowser-gtk/lib; do cp -a x/usr/lib/x86_64-linux-gnu/libicu*.so.70* x/usr/lib/x86_64-linux-gnu/libvpx.so.7* $b/; done
echo "Run old WebKit with: PLAYWRIGHT_BROWSERS_PATH=/tmp/oldpw-browsers PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 /tmp/oldpw/bin/python <script> ... webkit"
