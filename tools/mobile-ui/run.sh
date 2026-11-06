#!/usr/bin/env bash
# TESTING ONLY. Starts the preview for one layout, waits for it, shoots the given scenarios at the
# given sizes, then stops it.   run.sh <layout> <port> <outdir> "<scenario WxH> ..."
set -uo pipefail
L="$1"; PORT="$2"; OUT="$3"; shift 3
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT"
"$HERE/preview.sh" "$L" "$PORT" > "$OUT/server-$L.log" 2>&1 &
PID=$!
for i in $(seq 1 120); do
  curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/reader" 2>/dev/null | grep -q 200 && break
  kill -0 $PID 2>/dev/null || { echo "preview failed:"; tail -20 "$OUT/server-$L.log"; exit 1; }
  sleep 2
done
for spec in "$@"; do
  set -- $spec
  if [ "$1" = "gestures" ] || [ "$1" = "gestures-jitter" ]; then
    python3 "$HERE/gestures.py" "http://127.0.0.1:$PORT" "${2%x*}" "${2#*x}" "${1#gestures-}" | tee "$OUT/$1-$L-$2.txt"
  else
    python3 "$HERE/shoot.py" "http://127.0.0.1:$PORT" "$OUT" "$1" "${2%x*}" "${2#*x}"
  fi
done
pkill -f "ASPNETCORE_URLS=http://127.0.0.1:$PORT" 2>/dev/null; kill $PID 2>/dev/null; pkill -f "urls.*$PORT" 2>/dev/null
fuser -k "$PORT/tcp" 2>/dev/null; wait 2>/dev/null; true
