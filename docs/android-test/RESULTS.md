# Android Test — results

Every case from TEST-PLAN.md: **PASS** / **FAIL** / **PENDING** / **BLOCKED**, with evidence (run id › artifact › file).
Runs: [R1 42518447149](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42518447149) (Foundation 839d39d +
Mobile UI 95b9d79 + Android 7ec8017; cancelled after the API 35 jobs proved AT-03) ·
[R1b 42526285949](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42526285949) (same refs; suites on the AT-03 test-only Release).

## 1. Build and package
| # | Case | Result | Evidence |
|---|---|---|---|
| B-01 | Clean compose + restore + Release publish | **PASS** — 0 errors, 0 warnings, 139 s publish | R1 › audit › publish-release.txt |
| B-02 | Debug x64 build | **PASS** — 0 errors, 0 warnings | R1 › audit › build-debug.txt |
| B-03 | Manifest | **PASS** — minSdk 35, targetSdk 36, not debuggable, `allowBackup=false`, `fullBackupContent=false`, data-extraction rules excluding everything, no cleartext attribute | R1 › audit › badging.txt, manifest-xmltree.txt |
| B-04 | Permissions | **PASS** — only `in.chuvadi.reader.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` (AndroidX's own signature permission); no INTERNET, no storage | R1 › audit › audit.json |
| B-05 | App id placeholder | **PASS** — `in.chuvadi.reader`; FileProvider authority `${applicationId}.files` | badging.txt |
| B-06 | Signing | **PASS** — APK v2/v3 signed with the SDK debug key ("Android Debug"); no keystore in the repo | apksigner.txt |
| B-07 | Size | **RECORDED** — `.aab` 41.96 MB; universal `.apk` 42.34 MB; Play download (bundletool, per device) arm64 **24.97 MB**, x86_64 25.54 MB. ABIs: arm64-v8a and x86_64 only (no 32-bit) | sizes.txt, download-size.txt |
| B-08 | AOT / ReadyToRun | **RECORDED** — Mono runtime, **profiled AOT** (`RunAOTCompilation=true`, `AndroidEnableProfiledAot=true`, MAUI's default startup profile), partial trimming (`SdkOnly`), assembly store. Chuvadi assemblies' AOT images are 4–14 KB each, i.e. the default profile precompiles almost none of Chuvadi/Core/Ui: their code is JIT-compiled at run time. Startup numbers (S-01…) decide whether this needs an option | msbuild-props.json, apk-contents.txt |
| B-09 | No third-party code | **FAIL → AT-01** — AndroidX (×25), Google Material, Kotlin stdlib, kotlinx coroutines/serialization ship as MAUI dependencies; not in the notices. Everything else: .NET, MAUI, Chuvadi, LiPicons. Dex package listing re-run in R1b (script path bug in R1) | assemblies.txt, AT-01 |
| B-09b | Unused components | **FAIL (S4) → AT-02** — Essentials activities/receivers/provider in the manifest | AT-02 |
| B-10 | Licences | PENDING — in-app Licences page check runs in the function suite; notices gap is AT-01 | |
| B-11 | Play data safety | **FAIL (wording) → AT-01** — answers ("no data collected") match the package (no INTERNET, backups off); the basis line about libraries is wrong | PLAY-DATA-SAFETY.md |
| B-12 | **Release package starts** | **FAIL → AT-03 (S1)** — crashes at every launch (trimmed seam constructors) | R1 › results-*-api35 › dropbox.txt |

## 2. Startup
PENDING (R1b). R1 had no measurement: the Release app never reached a first frame (AT-03).

## 3. Design
PENDING (R1b). Handout reference frames rendered from `Portal & Android.dc.html`: `screenshots/handout/12d…12j.png`.

## 4–5. Function, robustness
PENDING (R1b function suite; robustness round 3).

## Test-tool notes (my own bugs, fixed)
- R1: the WebView donor took only the WebView `.apk`; the API 36 WebView needs the Trichrome static library, so the API 35
  update failed (`INSTALL_FAILED_MISSING_SHARED_LIBRARY`) and API 35 stayed on 124. Donor now pulls the library too.
- R1: the "is Release inspectable" check matched any DevTools socket when the app wasn't running (empty pid); fixed.
- R1: the audit's dex listing ran with a relative path from another folder; fixed. Startup stops a mode after three failed launches.
