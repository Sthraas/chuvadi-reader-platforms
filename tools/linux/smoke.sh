#!/usr/bin/env bash
# Launch test for a published Linux build, under Xvfb + mutter (both test-only tools).
# Passes when Blazor reports its first render within the time limit, the screen then shows the page
# (not a flat colour), and no error is logged. Leaves timings and one screenshot per run.
#
#   tools/linux/smoke.sh <publish-dir> <out-dir> [runs]
set -euo pipefail

app="${1:?publish dir}"
out="${2:?output dir}"
runs="${3:-3}"
mkdir -p "$out"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$(mktemp -d)}"
chmod 700 "$XDG_RUNTIME_DIR"
export HOME="${HOME:-$(mktemp -d)}"
export DISPLAY=:97
export GTK_A11Y=none # no accessibility bus in CI

Xvfb :97 -screen 0 1920x1080x24 >"$out/xvfb.log" 2>&1 &
xvfb=$!
sleep 1
# One session bus for every run, as a desktop session has. (A bus per launch leaves its portal
# services running after the app is stopped; they pile up and stall the machine.)
bus_info="$(dbus-daemon --session --fork --print-address=1 --print-pid=1)"
DBUS_SESSION_BUS_ADDRESS="$(sed -n 1p <<<"$bus_info")"
bus="$(sed -n 2p <<<"$bus_info")"
export DBUS_SESSION_BUS_ADDRESS
mutter --x11 --replace >"$out/mutter.log" 2>&1 &
wm=$!
sleep 3

cleanup() {
    kill "$wm" "$xvfb" 2>/dev/null || true
    kill "$bus" 2>/dev/null || true # its portals exit with it
}
trap cleanup EXIT

status=0
for i in $(seq 1 "$runs"); do
    log="$out/run-$i.log"
    CHUVADI_TIMING=1 "$app/chuvadi-reader" >"$log" 2>&1 &
    pid=$!

    rendered=0
    for _ in $(seq 1 300); do # 30 s
        if grep -q "blazor first render" "$log"; then
            rendered=1
            break
        fi
        sleep 0.1
    done

    # Blazor's first-render event proves .NET ran, not that pixels reached the screen.
    # Require a real picture: up to 10 s for the screen to show more than a flat colour.
    painted=0
    if [ "$rendered" = 1 ]; then
        for _ in $(seq 1 20); do
            sleep 0.5
            import -window root "$out/run-$i.png"
            colours=$(convert "$out/run-$i.png" -format %k info:)
            if [ "$colours" -gt 200 ]; then
                painted=1
                break
            fi
        done
        echo "run $i: screen shows $colours colours"
    fi

    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true

    if [ "$rendered" != 1 ]; then
        echo "run $i: no first render within 30 s" >&2
        status=1
    fi

    if [ "$rendered" = 1 ] && [ "$painted" != 1 ]; then
        echo "run $i: the window stayed blank (page never painted)" >&2
        status=1
    fi

    if grep -q "Chuvadi error" "$log"; then
        echo "run $i: the app logged an error" >&2
        status=1
    fi

    echo "== run $i"
    grep '\[timing\]' "$log" || true
done

exit "$status"
