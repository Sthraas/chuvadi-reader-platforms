# Chuvadi Reader — Android

The Android app is a .NET MAUI Blazor Hybrid host (`src/ChuvadiReader.Android`) around the
unchanged `ChuvadiReader.Ui` and `ChuvadiReader.Core`. Minimum Android 15 (API 35); target API is
the .NET 10 Android SDK's (API 36). Distributed through Google Play as an `.aab`.

Decisions waiting on Arun: [DECISIONS.md](DECISIONS.md). Step-by-step record: [BUILD-LOG.md](BUILD-LOG.md).

## Layout during development
In this working repo the host lives alone in `src/ChuvadiReader.Android`; it references
`..\ChuvadiReader.Core`, `..\ChuvadiReader.Ui`, `..\ChuvadiReader.Platform` and
`..\ChuvadiReader.Hosting`, the layout it has after the platform push. Build it in the test
composition (Foundation + Mobile UI + this host), at the pins in `.github/workflows/android.yml`:

```bash
git worktree add --detach ../foundation <FOUNDATION_REF>
git worktree add --detach ../mobileui   <MOBILEUI_REF>
docs/android/integration/compose.sh ../foundation ../mobileui .
cd ../foundation
```

## Prerequisites
- .NET SDK 10.0.x
- MAUI Android workload: `dotnet workload install maui-android`
- JDK 17 or 21
- Android SDK. If you don't have one, the build installs what it needs:
  ```bash
  dotnet build -t:InstallAndroidDependencies -f net10.0-android \
    src/ChuvadiReader.Android/ChuvadiReader.Android.csproj \
    -p:AndroidSdkDirectory=<sdk folder> -p:AcceptAndroidSDKLicenses=True
  ```
  On Linux set `USER` if it is empty (the SDK installer needs it).

Packages restore from the Reader's own CI feed (`ci/packages`: chuvadi-pdf 3.31.1, Chuvadi.Fonts
1.0.0, LiPicons.Blazor, Docs, Sheets) plus nuget.org for Microsoft's MAUI packages:

```bash
cd reader
dotnet restore src/ChuvadiReader.Android/ChuvadiReader.Android.csproj --configfile ci/nuget.config
```

## Build and run
```bash
# Debug, on a connected device or running emulator
dotnet build src/ChuvadiReader.Android/ChuvadiReader.Android.csproj -c Debug -t:Run

# Release: .aab (Play upload) and .apk, in bin/Release/net10.0-android/publish/
dotnet publish src/ChuvadiReader.Android/ChuvadiReader.Android.csproj -c Release -f net10.0-android
```
Without signing properties, Release packages are signed with the SDK's debug key — fine for
testing, never for Play.

## CI
`.github/workflows/android.yml` runs **only when started by hand** (Actions → Android → Run workflow,
or `gh workflow run android.yml --ref platform/android -f emulators=…`). Pushes and pull requests start
nothing. Emulator minutes are the largest part of the Actions bill, so it's one run per round, with
only the emulators that round needs. The `emulators` input takes `all`, `none` (build only), or a comma
list of `phone-35`, `phone-36`, `tablet-35`, `tablet-36`.
1. builds the Release `.aab` + `.apk` and a Debug x86_64 `.apk`, uploaded as `android-packages`;
2. on each chosen emulator (phone = pixel_7, tablet = pixel_tablet; no hardware keyboard):
   - smoke test: cold start, the Ui's own text on screen, real rotation, no crash or console error;
   - gestures: Open with, swipe, double-tap zoom, pinch, Arrange long-press drag (real touch), and
     the over-wide element report for Fit page;
   - platform: Open with .docx/.xlsx while running (new tab, same activity), Share to, rotation with
     a document, keyboard and on-screen keyboard, printing (PrintManager → saved PDF; range; L-8
     no-print file locked), Back, split screen.
   Screenshots, UI dumps, logs and the JSON results are uploaded.

## Signing for Play (Arun only — never commit a key)
Play uses **Play App Signing**: Google holds the app signing key; you sign uploads with your own
**upload key**. Create it once, on your own machine:

```bash
keytool -genkeypair -v -keystore chuvadi-upload.jks -alias chuvadi-upload \
  -keyalg RSA -keysize 4096 -validity 10000 -storetype PKCS12
```
- Keep `chuvadi-upload.jks` and its password outside every repository (`*.jks` / `*.keystore` are
  git-ignored here as a guard). Store a backup offline (e.g. encrypted, in your vault). If lost,
  Google can reset the upload key, but only through Play Console support.
- Sign a release locally:
  ```bash
  dotnet publish src/ChuvadiReader.Android/ChuvadiReader.Android.csproj -c Release -f net10.0-android \
    -p:AndroidKeyStore=true -p:AndroidSigningKeyStore=/secure/path/chuvadi-upload.jks \
    -p:AndroidSigningKeyAlias=chuvadi-upload \
    -p:AndroidSigningKeyPass=env:CHVD_KEY_PASS -p:AndroidSigningStorePass=env:CHVD_STORE_PASS
  ```
- If CI should sign later: put the keystore (base64) and passwords in GitHub **environment
  secrets** with required reviewers — only after Arun decides to.

## Play Store listing checklist
- [ ] Application id from the final domain (likely `chuvadi.in`) — permanent; placeholder `in.chuvadi.reader` until then (A-01).
- [ ] Developer account: Sthraas Intelligence Pvt Ltd (after the company registration).
- [ ] Upload key created and stored (above); Play App Signing enrolled.
- [ ] Target API: .NET 10's API 36 meets Play's current target-level rule; recheck before each release.
- [ ] Store icon 512 × 512 and adaptive icon: drafts in `docs/android/branding/` (A-09) — Arun's final check.
- [ ] Feature graphic 1024 × 500; phone and 7"/10" tablet screenshots (CI emulator shots are a start).
- [ ] Short (80 chars) and full description; category: Productivity.
- [ ] Privacy policy URL (required even when nothing is collected).
- [ ] **Data safety**: no data collected, no data shared; files processed on the device. Network
      permission: none (printing goes through Android's own print framework, A-04 (a), which needs no
      app permission).
- [ ] Content rating questionnaire; target audience (adults / general); no ads.
- [ ] **Licence (Arun, 7 Nov): proprietary, free for everyone, not open source.** Price: Free. The
      Foundation adds `LICENSE` and an EULA draft; use the EULA as the listing's custom licence /
      terms link and in-app About (the About screen is the shared Ui). Don't describe the app as
      open source anywhere in the listing.
- [ ] Permissions declared: none (files arrive through the system picker and Open-with/Share grants).
- [ ] App access: no sign-in needed (Sangam gating applies only to signing/sync — none on Android v1).
- [ ] Internal testing track first, then closed testing, then production.

---
Copyright © 2026 Sthraas Intelligence Pvt Ltd. All rights reserved. Proprietary; free for everyone, not open source.
