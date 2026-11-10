#!/bin/bash
# Mac smoke test — checks the Mac Test fixes on a real macOS runner. Usage: mac-smoke.sh /path/to/Chuvadi.app
#   M-16  the left bar's Open button → the real Open panel → the Reader, for PDF, Markdown, text, HTML, Word, Excel
#   D-132 the error log in ~/Library/Logs/Chuvadi: written, scrubbed, rolled over, about 1 MB at most
#   M-17  locked PDFs (AES-256, RC4): wrong and right passwords; M-18 Settings after the Reader and Library;
#   M-21  real ⌃⌘F / Esc in and out of Immersive; M-19 page errors reach the error log
#   D-154 WebKit's content process ends → same screen back, plain message, chuvadi.log; M-18 Accessibility press
#   M-02  files handed over by macOS open as tabs: at launch, and while running (single instance)
#   M-01  the menu bar carries Chuvadi's commands (File, View, Document), ⌘ shortcuts, no AppKit Enter Full Screen
#   M-11  Settings… ⌘, in the Chuvadi menu
#   M-04  the page reaches the window's top edge (no title-bar band)
#   M-07  the window opens at 1100×720, centred
#   M-16  the opened document shows in the Reader; no Blazor error bar, no logged errors
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

# Crash reports are counted across every quit in this run (M-03): three launches, two after typing in a field.
REPORTS=("$HOME/Library/Logs/DiagnosticReports" "/Library/Logs/DiagnosticReports")
before=$(ls "${REPORTS[@]}" 2>/dev/null | grep -c "^$EXE" || true)

