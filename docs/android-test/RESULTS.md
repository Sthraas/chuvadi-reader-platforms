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

## 2. Startup — **Release** (R4e, run 42741617577; Foundation f88f9ef + Mobile UI d34d542 + Android d134c74), API 36
The as-built Release `.apk` (profiled AOT, as shipped). 12 runs each after one discarded warm-up; device-clock ms from
ActivityTaskManager's launch. "UI painted" / "page 1 painted" come from an in-page probe (the emulator images are userdebug, so the
Release WebView is inspectable there; it isn't on a user build).
| Emulator | Cold → first frame | Cold → UI painted | Warm → first frame | Hot → first frame | Cold Open with → first frame | Cold Open with → page 1 painted |
|---|---|---|---|---|---|---|
| Phone (pixel_7) | **1,045** (worst 2,601) | **1,562** (worst 4,318) | **149** (worst 275) | **157** (worst 280) | **1,155** (worst 1,246) | **3,920** (worst 4,314) |
| Tablet (pixel_tablet) | **1,607** (worst 2,601) | **2,215** (worst 3,918) | **241** (worst 402) | **264** (worst 463) | **1,494** (worst 1,786) | **6,028** (worst 6,516) |
Against Debug (R1): cold UI −27 % phone / −23 % tablet; cold first page −7 % / −15 %. Warm "UI painted": no valid sample (the
probe always arrived after the paint — reported as upper bounds in `warm.json`). x86_64 emulators with a software GPU on shared
runners: compare between rounds, not with a phone in the hand. Cold first page is the slow spot → **AT-14**.

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

## Round 4d (run 42739175820; Foundation f88f9ef + Mobile UI d34d542 + Android d134c74)
Compose note: `P-08-path-labels.patch` (Android proposal) no longer applies either way on f88f9ef — Foundation took P-08 in its own
form; skipped and reported. Android is rebasing.
| # | Case | Result |
|---|---|---|
| B-12 | As-built Release starts (AT-03) | **PASS** — 0 crashes, 3 of 3 first frames, phone API 35, phone API 36, tablet API 36 |
| F-13 | D-105 gate, stock API 35 (WebView 124.0.6367.219) | **PASS** — "One small update first … needs version 128 or newer. On this device it is version 124.0.6367.219 … free from Google Play"; app alive, no crash |
| F-13b | API 36 (WebView 133): no update screen | **PASS** |
| F-04, F-06, F-07, F-11d, F-03c/d | Markup, forms, redaction, print card, typing in other fields | test tool didn't reach the controls (a Mark tap landed in the system image picker; redaction drag drew 0 boxes; sheet selector) — diagnostics added, R4e |

## Round 5 — re-verification on the Android handoff (run 42746209649; Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b; **Release**, API 36)
Compose: clean (no skipped patches). Build 0 warnings; `.aab` 42.6 MB, Play download (arm64) 25.3 MB.
| Bug | Result |
|---|---|
| AT-02 Essentials components | **verified** — gone from the manifest |
| AT-03 Release launch | **verified** — 0 crashes, 3 of 3 first frames (phone, tablet) |
| AT-04 desk header on touch | **verified** — name + `···` only |
| AT-05 tablet portrait `Document ▾` | **verified** |
| AT-06 touch targets | **still open** (unchanged sizes) |
| AT-07 path labels | **verified** — none on any screen |
| AT-08 system bars follow the theme | **verified** through a real Settings tap (`screenshots/r4/r5-at08-night-theme.png`). The design sweep sets themes from the page only, which the host doesn't see — so its cream bars aren't evidence |
| AT-09 Find brings the match into view | phone **PASS**; tablet **still open** |
| AT-10 typed keys kept | **verified** — Find box and Library search, burst and slow |
| AT-11 tabs after a background kill | **verified** — 11/11 phone and tablet |
| AT-12 same file → same tab | **still open** (4 → 5 tabs) |
| AT-13 heavy image page | **PASS this run** (1.7 s both); intermittent, repeating |
| AT-15 markup by touch | **still open**; shapes fail the same way (pointer goes to the desk) |
Other cases this round: Find 1/1 on page 3 (phone), D-08 keyboard, F-12 Back, F-16 trim-memory, D-10 theme persists, R-01 damaged
files, R-03 600 pages, R-04 provider URI, R-05 airplane, R-06 locales, R-07 fresh install, R-10 no crash — all **PASS** on Release.
F-14 phone "page moved 1 → 3 on rotation": the before-state was read while the reopened tab was still restoring its last page (3);
test timing, not filed. Tablet print card button and F-06/F-07 saves still not reached by the tool (AT-15 blocks markup).

