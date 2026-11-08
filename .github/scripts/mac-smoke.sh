#!/bin/bash
# Mac smoke test — checks the Mac Test fixes on a real macOS runner. Usage: mac-smoke.sh /path/to/Chuvadi.app
#   M-02  files handed over by macOS open as tabs: at launch, and while running (single instance)
#   M-01  the menu bar carries Chuvadi's commands (File, View, Document), ⌘ shortcuts, no AppKit Enter Full Screen
#   M-11  Settings… ⌘, in the Chuvadi menu
#   M-04  the page reaches the window's top edge (no title-bar band)
#   M-07  the window opens at 1100×720, centred
#   M-03  quitting leaves no crash report
#   M-06  prints the WebView timing breakdown
# Every check runs; the script fails at the end if any failed. Log: smoke-files.log.
set -u
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
LOG="$PWD/smoke-files.log"
BUNDLE_ID=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist")
EXE=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$APP/Contents/Info.plist")
FAILED=()
fail() { echo "FAIL: $*"; FAILED+=("$*"); }
pass() { echo "PASS: $*"; }

# wait_for <regex> <seconds>
wait_for() {
  local end=$((SECONDS + $2))
  while [ $SECONDS -lt $end ]; do grep -Eq "$1" "$LOG" 2>/dev/null && return 0; sleep 0.5; done
  return 1
}

# Three small valid PDFs (one page each), written byte-exact with a correct xref table.
DOCS="$RUNNER_TEMP/smoke-docs"; mkdir -p "$DOCS"
python3 - "$DOCS" <<'EOF'
import sys, os
for name in ("one", "two", "three"):
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>"]
    out = bytearray(b"%PDF-1.4\n"); offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs: out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    open(os.path.join(sys.argv[1], name + ".pdf"), "wb").write(out)
EOF

REPORTS=("$HOME/Library/Logs/DiagnosticReports" "/Library/Logs/DiagnosticReports")
before=$(ls "${REPORTS[@]}" 2>/dev/null | grep -c "^$EXE" || true)

# --- M-02 (a): launched with a file ---------------------------------------------------------------
rm -f "$LOG"
open -n --env CHUVADI_SMOKE=1 --stdout "$LOG" --stderr "$LOG" -a "$APP" "$DOCS/one.pdf"
if wait_for 'CHUVADI tabs 1: one\.pdf' 90; then pass "M-02 a file given at launch opens as a tab"; else fail "M-02 launch file did not open"; fi

# --- M-02 (b): two more files while running — same process, two more tabs ----------------------------
open -a "$APP" "$DOCS/two.pdf" "$DOCS/three.pdf"
if wait_for 'CHUVADI tabs 3: ' 60; then pass "M-02 files opened while running become tabs"; else fail "M-02 running-app files did not open"; fi
n=$(pgrep -f "$APP/Contents/MacOS/$EXE" | wc -l | tr -d ' ')
[ "$n" = "1" ] && pass "single instance ($n process)" || fail "single instance: $n processes"
sleep 4   # the menu is dumped 1.5 s after the tabs change

# --- M-01 / M-11: the real AppKit menu bar --------------------------------------------------------
menu() { grep "CHUVADI menu $1:" "$LOG" | tail -1; }
FILE=$(menu File); VIEW=$(menu View); DOC=$(menu Document)
echo "$FILE"; echo "$VIEW"; echo "$DOC"
[[ "$FILE" == *"⌘O"* ]] && pass "M-01 File menu has Open… ⌘O" || fail "M-01 File menu: $FILE"
[[ "$FILE" == *"⌘P"* ]] && pass "M-01 File menu has Print ⌘P" || fail "M-01 File menu has no ⌘P"
items=$(echo "${DOC#*: }" | tr '|' '\n' | grep -c '[^ ]' || true)
[ "${items:-0}" -ge 3 ] && pass "M-01 Document menu has $items items" || fail "M-01 Document menu: $DOC"
[[ "$VIEW" == *"⌘K"* && "$VIEW" == *"⌃⌘F"* ]] && pass "M-01 View has ⌘K and Immersive ⌃⌘F" || fail "M-01 View menu: $VIEW"
[[ "$VIEW" != *"Enter Full Screen"* ]] && pass "M-01 no AppKit Enter Full Screen" || fail "M-01 View still has Enter Full Screen"
grep -q 'CHUVADI menu .*Settings… ⌘,' "$LOG" && pass "M-11 Settings… ⌘, in the Chuvadi menu" || fail "M-11 no Settings… ⌘,"
grep -q 'menu-build-failed' "$LOG" && fail "menu build threw: $(grep menu-build-failed "$LOG" | tail -1)"