# Open-panel fixtures (M-16): five-page PDF, Markdown, text, HTML, Word, Excel — minimal but valid.
python3 - "$DOCS" <<'EOF'
import sys, os, zipfile
d = sys.argv[1]
kids = " ".join("%d 0 R" % (3 + i) for i in range(5))
objs = [b"<< /Type /Catalog /Pages 2 0 R >>", ("<< /Type /Pages /Kids [%s] /Count 5 >>" % kids).encode()]
objs += [b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>"] * 5
out = bytearray(b"%PDF-1.4\n"); offs = []
for i, o in enumerate(objs, 1):
    offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
x = len(out)
out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
for o in offs: out += b"%010d 00000 n \n" % o
out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
open(os.path.join(d, "five-pages.pdf"), "wb").write(out)
open(os.path.join(d, "notes.md"), "w").write("# Notes\n\nA *Markdown* file.\n\n- one\n- two\n")
open(os.path.join(d, "plain.txt"), "w").write("A plain text file.\nSecond line.\n")
open(os.path.join(d, "page.html"), "w").write("<!doctype html><html><body><h1>Page</h1><p>An HTML file.</p></body></html>\n")
ct = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>%s</Types>'
rel = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="%s"/></Relationships>'
with zipfile.ZipFile(os.path.join(d, "letter.docx"), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct % '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>')
    z.writestr("_rels/.rels", rel % "word/document.xml")
    z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>A Word file.</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>')
with zipfile.ZipFile(os.path.join(d, "table.xlsx"), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct % ('<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'))
    z.writestr("_rels/.rels", rel % "xl/workbook.xml")
    z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
    z.writestr("xl/worksheets/sheet1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Name</t></is></c><c r="B1"><v>42</v></c></row></sheetData></worksheet>')
EOF

quit_app() {
  cat > "$RUNNER_TEMP/quit.swift" <<SW
import AppKit
for app in NSRunningApplication.runningApplications(withBundleIdentifier: "$BUNDLE_ID") { _ = app.terminate() }
SW
  xcrun swift "$RUNNER_TEMP/quit.swift"
  local end=$((SECONDS + 40)); while pgrep -f "$APP/Contents/MacOS/$EXE" >/dev/null && [ $SECONDS -lt $end ]; do sleep 0.5; done
  ! pgrep -f "$APP/Contents/MacOS/$EXE" >/dev/null
}

# --- M-16: the left bar's Open button → the real Open panel → the Reader, for every format --------------
PICKS="five-pages.pdf notes.md plain.txt page.html letter.docx table.xlsx"
PICK_ENV=$(for f in $PICKS; do printf '%s;' "$DOCS/$f"; done)
rm -f "$LOG"
LOGDIR="$HOME/Library/Logs/Chuvadi"; rm -rf "$LOGDIR"
open -n --env CHUVADI_SMOKE=1 --env CHUVADI_SMOKE_LOGFILL=1 --env "CHUVADI_SMOKE_PICK=$PICK_ENV" --stdout "$LOG" --stderr "$LOG" -a "$APP"
wait_for 'CHUVADI tabs 6: ' 150 || true
sleep 3   # the last Ui report comes 1.5 s after the tab
grep -E 'CHUVADI (open-button|picked|tabs|ui) ' "$LOG"
i=0
for f in $PICKS; do
  i=$((i + 1))
  line=$(grep "CHUVADI ui " "$LOG" | sed -n "${i}p")
  if grep -q "CHUVADI tabs $i: .*$f" "$LOG" && [[ "$line" == *"route=/reader"* && "$line" == *"reader=1"* && "$line" == *"errorbar=none"* ]]; then
    pass "M-16 Open button → panel → $f shows in the Reader"
  else
    fail "M-16 Open panel $f: ${line:-no Ui report}"
  fi
done
hl=$(grep "CHUVADI ui " "$LOG" | sed -n "4p")
[[ "$hl" == *'frame="Page'* && "$hl" == *"An HTML file"* ]] && pass "HTML viewer shows the document in its frame" \
  || fail "HTML viewer frame: ${hl:-no Ui report}"
if grep -qE 'CHUVADI log (Error|Critical)' "$LOG"; then
  fail "M-16 the Ui logged errors on the Open-panel path"; grep -E 'CHUVADI log (Error|Critical)' "$LOG" | head -5 | tr '⏎' '\n' | head -80
fi
cp "$LOG" "$PWD/smoke-open-panel.log"

# --- D-132: the Mac error log — present, scrubbed, rolled over, about 1 MB at most --------------------------
ls -l "$LOGDIR" 2>/dev/null
if [ -f "$LOGDIR/chuvadi.log" ]; then
  pass "D-132 error log written to ~/Library/Logs/Chuvadi"
  total=$(cat "$LOGDIR"/*.log | wc -c | tr -d ' ')
  [ "$total" -le 1100000 ] && pass "D-132 log total $total bytes (≤ ~1 MB)" || fail "D-132 log total $total bytes"
  [ -f "$LOGDIR/chuvadi.1.log" ] && pass "D-132 log rolled over to chuvadi.1.log" || fail "D-132 no roll-over after 1.3 MB of warnings"
  leaks=$(cat "$LOGDIR"/*.log | grep -cE "smoke-secret-name|smoke-hunter2|/Users/|five-pages|notes\.md|plain\.txt|page\.html|letter\.docx|table\.xlsx" || true)
  [ "${leaks:-0}" = "0" ] && pass "D-132 log holds no file names, paths or quoted secrets" || { fail "D-132 log leaks ($leaks lines)"; cat "$LOGDIR"/*.log | grep -E "smoke-secret-name|smoke-hunter2|/Users/|five-pages|notes|plain|page\.html|letter|table" | head -5; }
  grep -h "smoke-check" "$LOGDIR"/*.log | head -1
  grep -h "smoke-check" "$LOGDIR"/*.log | grep -qE '<\.pdf #[0-9a-f]{8}>.*<text #[0-9a-f]{8}>' && pass "D-132 names become extension + hash, secrets a hash" \
    || fail "D-132 smoke-check entry not in the expected scrubbed form"
  cp -R "$LOGDIR" "$PWD/chuvadi-logs" 2>/dev/null || true
else
  fail "D-132 no error log at $LOGDIR"
fi
quit_app || fail "Open-panel run did not quit"
sleep 2

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
KEYS="$RUNNER_TEMP/keys"
xcrun swiftc -O -o "$KEYS" "$SCRIPTS/keys.swift" && sudo python3 "$SCRIPTS/grant-post-event.py" "$KEYS"

# native_watch <seconds>: posts what the app asks for ("CHUVADI native-key …"): a real key, an Accessibility press
# ("ax-press:Label"), or ending WebKit's content process ("kill-webcontent"). Runs until "steps done".
native_watch() {
  local seen=0 end=$((SECONDS + $1)) n k
  while [ $SECONDS -lt $end ]; do
    n=$(grep -c "CHUVADI native-key " "$LOG" 2>/dev/null || true)
    if [ "${n:-0}" -gt "$seen" ]; then
      seen=$((seen + 1))
      k=$(grep "CHUVADI native-key " "$LOG" | sed -n "${seen}p" | sed 's/.*native-key //')
      case "$k" in
        kill-webcontent) pkill -9 -f com.apple.WebKit.WebContent && echo "killed WebKit's content process" ;;
        ax-press:*) "$KEYS" "$BUNDLE_ID" ax-press "${k#ax-press:}" ;;
        *) "$KEYS" "$BUNDLE_ID" "$k" ;;
      esac
    fi
    grep -q "CHUVADI steps done" "$LOG" 2>/dev/null && break
    sleep 0.3
  done
}

# --- M-18 / D-154: WebKit's content process ends → the same screen comes back, with a message and a log entry ----
wcrep() { ls "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports 2>/dev/null | grep -c "WebContent" || true; }
wc_before=$(wcrep)
rm -f "$LOG"; rm -rf "$LOGDIR"
open -n --env CHUVADI_SMOKE=1 \
  --env "CHUVADI_SMOKE_STEPS=click:Settings;click:Appearance;native:kill-webcontent;wait;wait;native:ax-press:Appearance;wait;wait" \
  --stdout "$LOG" --stderr "$LOG" -a "$APP"
native_watch 180 &
NW=$!
wait_for 'CHUVADI steps done' 180 || fail "M-18 recovery steps did not finish"
wait $NW 2>/dev/null || true
grep -E "CHUVADI (step|webcontent|log Error)|ax-press|killed" "$LOG" | cut -c1-600
s=$(grep -E "CHUVADI step 2 click: route=" "$LOG" | tail -1)
[[ "$s" == *"route=/settings"* && "$s" == *"errorbar=none"* ]] && pass "M-18 Settings › Appearance (click)" || fail "M-18 Appearance: ${s:-no report}"
grep -q "CHUVADI webcontent-ended" "$LOG" && pass "D-154 the content process's end is noticed" || fail "D-154 the content process's end went unnoticed"
s=$(grep -E "CHUVADI step 5 wait: route=" "$LOG" | tail -1)
[[ "$s" == *"route=/settings"* && "$s" == *"errorbar=none"* ]] && pass "D-154 the Ui comes back on the same screen" || fail "D-154 after the content process ended: ${s:-no report}"
m=$(grep -E "CHUVADI step 3 native: route=" "$LOG" | tail -1)   # the message is a toast; it fades after a few seconds
[[ "$m" == *"notice=1"* ]] && pass "D-154 a plain message says it was reopened" || fail "D-154 no message after reopening: ${m:-no report}"
grep -h "content process ended" "$LOGDIR"/*.log 2>/dev/null | head -1 | grep -q . && pass "D-154 chuvadi.log records it" || fail "D-154 not in chuvadi.log"
grep -h "content process ended" "$LOGDIR"/*.log 2>/dev/null | head -2
ended=$(grep -c "CHUVADI webcontent-ended" "$LOG" || true)
s=$(grep -E "CHUVADI step 8 wait: route=" "$LOG" | tail -1)
if [ "${ended:-0}" -ge 2 ]; then
  echo "M-18 note: the Accessibility press on Appearance ended WebKit's content process (the macOS 26 trigger reproduced)"
else
  echo "M-18 note: the Accessibility press on Appearance did not end the content process here"
fi
[[ "$s" == *"errorbar=none"* ]] && pass "M-18 after an Accessibility press on Appearance the Ui lives" || fail "M-18 after the Accessibility press: ${s:-no report}"
sleep 5
wc_after=$(wcrep)
if [ "$wc_after" -gt "$wc_before" ]; then
  for d in "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports; do
    ls -t "$d" 2>/dev/null | grep WebContent | head -1 | while read -r f; do echo "== $d/$f"; grep -oE '"symbol":"[^"]+"' "$d/$f" | head -16; cp "$d/$f" "$PWD/" 2>/dev/null; done
  done
fi
cp "$LOG" "$PWD/smoke-appearance.log"; cp -R "$LOGDIR" "$PWD/chuvadi-logs-recovery" 2>/dev/null || true
quit_app || fail "recovery run did not quit"
sleep 2

# --- M-21 / M-15 on the tester's path: two documents through the Open panel, then real ⌃⌘F, Esc and ⌘O ----------
for k in k1 k2 k3 locked; do cp "$DOCS/five-pages.pdf" "$DOCS/$k.pdf"; done   # names no other phase opens
chmod 000 "$DOCS/locked.pdf"   # M-14: an unreadable file — the Ui shows .NET's own message for it
rm -f "$LOG"
open -n --env CHUVADI_SMOKE=1 --env "CHUVADI_SMOKE_PICK=$DOCS/k1.pdf;$DOCS/k2.pdf;$DOCS/k3.pdf;$DOCS/locked.pdf" \
  --env "CHUVADI_SMOKE_STEPS=native:cmd-o;wait;pick;native:ctrl-cmd-f;native:escape;native:cmd-o;wait;pick;wait;native:ctrl-tab;native:ctrl-shift-tab;native:cmd-1" \
  --stdout "$LOG" --stderr "$LOG" -a "$APP"
native_watch 180 &
NW=$!
wait_for 'CHUVADI steps done' 180 || fail "M-21/M-15 steps did not finish"
wait $NW 2>/dev/null || true
grep -E "CHUVADI (step [0-9]+ native|immersive|menu-command|tabs|picked|log Error)" "$LOG" | cut -c1-400
grep -qE "CHUVADI tabs [0-9]+: (.*, )?k1\.pdf" "$LOG" && pass "M-15 real ⌘O on Home, first thing after launch, opens the file" || fail "M-15 ⌘O on Home opened nothing"
s=$(grep -E "CHUVADI step 4 native: route=" "$LOG" | tail -1)
[[ "$s" == *"immersive=1"* ]] && pass "M-21 after the Open panel, real ⌃⌘F enters Immersive" || fail "M-21 ⌃⌘F after the Open panel: ${s:-no report}"
s=$(grep -E "CHUVADI step 5 native: route=" "$LOG" | tail -1)
[[ "$s" == *"immersive=0"* ]] && pass "M-21 after the Open panel, real Esc leaves Immersive" || fail "M-21 Esc after the Open panel: ${s:-no report}"
grep -qE "CHUVADI tabs [0-9]+: .*k3\.pdf" "$LOG" && pass "M-15 real ⌘O in the Reader opens the file" || fail "M-15 ⌘O in the Reader opened nothing"
s=$(grep -E "CHUVADI step 3 pick: route=" "$LOG" | tail -1)
[[ "$s" == *'immersiveTip="Immersive (⌃⌘F)"'* ]] && pass "M-09 the View rail labels Immersive ⌃⌘F" || fail "M-09 View rail label: ${s:-no report}"
s=$(grep -E "CHUVADI step 9 wait: route=" "$LOG" | tail -1)
[[ "$s" == *"dotnet=text"* ]] && pass "M-14 an unreadable file shows .NET's message as text" || fail "M-14 unreadable file: ${s:-no report}"
act() { grep -E "CHUVADI step $1 [a-z]+: route=" "$LOG" | tail -1 | sed -E 's/.* active=//; s/ sent=.*//'; }
a9=$(act 9); a10=$(act 10); a11=$(act 11); a12=$(act 12)
first=$(grep -E "CHUVADI tabs [0-9]+: " "$LOG" | tail -1 | sed -E 's/.*CHUVADI tabs [0-9]+: //; s/, .*//')
echo "active: before=$a9 ⌃Tab=$a10 ⌃⇧Tab=$a11 ⌘1=$a12 (first tab $first)"
[ -n "$a10" ] && [ "$a10" != "$a9" ] && pass "M-08 real ⌃Tab moves to another tab" || fail "M-08 ⌃Tab left the tab at $a10"
[ -n "$a11" ] && [ "$a11" = "$a9" ] && pass "M-08 real ⌃⇧Tab moves back" || fail "M-08 ⌃⇧Tab: $a11 (expected $a9)"
[ -n "$a12" ] && [ "$a12" = "$first" ] && pass "M-23 real ⌘1 goes to the first tab" || fail "M-23 ⌘1: $a12 (expected $first)"
chmod 644 "$DOCS/locked.pdf"
cp "$LOG" "$PWD/smoke-keys.log"
quit_app || fail "keys run did not quit"
sleep 2

# --- M-08 / M-23 in Mac Test's state: files handed over by macOS, the window without a first responder, then real
# ⌃Tab, ⌃⇧Tab and ⌘1 — judged by the tab strip on the page, as a person (and Mac Test's screenshots) see it ---------
for k in t1 t2; do cp "$DOCS/five-pages.pdf" "$DOCS/$k.pdf"; done
rm -f "$LOG"
open -n --env CHUVADI_SMOKE=1 --env "CHUVADI_SMOKE_STEPS=wait;wait;unfocus;native:ctrl-tab;native:ctrl-shift-tab;native:cmd-1" \
  --stdout "$LOG" --stderr "$LOG" -a "$APP" "$DOCS/t1.pdf" "$DOCS/t2.pdf"
native_watch 180 &
NW=$!
wait_for 'CHUVADI steps done' 180 || fail "M-08 tab-key steps did not finish"
wait $NW 2>/dev/null || true
grep -E "CHUVADI (step [0-9]+ [a-z]+:|page-key|webview-focus)" "$LOG" | cut -c1-500
strip() { grep -E "CHUVADI step $1 [a-z]+: route=" "$LOG" | tail -1 | sed -E 's/.* strip=("[^"]*"|-).*/\1/'; }
first=$(grep -E "CHUVADI step 6 [a-z]+: route=" "$LOG" | tail -1 | sed -E 's/.* strip1=("[^"]*"|-).*/\1/')
s3=$(strip 3); s4=$(strip 4); s5=$(strip 5); s6=$(strip 6)
echo "tab strip: before=$s3 ⌃Tab=$s4 ⌃⇧Tab=$s5 ⌘1=$s6 (first $first)"
grep -q "CHUVADI step 3 unfocus: resigned=True" "$LOG" && echo "(the WebView had given up the keyboard before the keys)"
[ -n "$s4" ] && [ "$s4" != "-" ] && [ "$s4" != "$s3" ] && pass "M-08 without a first responder, real ⌃Tab changes the tab on screen" || fail "M-08 ⌃Tab: strip $s3 → $s4"
[ -n "$s5" ] && [ "$s5" = "$s3" ] && pass "M-08 real ⌃⇧Tab changes it back on screen" || fail "M-08 ⌃⇧Tab: strip $s5 (expected $s3)"
[ -n "$s6" ] && [ "$s6" = "$first" ] && pass "M-23 real ⌘1 shows the first tab on screen" || fail "M-23 ⌘1: strip $s6 (expected $first)"
cp "$LOG" "$PWD/smoke-tabkeys.log"
quit_app || fail "tab-key run did not quit"
sleep 2

# --- M-17 / M-18 / M-21 / M-19: the tester's sequences, scripted --------------------------------------------
# Locked PDFs (qpdf: a testing tool, never shipped), a real-key sender with Post Event access, then one launch that
# walks: page error → locked AES-256 file → wrong password → right password (each with a real Return) → real ⌃⌘F →
# real Esc → another mode → Document ▾ → Esc → real ⌘K → Esc → Library → Settings → RC4 file → right password. After each step the app reports the page.
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
command -v qpdf >/dev/null || brew install qpdf >/dev/null 2>&1 || true
qpdf --encrypt user1 own1 256 -- "$DOCS/five-pages.pdf" "$DOCS/aes256.pdf"
qpdf --allow-weak-crypto --encrypt user1 own1 40 -- "$DOCS/five-pages.pdf" "$DOCS/rc4.pdf"
rm -f "$LOG"; rm -rf "$LOGDIR"
STEPS="jserror;pick;pw:wrong;pw:user1;native:ctrl-cmd-f;native:escape;mode:2;click:Document;native:escape;native:cmd-k;native:escape;click:Library;click:Settings;pick;pw:user1"
open -n --env CHUVADI_SMOKE=1 --env "CHUVADI_SMOKE_PICK=$DOCS/aes256.pdf;$DOCS/rc4.pdf" --env "CHUVADI_SMOKE_STEPS=$STEPS" \
  --stdout "$LOG" --stderr "$LOG" -a "$APP"
native_watch 300 &
WATCH=$!
wait_for 'CHUVADI steps done' 300 || fail "scripted steps did not finish"
wait $WATCH 2>/dev/null || true
grep -E "CHUVADI (step|native-key|log )" "$LOG" | cut -c1-700
step() { grep -E "CHUVADI step $1 [a-z]+: route=" "$LOG" | tail -1; }
ok_ui() { [[ "$1" == *"errorbar=none"* ]]; }
s=$(step 3); ok_ui "$s" && [[ "$s" == *"unlock=1"* ]] && pass "M-17 wrong password: the prompt stays, the Ui lives" || fail "M-17 wrong password: ${s:-no report}"
s=$(step 4); ok_ui "$s" && [[ "$s" == *"unlock=0"* && "$s" == *"reader=1"* ]] && pass "M-17 right password (AES-256) opens the PDF" || fail "M-17 right password: ${s:-no report}"
s=$(step 5); [[ "$s" == *"immersive=1"* ]] && pass "M-21 real ⌃⌘F enters Immersive" || fail "M-21 ⌃⌘F: ${s:-no report}"
s=$(step 6); [[ "$s" == *"immersive=0"* ]] && pass "M-21 real Esc leaves Immersive" || fail "M-21 Esc: ${s:-no report}"
s=$(step 13); ok_ui "$s" && [[ "$s" == *"route=/settings"* ]] && pass "M-18 Settings after the Reader and Library" || fail "M-18 Settings: ${s:-no report}"
s=$(step 15); ok_ui "$s" && [[ "$s" == *"unlock=0"* && "$s" == *"reader=1"* ]] && pass "M-17 right password (RC4) opens the PDF" || fail "M-17 RC4: ${s:-no report}"
# M-19: page errors reach the D-132 log, scrubbed; and every error bar seen has a logged cause.
if grep -h "smoke-page-error" "$LOGDIR"/*.log 2>/dev/null | grep -q 'PageError.*<\.pdf #[0-9a-f]\{8\}>'; then
  pass "M-19 a page error reaches ~/Library/Logs/Chuvadi, scrubbed"
else
  fail "M-19 page error not in the log: $(cat "$LOGDIR"/*.log 2>/dev/null | head -3)"
fi
grep -h "smoke-secret-name" "$LOGDIR"/*.log 2>/dev/null && fail "M-19 the page error kept a file name"
if grep -E "CHUVADI step [0-9]+ [a-z]+: route=" "$LOG" | grep -vq "errorbar=none"; then
  grep -q "PageError" "$LOGDIR"/*.log 2>/dev/null && grep -v smoke-page-error "$LOGDIR"/*.log | grep -q PageError \
    && pass "M-19 the Ui failure above is in the error log" || fail "M-19 a Ui failure left nothing in the error log"
  grep -h "PageError" "$LOGDIR"/*.log | grep -v smoke-page-error | head -3 | tr '⏎' '\n' | cut -c1-3000
fi
cp "$LOG" "$PWD/smoke-steps.log"; cp -R "$LOGDIR" "$PWD/chuvadi-logs-steps" 2>/dev/null || true
quit_app || fail "scripted run did not quit"
sleep 2


# --- M-02 (a): launched with a file (tabs saved by the run above come back first; the file is added) ---------------------------------------------------------------
rm -f "$LOG"
open -n --env CHUVADI_SMOKE=1 --stdout "$LOG" --stderr "$LOG" -a "$APP" "$DOCS/one.pdf"
if wait_for 'CHUVADI tabs [0-9]+: (.*, )?one\.pdf$' 90; then pass "M-02 a file given at launch opens as a tab"; else fail "M-02 launch file did not open"; fi

# --- M-02 (b): two more files while running — same process, two more tabs ----------------------------
open -a "$APP" "$DOCS/two.pdf" "$DOCS/three.pdf"
if wait_for 'CHUVADI tabs [0-9]+: .*one\.pdf, two\.pdf, three\.pdf$' 60; then pass "M-02 files opened while running become tabs"; else fail "M-02 running-app files did not open"; fi
n=$(pgrep -f "$APP/Contents/MacOS/$EXE" | wc -l | tr -d ' ')
[ "$n" = "1" ] && pass "single instance ($n process)" || fail "single instance: $n processes"
sleep 4   # the menu is dumped 1.5 s after the tabs change

# --- M-16: the opened document shows in the Reader, and the Ui did not fail -------------------------------
wait_for 'CHUVADI ui ' 15 || true
UI=$(grep 'CHUVADI ui ' "$LOG" | tail -1); echo "$UI"
[[ "$UI" == *"reader=1"* && "$UI" == *"errorbar=none"* ]] && pass "M-16 Reader shows the document, no Blazor error bar" \
  || fail "M-16 Ui after opening: ${UI:-no report}"
if grep -q 'CHUVADI log Error\|CHUVADI log Critical' "$LOG"; then
  fail "M-16 the Ui logged errors"; grep -E 'CHUVADI log (Error|Critical)' "$LOG" | head -5 | tr '⏎' '\n' | head -60
fi

# --- M-14: .NET messages are text, not resource keys -------------------------------------------------
T=$(grep 'CHUVADI dotnet-text' "$LOG" | tail -1); echo "$T"
[[ "$T" == *"Cannot access a disposed object"* ]] && pass "M-14 .NET messages are text" || fail "M-14 .NET message: ${T:-no report}"

# --- M-01 / M-11: the real AppKit menu bar --------------------------------------------------------
menu() { grep "CHUVADI menu $1:" "$LOG" | tail -1; }
FILE=$(menu File); VIEW=$(menu View); DOC=$(menu Document)
echo "$FILE"; echo "$VIEW"; echo "$DOC"
[[ "$FILE" == *"⌘O"* ]] && pass "M-01 File menu has Open… ⌘O" || fail "M-01 File menu: $FILE"
[[ "$FILE" == *"⌘P"* ]] && pass "M-01 File menu has Print ⌘P" || fail "M-01 File menu has no ⌘P"
items=$(echo "${DOC#*: }" | tr '|' '\n' | grep -c '[^ ]' || true)
[ "${items:-0}" -ge 3 ] && pass "M-01 Document menu has $items items" || fail "M-01 Document menu: $DOC"
[[ "$VIEW" == *"⌘K"* && "$VIEW" == *"⌃⌘F"* ]] && pass "M-01 View has ⌘K and Immersive ⌃⌘F" || fail "M-01 View menu: $VIEW"
[ -n "$VIEW" ] && [[ "$VIEW" != *"Enter Full Screen"* ]] && pass "M-01 no AppKit Enter Full Screen" || fail "M-01 View missing or still has Enter Full Screen"
grep -q 'CHUVADI menu .*Settings… ⌘,' "$LOG" && pass "M-11 Settings… ⌘, in the Chuvadi menu" || fail "M-11 no Settings… ⌘,"
grep -q 'menu-build-failed' "$LOG" && fail "menu build threw: $(grep menu-build-failed "$LOG" | tail -1)"

# --- M-04 / M-07: geometry -------------------------------------------------------------------------
GEO=$(grep 'CHUVADI geometry' "$LOG" | tail -1); WEB=$(grep 'CHUVADI webview' "$LOG" | tail -1)
echo "$GEO"; echo "$WEB"
read -r ww wh wx wy sw sh sx sy <<<"$(echo "$GEO" | sed -E 's/.*window=([0-9]+)x([0-9]+)@(-?[0-9]+),(-?[0-9]+) screen=([0-9]+)x([0-9]+)@(-?[0-9]+),(-?[0-9]+).*/\1 \2 \3 \4 \5 \6 \7 \8/')"
# 1100×720, clamped to the screen's visible area (the runner's screen is 1024×768, visible 1024×677).
ew=$(( ${sw:-0} < 1100 ? ${sw:-0} : 1100 )); eh=$(( ${sh:-0} < 720 ? ${sh:-0} : 720 ))
# Exact when the screen has room; when clamped, AppKit may shave a couple of points off the visible frame.
tol=0; { [ "$ew" -lt 1100 ] || [ "$eh" -lt 720 ]; } && tol=4
dw=$(( ${ww:-0} - ew )); dw=${dw#-}; dh=$(( ${wh:-0} - eh )); dh=${dh#-}
if [ -n "${ww:-}" ] && [ "$dw" -le "$tol" ] && [ "$dh" -le "$tol" ]; then pass "M-07 window ${ww}×${wh} (1100×720 clamped to ${sw}×${sh})"; else fail "M-07 window ${ww:-?}×${wh:-?}, expected ${ew}×${eh}"; fi
cy=$(( sy + (sh - wh) / 2 - wy )); cy=${cy#-}
[ -n "${wh:-}" ] && [ "$cy" -le 2 ] && pass "M-07 centred vertically" || fail "M-07 not centred vertically (y off by ${cy:-?})"
if [ -n "${ww:-}" ] && [ -n "${sw:-}" ]; then
  cx=$(( sx + (sw - ww) / 2 - wx )); cx=${cx#-}
  [ "$cx" -le 2 ] && pass "M-07 centred horizontally" || fail "M-07 not centred (x off by $cx)"
else
  fail "M-07 no geometry reported"
fi
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
grep -hE 'CHUVADI (quit|quit-window|quit-exception)' "$LOG" "$PWD/smoke-steps.log" "$PWD/smoke-open-panel.log" 2>/dev/null || true

echo "== ${#FAILED[@]} failed"
for f in ${FAILED[@]+"${FAILED[@]}"}; do echo " - $f"; done
[ ${#FAILED[@]} -eq 0 ]