## Round 8 — re-verification (run 42802779369; Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8; **Release**, API 36)
As-built Release: 0 crashes, 3/3 first frames (phone, tablet).
| Item | Result |
|---|---|
| AT-06 touch targets | original table **fixed**; a second list of tablet content controls (and the desk name field) still under 44 dp — see BUGS |
| AT-09 Find brings the match into view | **verified** phone and tablet |
| AT-12 same file → same tab | **verified** (4 tabs stay 4) |
| AT-13 heavy image page | **5/5 phone, 5/5 tablet** (22/22 since the fix) — verified |
| AT-15 markup by finger | shapes **PASS** (phone + tablet), redaction box draws (tablet), text box is created; caret not in it → **AT-17** |
| Page-box drift | tablet box says 2 with page 3 on screen after Find → **AT-16**; own check from R8b |
| F-11 printing, phone | **PASS** again: Android dialog → PDF, 12 pages, 40,561 chars, 0 images |
| F-11d print card → Android print dialog, tablet | **PASS** (first time the tool reached it); vector check of the tablet file in R8b |
| AT-10 / AT-11 / F-15b ×10 / F-03b | **PASS** again |
| F-06 forms, F-07 redacted copy saved, F-09 Save | not conclusive (tool: selection handles from my own long-press, phone Redact selector); re-run R8b |

## Round 8b (run 42807280851; same refs as round 8)
| Item | Result |
|---|---|
| Page-box check (`drift.py`) | cold open, second document, reopen, rotation: **PASS** phone and tablet. "Move to page 5" and "restart" steps were test-script errors; corrected for round 9 |
| AT-16 tablet page box after Find | **FAIL again** (box 2, page 3 on screen) |
| AT-17 text box caret | first tap: box without caret (**FAIL**); second tap on the box: caret, keyboard, typing correct (**PASS**), phone and tablet |
| Shapes by finger; redaction box by finger (tablet) | **PASS** |
| Printing, phone: vector | **PASS** (12 pages, 40,561 chars, 0 images) |
| Print card → Android print dialog, tablet | **PASS**; the tablet's saved file still not checked (script) |
| **Not verified yet** | Save / Save as with the saved file read back (markup, form value, redacted text gone), form filling by touch, Arrange drag and save. My script didn't complete these: on the phone the text-box property sheet covered the Save button; my test grant was read-only so in-place Save had nowhere to write; the form tap missed the field. No app fault shown or ruled out |

