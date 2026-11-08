# Android Test — test plan

Independent testing of Chuvadi Reader for Android (D-122). Nothing is assumed to work until seen
working. The Android chat's rounds 3–7 are its own checks; these are separate and go further.

## What is tested
The composition that will ship: `platform/foundation` + `platform/mobile-ui` (merged) + pending hooks +
`platform/android` host, built from clean by the Android chat's own `compose.sh`, at the refs given to
each run (round 1: Foundation `839d39d`, Mobile UI `95b9d79`, Android `7ec8017`).
**The Release package is what gets tested** — the universal Release `.apk` from the same build as the
`.aab` — not the Debug build the Android chat's CI uses. Debug is used only where Release can't be
inspected, and that is stated beside the result.

## Where
GitHub Actions on this public repo (`.github/workflows/android-test.yml`, manual dispatch, **one run per
round, no retry loops**). Emulators: `pixel_7` phone and `pixel_tablet`, `google_apis` x86_64, API 35 and
API 36, no hardware keyboard.

**API 35 and WebView.** The API 35 image ships WebView 124; the app (D-105) then shows only its update
screen, so the Android chat never ran the Reader on Android 15. Real Android 15 devices get WebView
updates through Play. A *donor* job pulls the API 36 image's Google WebView and installs it on the API 35
emulators as an update (same package, same signer), so the Reader is tested on Android 15 too. The
update screen itself is re-checked on a stock API 35 image (R-08).

Test tooling (never shipped): emulator runner, setup actions, bundletool, reportlab, pypdf, Pillow,
websocket-client (DevTools), headless Chrome for the handout frames. Scripts in `docs/android-test/ci/`.

## Reporting
`RESULTS.md` (every case, pass/fail, evidence: run id + artifact path), `BUGS.md` (steps, expected,
actual, evidence, severity, owner: Android host / Mobile UI look / Foundation shared Ui-Core / library),
`screenshots/`. Severity: **S1** blocks release or loses data · **S2** feature broken or wrong · **S3**
visible defect with a workaround · **S4** cosmetic.

---

## 1. Build and package (build job, from clean)
| # | Case | Pass when |
|---|---|---|
| B-01 | Compose + restore + Release publish from a clean runner | 0 errors, **0 warnings** (rule 7), `.aab` and `.apk` produced |
| B-02 | Debug x64 build | builds, 0 warnings |
| B-03 | Manifest | minSdk 35, targetSdk 36, not debuggable, allowBackup false, data-extraction rules, no cleartext |
| B-04 | Permissions | none beyond what a feature needs (expect none; INTERNET absent) |
| B-05 | App id | placeholder `in.chuvadi.reader` everywhere (manifest, FileProvider authority) |
| B-06 | Signing | Release signed only with a debug/test key; no keystore in the repo; README steps for the upload key correct |
| B-07 | Size | `.aab`, universal `.apk`, and bundletool per-device download size (arm64, x86_64) recorded |
| B-08 | AOT / ReadyToRun | which startup compilation the Release uses (profiled AOT / full AOT / R2R / JIT), with evidence |
| B-09 | No third-party code | every managed assembly and every Java package in the dex listed; anything not .NET / MAUI / Android / Chuvadi flagged |
| B-10 | Licences | Sthraas copyright in the assembly info and About; Licences page shows EULA, third-party notices and the ".NET runtime" tab; notices cover everything that ships (incl. AndroidX/Kotlin if present) |
| B-11 | Play data safety | `legal/store/PLAY-DATA-SAFETY.md` matches the package: permissions, SDKs, network, backups |

## 2. Startup speed (all four emulators, Release)
Device-clock milliseconds from ActivityTaskManager's launch to: Android's first frame (`am start -W`),
the Blazor UI painted (in-page probe), and for Open with, page 1's SVG painted. 12 runs each (≥ 10),
one discarded warm-up. Cold = force-stop + drop caches; warm = process alive, activity destroyed
("Don't keep activities"); hot = Home and back. Report median and worst; runs where the probe arrived
after the UI was ready are reported separately as upper bounds.
| # | Case |
|---|---|
| S-01 | Cold launch → first frame / UI |
| S-02 | Warm launch → first frame / UI |
| S-03 | Hot launch → first frame |
| S-04 | Cold Open with (PDF) → first frame / first page |
| S-05 | Memory after load (PSS) |

