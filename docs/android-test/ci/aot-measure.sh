#!/usr/bin/env bash
# Cold Open with → page 1 for each variant (10 runs) + the traced timeline (test tooling only).
#   aot-measure.sh <variants-dir> <out-dir>
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; V="$1"; mkdir -p "$2"; OUT="$(cd "$2" && pwd)"
adb root >/dev/null 2>&1; sleep 2; adb wait-for-device
adb shell settings put system screen_off_timeout 1800000; adb shell svc power stayon true
python3 "$HERE/fixtures.py" "$OUT/fx" > /dev/null
for v in baseline chuvadi fullaot; do
  [ -f "$V/$v.apk" ] || { echo "$v: no apk"; continue; }
  adb uninstall in.chuvadi.reader >/dev/null 2>&1
  adb install -r "$V/$v.apk" > /dev/null
  ONLY_OPEN=1 python3 "$HERE/startup.py" "$OUT/$v" "$OUT/fx/doc-12p.pdf" 10
done
if [ -f "$V/trace.apk" ]; then
  adb uninstall in.chuvadi.reader >/dev/null 2>&1
  adb install -r "$V/trace.apk" > /dev/null
  python3 "$HERE/trace.py" "$OUT/trace" "$OUT/fx/doc-12p.pdf" 10
fi
python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
for v in ("baseline", "chuvadi", "fullaot"):
    p = os.path.join(out, v, "summary.json")
    if os.path.exists(p):
        for t in json.load(open(p))["summary"]:
            if t["kind"] == "open-with-cold" and t["n"]:
                print(v, t)
PY