## Round 9 / 9b (runs 42867016981 and 42875987375; Android 8f173c9 + Foundation dd59362 + Mobile UI 3ecbc75; **Release**, API 36)
Built with SDK 10.0.403 pinned (10.0.404 breaks the clean build → AT-19). 0 warnings. As-built Release: 0 crashes, 3/3 launches.
The save suite opens **writable** files through the system picker, changes them by touch and reads the saved files back; it ran on
the Release as built and on a test-only build with the host's save pickers switched on.
| Case | As built | Pickers switched on (test-only) |
|---|---|---|
| Open through the system picker | **PASS** phone, tablet | **PASS** |
| Text box typed (after the second tap, AT-17) | **PASS** phone, tablet | **PASS** |
| **Save in place** (tablet): the picked file now holds the text | **PASS** — "Saved to sv-text.pdf", text read back | **PASS** |
| **Save as new PDF** | **FAIL → AT-18** (no picker, no file) | tablet **PASS**: rectangle in the new file (page 1 has the stamped mark), 12 pages; original untouched. Phone: not reached — the selected mark's sheet covers the Save button and my script couldn't dismiss it |
| Form values kept through a Save as (patient Ravi, ward Cardiac) | FAIL → AT-18 | tablet **PASS** |
| **Form filling by touch** | **not offered**: the Reader has no Fill form tool yet (greyed "until built" on every platform, PHASE1-PARITY); filled values are displayed (**PASS**) | same |
| Redaction box by finger | **PASS** phone, tablet | **PASS** |
| **Save redacted copy** | **FAIL → AT-18** | tablet **PASS**: heading gone from the page content and text, body and other pages kept, original untouched |
| Arrange: long-press drag two pages to a desk, reorder | phone **PASS** (both); tablet **FAIL → AT-20** | same |
| **Bind** the desk to a PDF | **FAIL → AT-18** | not reached (phone second pass lost the picker folder; tablet has no pages on the desk) |
| Print → Android dialog → PDF | **PASS** phone and **tablet** (first time): 12 pages, 40,550 chars, 0 images | **PASS** |
Other suites (R9): page-box check 6/6 phone; tablet 5/6 — the box always matched the page on screen, but four taps on Next page
moved three pages (twice now; looking at whether a tap is dropped). Function 19/19 phone; tablet fails only AT-16 (box 2 after Find)
and my old print script. AT-13 5/5 phone (5.5–5.7 s), 5/5 tablet (10.0–11.2 s). Touch targets: unchanged from round 8.

## Round 10 / 10b / 10c (runs 42938865447, 42948523807, 42951440189; Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36)
Build from clean on SDK 10.0.403 + workload set 10.0.403: 0 errors, 0 warnings; `.aab` 42.75 MB, `.apk` 43.13 MB; as-built Release
launches with 0 crashes on phone and tablet.

| Area | Phone | Tablet |
|---|---|---|
| Save suite (files read back) — see the AT-18 table in BUGS.md | redacted copy, Flatten, print PASS; Save as new PDF blocked (AT-22); password, Bind, Reduce not proven | Save, Save as, form values, redacted, password, Flatten, rotated, print, Bind all PASS; Reduce not proven |
| AT-17 caret in a new text box | PASS (10b) | PASS (10, 10b, 10c) |
| AT-16 own check + drift suite | 7 of 7 | 7 of 7 |
| Rotated page (/Rotate 90) | shown turned, 1123 × 794 | shown turned, 596 × 421; mark saved in place, rotation kept |
| Excel grid + value bar (H-23) | 4 cells, headers, tab "Data"; A2 → "Chuvadi XLSX test cell" | same |
| Arrange drag / reorder | 2 of 2 dragged, reorder 1 of 1 | 0 — AT-20 (other route works) |
| Touch targets (AT-06) | 42 of 42 | 30 of 30 |
| Regression: function | 19 of 19 | 17 of 19 (the two are my old print step; print is covered and passes in the save suite) |
| Regression: design | all pass | all pass |
| AT-13 large image page | 5 of 5 (5.6–6.3 s) | 5 of 5 (8.1–8.5 s) |
| Cold Open with → page 1 (trace build, median) | 5,150 → 4,074 ms | 7,572 → 9,149 ms (AT-14) |

**Round 10c phone leg:** hung inside the emulator step for over an hour (the 10b phone leg took 20 minutes) and I cancelled it;
no results came back. The 10c changes it carried (putting the mark card away, password fields one at a time, folder picker for
Bind) are therefore unproven on the phone. One run, read, not retried.

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
- Round 10: the picker did not scroll to files below the fold (fixed 10b); Bind all asks for a folder, not a file name (fixed 10c);
  "Compress" is labelled "Reduce file size (Press)" and its card's `Press →` button is outside my card selector (still to fix).
