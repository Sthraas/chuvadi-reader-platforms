#!/usr/bin/env bash
# Test-only build variants (never shipped), no emulator needed:
#   baseline  = as shipped (MAUI's default profiled AOT)
#   chuvadi   = profiled AOT + the Chuvadi assemblies (Chuvadi.*, ChuvadiReader.*, LiPicons) compiled in full
#               (the runner's SDK pack AOT targets are edited to drop profile/profile-only for those assemblies)
#   trace     = baseline + trace-patch.py markers (Console lines → logcat), for the cold Open-with timeline
#   aot-variants.sh <reader-checkout> <test-ci-dir> <out-dir>
set -uo pipefail
READER="$(cd "$1" && pwd)"; CI="$(cd "$2" && pwd)"; mkdir -p "$3"; OUT="$(cd "$3" && pwd)"
P="src/ChuvadiReader.Android/ChuvadiReader.Android.csproj"
C=(-c Release -f net10.0-android --no-restore "-p:AndroidSdkDirectory=$ANDROID_HOME" -p:TreatWarningsAsErrors=false)
cd "$READER"
clean() { rm -rf src/ChuvadiReader.Android/obj/Release src/ChuvadiReader.Android/bin/Release; }
collect() {
  find src/ChuvadiReader.Android/bin/Release -name '*-Signed.apk' -exec cp {} "$OUT/$1.apk" \;
  find src/ChuvadiReader.Android/bin/Release -name '*-Signed.aab' -exec cp {} "$OUT/$1.aab" \;
  ls -l "$OUT/$1.apk" "$OUT/$1.aab" | tee -a "$OUT/sizes.txt"
  find src/ChuvadiReader.Android/obj/Release -path '*aot*' -name 'libaot-Chuvadi*.so' -printf "%s %f\n" 2>/dev/null | sort -k2 | head -12 > "$OUT/$1-chuvadi-aot-images.txt"
}
build() { t=$(date +%s); clean; dotnet publish "$P" "${C[@]}" "$@" > "$OUT/build-$V.txt" 2>&1; echo "$V build exit $? in $(( $(date +%s)-t )) s" | tee -a "$OUT/sizes.txt"; collect "$V"; }

VARIANTS="${AT_VARIANTS:-baseline chuvadi fullaot trace}"
has() { [[ " $VARIANTS " == *" $1 "* ]]; }
has baseline && { V=baseline build; }

if has chuvadi; then
# chuvadi: edit the SDK pack's AOT targets on this runner only.
AOTT="$(ls -d /usr/share/dotnet/packs/Microsoft.Android.Sdk.Linux/* | sort -V | tail -1)/targets/Microsoft.Android.Sdk.Aot.targets"
sudo cp "$AOTT" "$AOTT.orig"
sudo python3 - "$AOTT" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
anchor = "    </GetAotAssemblies>\n"
add = anchor + """    <ItemGroup>
      <_MonoAOTAssemblies Update="@(_MonoAOTAssemblies)" Condition="$([System.String]::Copy('%(Filename)').StartsWith('Chuvadi')) or $([System.String]::Copy('%(Filename)').StartsWith('LiPicons'))"
                          AotArguments="$([System.Text.RegularExpressions.Regex]::Replace('%(AotArguments)', ',?profile=[^,]*|,?profile-only', ''))" />
    </ItemGroup>
    <Message Importance="high" Text="ATAOT %(_MonoAOTAssemblies.Filename): %(_MonoAOTAssemblies.AotArguments)" Condition="$([System.String]::Copy('%(_MonoAOTAssemblies.Filename)').StartsWith('Chuvadi'))" />
"""
assert anchor in s
open(p, "w").write(s.replace(anchor, add, 1))
print("aot targets edited")
PY
V=chuvadi build
grep "ATAOT" "$OUT/build-chuvadi.txt" | sort -u | head -8 | cut -c1-260 | tee "$OUT/chuvadi-aot-args.txt"
sudo cp "$AOTT.orig" "$AOTT"
dotnet build-server shutdown > /dev/null 2>&1   # MSBuild nodes cache the edited targets (R7's trace build inherited them)
fi

has fullaot && { V=fullaot build -p:AndroidEnableProfiledAot=false; }

# trace
if has trace; then
python3 "$CI/trace-patch.py" "$READER" | tee "$OUT/trace-patch.txt"
V=trace build
fi
for v in baseline chuvadi fullaot trace; do [ -f "$OUT/$v.apk" ] && echo "$v: $(unzip -l "$OUT/$v.apk" | awk '/libaot-Chuvadi/ {s+=$1} END {print s}') bytes of Chuvadi AOT images" | tee -a "$OUT/sizes.txt"; done
