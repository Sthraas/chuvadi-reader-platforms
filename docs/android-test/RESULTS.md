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
**Release: not measurable yet** — the shipped Release never reaches a first frame (AT-03; R1c re-confirmed 3 of 3 launches crash on
API 36 phone and tablet). R1c's test-only rooted build still crashed (the build reused the previous link output); R2 rebuilds it clean.

**Preliminary, Debug x64 build of the same composition (JIT, no AOT, not what ships), API 36, 12 runs, device clock, ms:**
| Emulator | Cold → first frame | Cold → UI painted | Warm → first frame | Hot → first frame | Cold Open with → first frame | Cold Open with → page 1 painted |
|---|---|---|---|---|---|---|
| Phone (pixel_7) | 1,488 (worst 1,616) | 2,144 (worst 2,318) | 138 (worst 198) | 109 (worst 186) | 1,582 (worst 1,696) | **4,232** (worst 4,782) |
| Tablet (pixel_tablet) | 1,933 (worst 2,244) | 2,864 (worst 3,132) | 220 (worst 485) | 171 (worst 335) | 2,111 (worst 2,432) | **7,080** (worst 7,897) |
Warm "UI painted" had no valid sample (probe arrived after the UI each time; recorded as upper bounds). Emulators are x86_64 with
software GPU on shared CI runners: compare between rounds, not with a phone in the hand. Evidence: R1 › results-*-api36 › startup-debug.

## 3. Design (R1, API 36, Debug build — the look is identical to Release)
| # | Case | Result | Evidence |
|---|---|---|---|
| D-01 | Every screen × 5 themes × portrait/landscape, phone and tablet | **DONE** — 140 phone and 140 tablet screenshots, every screen reached | R1 › results-*-api36 › design/*.png |
| D-02 | 12d tablet Read | **PASS** (rail heading shows the mode name per D-111; extra "More view options" per D-113) | screenshots/r1/12d-vs-app.png |
| D-02 | 12e tablet Mark | **PASS** with the desktop's larger markup set; Save pinned at the rail foot (D-112) | 12e-vs-app.png |
| D-02 | 12f tablet Arrange portrait | **FAIL → AT-04, AT-05** | 12f-vs-app.png |
| D-02 | 12g phone Read | **PASS** | 12g-vs-app.png |
| D-02 | 12h phone Mark | **PASS** | 12h-vs-app.png |
| D-02 | 12i phone Arrange | **FAIL → AT-04** | 12i-vs-app.png |
| D-02 | 12j phone Protect + View sheet | **PASS** (rows 44 dp; Box not pre-selected as drawn — S4, noted only) | 12j-vs-app.png |
| D-03 | Touch targets ≥ 44 dp | **FAIL → AT-06** | design/*.layout.json |
| D-04 | Sideways overflow | **PASS** — 0 px on every screen, both orientations | design/summary.json |
| D-06 | Themes / system bars | **FAIL → AT-08** (system bars stay cream) | screenshots/r1/themes-phone-home-mark.png |
| D-10 | Theme by a real Settings tap, kept after restart | **PASS** phone (R1c); tablet result was a test-tool error (taps not rotated), re-run R2 | R1c › function |

## 4. Function (R1c, API 36, Debug fallback; round 2 re-runs with corrected tooling)
| # | Case | Result |
|---|---|---|
| F-01c | Open with opens the PDF (phone, tablet) | **PASS** |
| F-17 | Single instance: one activity after three arrivals | **PASS** |
| F-14 | Rotation keeps document, page, process | **PASS** |
| F-15 | Process death (`am kill` in background) → tabs come back | **PASS** |
| F-16 | All trim-memory levels → alive and responsive | **PASS** |
| R-10 | No crash / ANR / uncaught page error (Debug) | **PASS** |
| F-10, R-02 | AES-256 files (user password; owner-only) | **"This PDF is damaged"** — the fixtures had `/P` unsigned (pypdf), i.e. the known library item **LIB-1**; R2 adds signed-`/P` fixtures to test the password path itself |
| F-01a/b, F-02, F-03, F-11, F-12, D-08 | — | test-tool errors (selectors, tablet tap rotation); fixed, re-run R2 |

## 5. Robustness
PENDING (round 3).

## Test-tool notes (my own bugs, fixed)
- R1: the WebView donor took only the WebView `.apk`; the API 36 WebView needs the Trichrome static library, so the API 35
  update failed (`INSTALL_FAILED_MISSING_SHARED_LIBRARY`) and API 35 stayed on 124. Donor now pulls the library too.
- R1: the "is Release inspectable" check matched any DevTools socket when the app wasn't running (empty pid); fixed.
- R1: the audit's dex listing ran with a relative path from another folder; fixed. Startup stops a mode after three failed launches.
