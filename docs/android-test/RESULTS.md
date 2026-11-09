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

## 4. Function — R2 (run 42533545934: Foundation 053e8e4 + Mobile UI 770bfdf + Android b731cfe), API 36, Debug fallback
The shipped Release can't run (AT-03), and R2's test-only rooted Release didn't produce a package (its publish log stops after
the AOT step; to look at), so these ran on the Debug x64 build of the same composition. Results apply to the look and logic, not
to Release-only behaviour (trimming, AOT).
| # | Case | Phone | Tablet |
|---|---|---|---|
| F-01a | Home Open → system picker (DocumentsUI) → picked file opens | **PASS** | **PASS** |
| F-01b | Share to Chuvadi | test tool (am grant), fixed for R3 | same |
| F-01c | Open with | **PASS** | **PASS** |
| F-17 | Single instance (one activity after three arrivals) | **PASS** | **PASS** |
| F-02 | Next page (phone: real swipe; tablet: Next page) | **PASS** | **PASS** |
| F-03 | Find "zephyrine" | typing cut by the test's burst ("zene"), re-run R3 | **FAIL → AT-09** (1/1 but match not shown) |
| F-11a/b | Print → Android dialog → Save as PDF; vector check | not reached (test: a toast covered the button), R3 | same |
| F-11c | No-print PDF: Print refused with the reason | **PASS** ("This file's permissions don't allow printing.") | **PASS** |
| R-02a | Owner-password-only AES-256 PDF opens without a prompt | **PASS** | **PASS** |
| F-10 | User-password AES-256 PDF asks for the password (B-07 in Foundation f1e4126) | **PASS** | **PASS** |
| F-14 | Rotation keeps document, page, process | **PASS** | **PASS** |
| F-15 | Process death → tabs restored | **PASS** | **PASS** |
| F-16 | Trim-memory levels → alive, responsive | **PASS** | **PASS** |
| D-10 | Theme by a real Settings tap, kept after restart | **PASS** | **PASS** |
| D-08 | On-screen keyboard: Find field stays above it | **PASS** (innerHeight 839 → 527) | **PASS** |
| F-12 | Back closes the open sheet/card, same screen | **PASS** | **PASS** |
| R-10 | No crash / ANR / uncaught page error | **PASS** | **PASS** |
| B-12 | As-built Release starts | **FAIL → AT-03** (3 of 3 crash, R1c and R2) | same |

### R3 / R3b (runs 42537723474, 42539596914; same refs, Debug fallback)
| # | Case | Phone | Tablet |
|---|---|---|---|
| F-01b | Share to Chuvadi → new tab | **PASS** | **PASS** |
| F-03 | Find "zephyrine" (one key per 250 ms) | **PASS** (R3, R3b: 1/1, page 3) | R3 **FAIL** (typed "zphyrine" → AT-10); R3b **PASS** |
| F-03b | Fast typing: Find box vs plain field | **FAIL → AT-10** ("burtwordt", "butot") | **FAIL → AT-10** ("butwort", "butest") |
| F-11a/b | Print → Android dialog → Save as PDF; output vector | **PASS** (R3c run 42541494724: 12 pages, 40,561 chars of text, **0 images**, Find marker present) | dialog reached in R3/R3b; R3c's tap on the card button missed (test selector) — tablet printing still to re-run |
| F-15 / F-15b | Tabs back after a background kill | **FAIL → AT-11** (11 of 11 lost) | **PASS** (11 of 11) |
| R-02a | Owner-only AES-256 file renders | R3, R3b: laid out, page 1 not rendered within 40 s — watching | **PASS** |
| everything else in the R2 table | | **PASS** again | **PASS** again |

## 5. Robustness — R4 (run 42543057904) and R4b (run 42546917921; Foundation 053e8e4 + Mobile UI 770bfdf + Android b731cfe; API 36, Debug fallback)
| # | Case | Phone | Tablet |
|---|---|---|---|
| R-01 | Truncated / broken-xref / random bytes / 0-byte "PDF" | **PASS** — "This PDF is damaged … Chuvadi can try to rebuild it as a new copy"; no crash; app usable | **PASS** |
| R-03 | 600-page PDF: first page | **PASS** 1.6 s, PSS 262 MB | **PASS** 2.2 s, PSS 258 MB |
| R-03b | 600-page PDF: jump to the end, last page renders | **PASS** 0.2 s | **PASS** 0.3 s |
| R-03c | 6000 × 6000 px image page (28 MB file) | R4 **not painted in 90 s**; R4b **PASS** 4.5 s → **AT-13** | R4 **PASS** 3.9 s; R4b **not painted in 120 s** → **AT-13** |
| R-03d | Next document opens after the heavy page (R4b) | **PASS** | **PASS** |
| R-04 | DocumentsProvider URI (`com.android.externalstorage.documents`) | R4b **PASS** | **PASS** |
| R-05 | Airplane mode: start + open a PDF | **PASS** | **PASS** |
| R-06 | en-IN / ta-IN / hi-IN system locale (R4b) | **PASS** ×3, no overflow | **PASS** ×3 — the date follows the locale ("திங்கள் 9 நவ. 2026", "सोमवार 9 नव॰ 2026"); the greeting stays English + Tamil by design |
| R-07 | Fresh install (data cleared): first-run box, no samples, no name (R4b) | **PASS** ("Open your first document") | **PASS** |
| R-10 | No crash / ANR in the suite (Debug) | **PASS** — the 4 FATAL lines in the log are the as-built Release launches before the suite (AT-03); logcat is now cleared before the suites | **PASS** (same) |

## Blocked in CI: Reader on Android 15 (API 35)
The API 35 image ships WebView 124, so the app correctly shows only its update screen (D-105). Updating it in CI from the API 36
image's WebView failed twice: that WebView needs the Trichrome static library, which my donor job couldn't locate on the API 36
image. Options for the coordinator: (a) keep trying a donor (Trichrome library), (b) a newer API 35 system image if one ships
WebView ≥ 128, (c) accept API 36 as the Reader check and test API 35 only for the update screen — real Android 15 devices get
WebView through Play. Recommendation: (c) now, (b) when such an image appears; (a) costs runner time with no sure end.
**Decided (coordinator, 9 Nov 07:12): (c).** API 36 is the Reader check; API 35 is tested only for the WebView update screen (D-105).

## Test-tool notes (my own bugs, fixed)
- R1: the WebView donor took only the WebView `.apk`; the API 36 WebView needs the Trichrome static library, so the API 35
  update failed (`INSTALL_FAILED_MISSING_SHARED_LIBRARY`) and API 35 stayed on 124. Donor now pulls the library too.
- R1: the "is Release inspectable" check matched any DevTools socket when the app wasn't running (empty pid); fixed.
- R1: the audit's dex listing ran with a relative path from another folder; fixed. Startup stops a mode after three failed launches.