## 3. Design fidelity
| # | Case |
|---|---|
| D-01 | Screenshot every screen: Home, Library, Settings, Read, Mark, Arrange, Protect; phone also Tabs sheet, ⋮ sheet, Protect View sheet — × 5 themes × portrait + landscape × phone + tablet × API 35 + 36 |
| D-02 | Frame-by-frame against the handout: 12d (tablet Read, landscape), 12e (tablet Mark), 12f (tablet Arrange, portrait), 12g–12j (phone Read, Mark, Arrange, Protect + View sheet). Rails 72 / 72 / 60 px; phone app bar, bottom bar, tool strip, FAB |
| D-03 | Touch targets: every visible control ≥ 44 dp (fail), 44–47 dp listed (handout asks 48) |
| D-04 | No sideways overflow on any screen |
| D-05 | Safe areas: nothing under the status bar, navigation bar or camera cut-out; edge-to-edge (API 35 enforces it) |
| D-06 | System dark mode: app keeps its theme, status/nav bar icons stay legible in every theme |
| D-07 | Split screen (half and third), freeform resize: layout switches phone ↔ tablet correctly |
| D-08 | On-screen keyboard: fields stay visible, nothing hidden behind the keyboard |
| D-09 | Interface size 100 / 125 / 150 % on phone and tablet |
| D-10 | Real Settings tap changes theme and it persists across restart |

## 4. Function (Release, real touch where it matters)
| # | Case |
|---|---|
| F-01 | Open: system picker (SAF) from Home "Open", Share to Chuvadi, Open with (pdf, docx, xlsx), while running and cold |
| F-02 | View: page navigation, swipe, pinch zoom, double-tap zoom and back, Fit page / width, rotate page |
| F-03 | Find: text found on the right page, count, next/previous, with the on-screen keyboard |
| F-04 | Annotate (Mark): text box, highlight, note, freehand, shape, image; undo/redo; saved annotations reopen |
| F-05 | Sign: signature placement (and the gated digital signature state) |
| F-06 | Forms: text field, checkbox, choice filled and saved |
| F-07 | Redact (Protect): box redaction, Save redacted copy; redacted text really gone (extract text from the saved file) |
| F-08 | Arrange: long-press drag reorder, delete, rotate, insert, merge two files, split; saved result has the new order |
| F-09 | Save and Save as: to the original (content URI write-back), Save as to a new SAF location; file valid; original untouched by Save as |
| F-10 | Encryption: open user-password file (prompt), wrong password, owner-only file; set a password and reopen |
| F-11 | Print: Android print dialog, vector (saved PDF contains text operators, no full-page images), range, no-print file refused (L-8), owner-password file (D-102) |
| F-12 | Back (P-06, P-07): closes sheet/card first, walks screens, then leaves; no dead presses |
| F-13 | WebView gate (D-105): stock API 35 (WebView 124) shows the update screen; after updating, the Reader appears without restart |
| F-14 | Rotation with an open document and open card: same page, same zoom, card state kept |
| F-15 | Process death and restore: `am kill` in background, return → tabs and page restored; unsaved markup kept or warned |
| F-16 | Low memory: `am send-trim-memory` RUNNING_CRITICAL / COMPLETE, then use: no crash |
| F-17 | Single instance: Open with while running adds a tab in the same task (no second activity) |
| F-18 | Clipboard copy text, external links open the browser, Share out |

## 5. Robustness
| # | Case |
|---|---|
| R-01 | Damaged files: truncated, broken xref, random bytes named .pdf, 0-byte — clear message, no crash, app usable after |
| R-02 | Encrypted files (user / owner) |
| R-03 | Very large: 600-page PDF (scroll to the end, find), 28 MB image page — no ANR, memory bounded |
| R-04 | Cloud-provider content URIs (a DocumentsProvider URI, not MediaStore; virtual/streamed files; a URI whose grant is revoked mid-session) |
| R-05 | No network (airplane mode): everything works, nothing tries the network (logcat / netstats) |
| R-06 | en-IN locale (and a non-Latin system language): dates, numbers, no layout breaks |
| R-07 | Fresh install: first-run box, no sample files (H-12), no name on Home (A-10) |
| R-08 | Upgrade install over the previous build: settings, recents, drafts kept |
| R-09 | Uninstall leaves nothing in shared storage |
| R-10 | No crash / ANR / console error over the whole run (logcat FATAL, ANR, chromium console errors) |

## Rounds
1. Build + audit, startup, design sweep (all four emulators).
2. Function suite (F-01..F-18).
3. Robustness (R-01..R-10) and re-verification of fixed bugs.
Each round: one dispatch, read the run, file bugs, push BUGS.md.
