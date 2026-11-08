#!/usr/bin/env bash
# B-15 test (test-only, never shipped): where new user namespaces are refused, Chuvadi must show a plain
# message window and exit with code 2 — not abort, hang or show a blank window.
#   tools/linux/no-userns-test.sh <publish dir> <out dir>
# Needs Xvfb, mutter, xdotool, ImageMagick, dbus, python3-seccomp (test tools).
set -uo pipefail
app="$1"; out="$2"; mkdir -p "$out"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DISPLAY=:86
Xvfb :86 -screen 0 1280x800x24 >/dev/null 2>&1 & xvfb=$!
sleep 1
bus_info="$(dbus-daemon --session --fork --print-address=1 --print-pid=1)"
export DBUS_SESSION_BUS_ADDRESS="$(sed -n 1p <<<"$bus_info")"; bus="$(sed -n 2p <<<"$bus_info")"
mutter --x11 --replace >/dev/null 2>&1 & wm=$!
sleep 2
cleanup() { kill "$wm" "$xvfb" "$bus" 2>/dev/null; }
trap cleanup EXIT

home="$(mktemp -d)"
HOME="$home" XDG_CONFIG_HOME="$home/.config" /usr/bin/python3 "$here/no-userns.py" "$app/chuvadi-reader" 2>"$out/stderr.txt" &
pid=$!
window=""
for _ in $(seq 60); do
    sleep 0.25
    window="$(xdotool search --onlyvisible --name "" 2>/dev/null | while read -r w; do
        xdotool getwindowpid "$w" 2>/dev/null | grep -qx "$pid" && echo "$w"; done | head -1)"
    [ -n "$window" ] && break
    kill -0 "$pid" 2>/dev/null || break
done
sleep 1
import -window root "$out/no-userns.png" 2>/dev/null
fail=0
[ -n "$window" ] || { echo "FAIL no window from the app"; fail=1; }
grep -q "Chuvadi can't start on this computer" "$out/stderr.txt" || { echo "FAIL no message on stderr"; fail=1; }
xdotool windowactivate --sync "$window" 2>/dev/null; sleep 0.5; xdotool key Return 2>/dev/null
for _ in $(seq 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
if kill -0 "$pid" 2>/dev/null; then echo "FAIL still running after Close"; kill "$pid"; fail=1; code=-1; else wait "$pid"; code=$?; fi
[ "$code" = 2 ] || { echo "FAIL exit code $code (want 2)"; fail=1; }
grep "Chuvadi can't start" "$out/stderr.txt" | cut -c1-220
[ "$fail" = 0 ] && echo "PASS: message window shown, exit 2"
exit "$fail"
