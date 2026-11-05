#!/usr/bin/env bash
# Launch test for a published Linux build, under Xvfb + mutter (both test-only tools).
# Passes when Blazor reports its first render within the time limit and no error is logged.
# Leaves startup timings and a screenshot in the output folder.
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
dbus-run-session -- mutter --x11 --replace >"$out/mutter.log" 2>&1 &
wm=$!
sleep 3

cleanup() {
    kill "$wm" "$xvfb" 2>/dev/null || true
}
trap cleanup EXIT

status=0
for i in $(seq 1 "$runs"); do
    log="$out/run-$i.log"
    CHUVADI_TIMING=1 dbus-run-session -- "$app/chuvadi-reader" >"$log" 2>&1 &
    pid=$!

    rendered=0
    for _ in $(seq 1 300); do # 30 s
        if grep -q "blazor first render" "$log"; then
            rendered=1
            break
        fi
        sleep 0.1
    done

    if [ "$rendered" = 1 ] && [ "$i" = 1 ]; then
        sleep 2 # let the page settle for the screenshot
        import -window root "$out/home.png"
    fi

    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true

    if [ "$rendered" != 1 ]; then
        echo "run $i: no first render within 30 s" >&2
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
