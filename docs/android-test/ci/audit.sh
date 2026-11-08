#!/usr/bin/env bash
# Package audit of the Release .aab / .apk (test tooling only).
#   audit.sh <reader-checkout> <packages-dir> <out-dir>
# Writes manifest, permissions, signing, sizes, ABIs, AOT/R2R evidence, every managed assembly,
# every Java package in the dex, native libraries, notices assets; and audit.json with the checks.
set -uo pipefail
READER="$(cd "$1" && pwd)"; PKGS="$(cd "$2" && pwd)"; mkdir -p "$3"; OUT="$(cd "$3" && pwd)"
mkdir -p "$OUT"
BT="$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -1)"
APK="$PKGS/chuvadi-reader-release.apk"; AAB="$PKGS/chuvadi-reader-release.aab"
echo "build-tools: $BT"

"$BT/aapt2" dump badging "$APK" > "$OUT/badging.txt" 2>&1
"$BT/aapt2" dump xmltree --file AndroidManifest.xml "$APK" > "$OUT/manifest-xmltree.txt" 2>&1
"$BT/aapt2" dump permissions "$APK" > "$OUT/permissions.txt" 2>&1
"$BT/apksigner" verify --verbose --print-certs "$APK" > "$OUT/apksigner.txt" 2>&1
keytool -printcert -jarfile "$AAB" > "$OUT/aab-cert.txt" 2>&1
ls -l "$APK" "$AAB" > "$OUT/sizes.txt"
unzip -l "$APK" > "$OUT/apk-contents.txt"
unzip -l "$AAB" > "$OUT/aab-contents.txt"

# bundletool (test tooling): what Play would deliver to a phone / tablet.
curl -sSL -o /tmp/bundletool.jar https://github.com/google/bundletool/releases/download/1.17.2/bundletool-all-1.17.2.jar
java -jar /tmp/bundletool.jar build-apks --bundle="$AAB" --output=/tmp/app.apks --overwrite > "$OUT/bundletool.txt" 2>&1
for dev in arm64 x86_64; do
  printf '{"supportedAbis":["%s"],"supportedLocales":["en-IN"],"screenDensity":420,"sdkVersion":35}' \
    "$([ $dev = arm64 ] && echo arm64-v8a || echo x86_64)" > /tmp/dev-$dev.json
  java -jar /tmp/bundletool.jar get-size total --apks=/tmp/app.apks --device-spec=/tmp/dev-$dev.json >> "$OUT/download-size.txt" 2>&1
  echo "($dev)" >> "$OUT/download-size.txt"
done

# Dex: every Java package shipped (third-party audit).
mkdir -p /tmp/dex && (cd /tmp/dex && unzip -o -q "$APK" 'classes*.dex')
for d in /tmp/dex/classes*.dex; do "$BT/dexdump" "$d" 2>/dev/null | sed -n "s/^  Class descriptor  : 'L\(.*\)\/[^/]*;'/\1/p"; done \
  | awk -F/ '{print $1"/"$2"/"$3}' | sort | uniq -c | sort -rn > "$OUT/dex-packages.txt"

# Managed assemblies actually linked into the Release app (per ABI; same set for every ABI).
LINKED="$(find "$READER/src/ChuvadiReader.Android/obj/Release" -type d -name linked | head -1)"
echo "linked dir: $LINKED" > "$OUT/assemblies.txt"
ls -1 "$LINKED"/*.dll 2>/dev/null | xargs -n1 basename | sort >> "$OUT/assemblies.txt"
# AOT / ReadyToRun evidence: AOT images, assembly store, msbuild properties
unzip -l "$APK" | grep -E "lib/[^/]+/lib.*\.so" | awk '{print $1, $4}' > "$OUT/native-libs.txt"
dotnet msbuild "$READER/src/ChuvadiReader.Android/ChuvadiReader.Android.csproj" -p:Configuration=Release \
  -p:TargetFramework=net10.0-android -getProperty:RunAOTCompilation -getProperty:AndroidEnableProfiledAot \
  -getProperty:PublishReadyToRun -getProperty:UseMonoRuntime -getProperty:AndroidLinkMode -getProperty:PublishTrimmed \
  -getProperty:RuntimeIdentifiers -getProperty:AndroidPackageFormats -getProperty:EnableLLVM \
  -getProperty:AndroidUseAssemblyStore -getProperty:Debuggable -getProperty:AndroidSupportedAbis > "$OUT/msbuild-props.json" 2>&1

python3 - "$OUT" <<'PY'
import json, os, re, sys
out = sys.argv[1]
r = lambda n: open(os.path.join(out, n), errors="replace").read()
badging, xml, signer = r("badging.txt"), r("manifest-xmltree.txt"), r("apksigner.txt")
perms = sorted(set(re.findall(r"uses-permission: name='([^']+)'", badging)))
checks = {}
checks["package id is the placeholder in.chuvadi.reader"] = "package: name='in.chuvadi.reader'" in badging
checks["minSdkVersion 35"] = "minSdkVersion:'35'" in badging
checks["targetSdkVersion 36"] = "targetSdkVersion:'36'" in badging
checks["not debuggable"] = "application-debuggable" not in badging
checks["allowBackup false"] = bool(re.search(r"allowBackup\(0x[0-9a-f]+\)=(false|\(type 0x12\)0x0)", xml))
checks["no cleartext traffic allowed"] = "usesCleartextTraffic" not in xml or bool(re.search(r"usesCleartextTraffic.*0x0", xml))
checks["signed with a debug/test key only (no upload key yet)"] = "Android Debug" in signer
checks["no INTERNET permission"] = "android.permission.INTERNET" not in perms
checks["no storage permissions"] = not any(p for p in perms if "STORAGE" in p or "MEDIA" in p)
pk = r("dex-packages.txt")
third = [l.strip() for l in pk.splitlines() if not re.search(r" (android|java|javax|mono|crc[0-9a-f]+|microsoft|in/chuvadi|chuvadi)/", l)]
json.dump({"permissions": perms, "checks": checks, "non_platform_java_packages": third[:80]},
          open(os.path.join(out, "audit.json"), "w"), indent=1)
for k, v in checks.items():
    print(("PASS " if v else "FAIL ") + k)
print("permissions:", perms)
print("java packages not android/java/mono/microsoft/chuvadi:", third[:40])
PY
