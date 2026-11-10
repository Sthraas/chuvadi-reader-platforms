#!/usr/bin/env bash
# AT-14 test-only build variants (never shipped), on a booted phone emulator:
#   baseline  = as shipped (MAUI's default profiled AOT)
#   profiled  = (a) MAUI's profile + a Chuvadi AOT profile recorded here (startup, Open with, first render)
#   fullaot   = (b) every assembly AOT-compiled (AndroidEnableProfiledAot=false)
#   aot-variants.sh <reader-checkout> <fixtures-script> <out-dir>
set -uo pipefail
READER="$(cd "$1" && pwd)"; FIXTURES="$2"; mkdir -p "$3"; OUT="$(cd "$3" && pwd)"
P="src/ChuvadiReader.Android/ChuvadiReader.Android.csproj"
C=(-c Release -f net10.0-android --no-restore "-p:AndroidSdkDirectory=$ANDROID_HOME" -p:TreatWarningsAsErrors=false)
cd "$READER"
# The profile item, switched on by a property (test-only edit of the composed csproj).
sed -i 's#</Project>#  <ItemGroup Condition="'"'"'$(AtAotProfile)'"'"' != '"'"''"'"'"><AndroidAotProfile Include="$(AtAotProfile)" /></ItemGroup>\n</Project>#' "$P"
grep -n "AtAotProfile" "$P"
clean() { rm -rf src/ChuvadiReader.Android/obj/Release src/ChuvadiReader.Android/bin/Release; }
collect() {
  find src/ChuvadiReader.Android/bin/Release -name '*-Signed.apk' -exec cp {} "$OUT/$1.apk" \;
  find src/ChuvadiReader.Android/bin/Release -name '*-Signed.aab' -exec cp {} "$OUT/$1.aab" \;
  ls -l "$OUT/$1.apk" "$OUT/$1.aab" | tee -a "$OUT/sizes.txt"
}
t=$(date +%s); clean; dotnet publish "$P" "${C[@]}" > "$OUT/build-baseline.txt" 2>&1; echo "baseline build s: $(( $(date +%s)-t ))" | tee -a "$OUT/sizes.txt"; collect baseline

# (a) record: build + install + start with the AOT profiler, use the app, collect.
python3 "$FIXTURES" "$OUT/fx" > /dev/null
clean
dotnet build "$P" "${C[@]}" -t:BuildAndStartAotProfiling > "$OUT/profiling-start.txt" 2>&1; echo "start exit $?"; tail -3 "$OUT/profiling-start.txt"
sleep 25
adb push "$OUT/fx/doc-12p.pdf" /sdcard/Download/aot-doc.pdf >/dev/null
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Download/aot-doc.pdf >/dev/null; sleep 3
ID=$(adb shell content query --uri content://media/external/downloads --projection _id --where "_display_name=\'aot-doc.pdf\'" | sed -n 's/.*_id=\([0-9]*\).*/\1/p' | tail -1)
adb shell am start -a android.intent.action.VIEW -d "content://media/external/downloads/$ID" -t application/pdf -p in.chuvadi.reader --grant-read-uri-permission
sleep 25
adb shell input swipe 500 1500 500 500 300; sleep 5
dotnet build "$P" "${C[@]}" -t:FinishAotProfiling "-p:AndroidAotCustomProfilePath=$OUT/chuvadi.aprof" > "$OUT/profiling-finish.txt" 2>&1; echo "finish exit $?"; tail -3 "$OUT/profiling-finish.txt"
if [ ! -s "$OUT/chuvadi.aprof" ]; then
  # The Linux SDK pack has no native aprofutil (tools/Linux/aprofutil: not found); run the managed one.
  PACK="$(ls -d /usr/share/dotnet/packs/Microsoft.Android.Sdk.Linux/* | sort -V | tail -1)"
  APU="$(find "$PACK" -iname 'aprofutil*.dll' | head -1)"
  echo "managed aprofutil: $APU" | tee -a "$OUT/profiling-finish.txt"
  adb forward tcp:9999 tcp:9999
  [ -n "$APU" ] && timeout 120 dotnet "$APU" -s -v -p 9999 -o "$OUT/chuvadi.aprof" >> "$OUT/profiling-finish.txt" 2>&1
  find "$PACK" -iname '*aprof*' >> "$OUT/profiling-finish.txt"
fi
ls -l "$OUT/chuvadi.aprof" || { grep -i -E "error|aprof" "$OUT/profiling-finish.txt" | head; }
adb uninstall in.chuvadi.reader >/dev/null 2>&1

if [ -s "$OUT/chuvadi.aprof" ]; then
  t=$(date +%s); clean; dotnet publish "$P" "${C[@]}" "-p:AtAotProfile=$OUT/chuvadi.aprof" > "$OUT/build-profiled.txt" 2>&1; echo "profiled build s: $(( $(date +%s)-t ))" | tee -a "$OUT/sizes.txt"; collect profiled
fi
t=$(date +%s); clean; dotnet publish "$P" "${C[@]}" -p:AndroidEnableProfiledAot=false > "$OUT/build-fullaot.txt" 2>&1; echo "fullaot build s: $(( $(date +%s)-t ))" | tee -a "$OUT/sizes.txt"; collect fullaot
for v in baseline profiled fullaot; do [ -f "$OUT/$v.apk" ] && unzip -l "$OUT/$v.apk" | grep -c "libaot-" | sed "s/^/$v libaot images: /" | tee -a "$OUT/sizes.txt"; done
