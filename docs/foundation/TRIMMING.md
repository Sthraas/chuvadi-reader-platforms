# Trimmed Release builds (AT-03, 9 Nov 2026)

## What happened
The Android Release app died at every launch: `NoConstructorMatch, ChuvadiReader.Platform.NoAppInstance` (Android Test AT-03, S1).
- `ChuvadiReader.Platform` is trimmable (`IsTrimmable`, `IsAotCompatible`). Android Release (MAUI, `AndroidLinkMode=SdkOnly`) trims it, and so does Mac Catalyst Release.
- The kit registered the seam defaults from untyped `(Type, Type)` tuples, so the trimmer couldn't see that the container constructs them, and removed their constructors.
- Nothing warned, because the kit (Hosting) wasn't analysed. Debug builds aren't trimmed, and only Debug was launched in CI.

## Fix (coordinator decision a)
- **Typed registrations (structural, D-146):** every registration in `ChuvadiReaderServices` is one typed call, `Core<TService, TImpl>(…)` or `Seam<TService, TImpl>(…)`. `TImpl` carries `[DynamicallyAccessedMembers(PublicConstructors)]`, and `where TImpl : TService` makes the compiler check the pair. There is no table of `Type` values left.
  - **A new seam default (Android P-08's `PlainPathLabels`, or any later one) is one more `Seam<IPathLabels, PlainPathLabels>(services, life);` line.** Nothing else to remember, no list of exceptions.
  - Generic methods over reference types share one compiled body: no extra JIT at startup (StartupProbe: 1448 JIT methods against 1450 before; building the services 28.9 / 30.5 ms against 30.0 / 31.0 ms, medians of 12 runs, twice).
  - Why not the annotated `Registration` record of the first fix: it worked, but only while every entry went through it. **The trim analyser can't follow `Type` values through an array**: a plain `(Type, Type)` table, AT-03's own shape, built with 0 errors and its constructor was trimmed away. So the safe shape has to be the only shape.
- **Analysers on:** Hosting has the trim and AOT analysers (`EnableTrimAnalyzer`, `EnableAotAnalyzer`), with warnings as errors; Platform already had them (`IsTrimmable`, `IsAotCompatible`).
- **First catch:** the analyser found `FileAppStorage`'s settings JSON going through reflection, which a trimmed or AOT host can break. It now uses generated JSON (`SettingsJson`), byte for byte the same (tested).

## Proof and CI
- **`tools/TrimProbe`** (test only) calls `AddChuvadiReader` like a host, is published **trimmed** (`TrimMode=partial`: only trimmable assemblies, as Android `SdkOnly` and Mac Catalyst), and resolves every registered service.
  - Before the fix it failed exactly as Android: 6 of 53 services (`NoAppInstance`, `NoHostNotices`, `NoDroppedFiles`, `NoFileWriteBack`, `NoFileManager`, and `IncomingFiles`, which needs `IAppInstance`), each with "A suitable constructor … could not be located".
  - After the fix: 53 of 53.
- **What is caught, and where (tested 9 Nov with a stand-in seam in the trimmable Platform assembly):**

| Change | Result |
|---|---|
| New default as one `Seam<…>` line | Kept: trimmed probe 54 of 54 |
| A helper without the annotation | Build fails, IL2087 |
| The annotation removed from `Seam` | Build fails, IL2087 |
| A `(Type, Type)` table brought back | The analyser misses it; the guard test `The_kit_keeps_no_tables_of_types` fails, and so would the trimmed probe in CI (it failed: "A suitable constructor … could not be located") |

- `TypedRegistrationTests` also pins the 51 registrations: the same services, implementations, order and lifetimes as before this change, so every host behaves exactly as before.
- **CI job `trim-check`:** publishes and launches the probe trimmed.
  - `platforms.yml`: linux-x64, linux-arm64, osx-arm64.
  - `ci.yml` (PR #11): linux-x64, osx-arm64.

## For the host chats (their workflows; a host's own Release must launch in CI)
**Android**: build Release, install it and launch it, not only Debug. After the existing emulator boot step:
```bash
dotnet build src/ChuvadiReader.Android/ChuvadiReader.Android.csproj -c Release -f net10.0-android -p:AndroidPackageFormat=apk -warnaserror
adb install -r src/ChuvadiReader.Android/bin/Release/net10.0-android/in.chuvadi.reader-Signed.apk
adb shell am start -W -n in.chuvadi.reader/crc64…/MainActivity | tee start.txt   # the launcher activity
grep -q "TotalTime" start.txt                                                       # a crash never reports one
sleep 5; adb shell pidof in.chuvadi.reader                                          # still running
```
Also run the trim analyser in the Android host's Release build (`-p:EnableTrimAnalyzer=true -warnaserror`) once the host is clean, so a new reflection use fails the build.

**Mac (Catalyst)**: build Release (`-f net10.0-maccatalyst -c Release`), then start the app bundle's executable with `--self-test` or a 5-second launch-and-quit, and check that it exited 0. The same trimming applies there.

**Linux, Web, Windows**: not trimmed today. If a host ever turns trimming on, it inherits this protection; run its Release once in CI.