# --- M-04 / M-07: geometry -------------------------------------------------------------------------
GEO=$(grep 'CHUVADI geometry' "$LOG" | tail -1); WEB=$(grep 'CHUVADI webview' "$LOG" | tail -1)
echo "$GEO"; echo "$WEB"
read -r ww wh wx wy sw sh sx sy <<<"$(echo "$GEO" | sed -E 's/.*window=([0-9]+)x([0-9]+)@(-?[0-9]+),(-?[0-9]+) screen=([0-9]+)x([0-9]+)@(-?[0-9]+),(-?[0-9]+).*/\1 \2 \3 \4 \5 \6 \7 \8/')"
if [ "${ww:-0}" = "1100" ] && [ "${wh:-0}" = "720" ]; then pass "M-07 window 1100×720"; else fail "M-07 window ${ww:-?}×${wh:-?}"; fi
cx=$(( sx + (sw - ${ww:-0}) / 2 - ${wx:-0} )); cx=${cx#-}
[ "${cx:-99}" -le 2 ] && pass "M-07 centred horizontally" || fail "M-07 not centred (x off by $cx)"
top=$(echo "$WEB" | sed -E 's/.*top=(-?[0-9]+).*/\1/'); webh=$(echo "$WEB" | sed -E 's/.*height=([0-9]+).*/\1/')
[ "$top" = "0" ] && [ "$webh" = "${wh:-x}" ] && pass "M-04 page reaches the top edge (web view ${webh} of ${wh})" \
  || fail "M-04 band above the page: web view top=$top height=$webh, window height=${wh:-?}"

# --- M-06: timing breakdown -------------------------------------------------------------------------
grep -E 'CHUVADI_STARTUP|CHUVADI webtimings' "$LOG" || true

# --- M-03: quit cleanly -------------------------------------------------------------------------------
cat > "$RUNNER_TEMP/quit.swift" <<EOF
import AppKit
for app in NSRunningApplication.runningApplications(withBundleIdentifier: "$BUNDLE_ID") { _ = app.terminate() }
EOF
xcrun swift "$RUNNER_TEMP/quit.swift"
end=$((SECONDS + 40)); while pgrep -f "$APP/Contents/MacOS/$EXE" >/dev/null && [ $SECONDS -lt $end ]; do sleep 0.5; done
pgrep -f "$APP/Contents/MacOS/$EXE" >/dev/null && fail "M-03 app still running 40 s after Quit"
sleep 10   # ReportCrash writes its report a few seconds after the process ends
after=$(ls "${REPORTS[@]}" 2>/dev/null | grep -c "^$EXE" || true)
if [ "$after" -gt "$before" ]; then
  fail "M-03 quitting left a crash report"
  for d in "${REPORTS[@]}"; do ls -t "$d" 2>/dev/null | grep "^$EXE" | head -1 | while read -r f; do head -60 "$d/$f"; done; done
else
  pass "M-03 quit without a crash report"
fi
grep -E 'CHUVADI quit|quit-exception' "$LOG" || true

echo "== ${#FAILED[@]} failed"
for f in "${FAILED[@]}"; do echo " - $f"; done
[ ${#FAILED[@]} -eq 0 ]
