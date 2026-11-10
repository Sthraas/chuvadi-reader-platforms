# Mac Test — results

Subject: `platform/mac` **7a65178** → c6d7705 → 00a5975 → 83207af → b790370 → dd67166 → **812079f** (current). Harness: `tests/mac/` + `.github/workflows/mac-test.yml` on `platform/mac-test`.
Runs (one each, read before the next — no retries):

| Round | Run | What changed in the harness |
|---|---|---|
| 0 | 42486517764 | first try — T1 passed up to the assembly-id step (my tool's NuGet config), probes skipped |
| 1 | 42487095203 | full plan; drove the app through the native menu bar and `open -a` |
| 2 | 42490785792 | menu bar and `open -a` found broken (M-01, M-02) → drive through ⌘O / ⌘K instead; quit-crash capture |
| 3 | 42494662734 | ⌘O found not to open a panel → the Open button; app stdout per launch; diagnostic exception build |
| 4 | 42517758923 | panel path set through Accessibility (typing into the Go-to field was lossy) → documents open; timing sets skipped |

## Re-test on platform/mac 812079f (10 Nov, Foundation fc6286a) — current state

Runs **42729787491** (full suite, all runners), **42729700046**, **42736222709**, **42737825523** (new "shared" suite:
T4.0, M-08/09/10, M-14, T3.5 — all runners).

| Case | macOS 26 | macOS 15 | 15 Intel | Note / bug |
|---|---|---|---|---|
| M-08 Shortcuts labels | ✅ | ✅ | ✅ | "⌃Tab · ⌃⇧Tab" |
| M-08 ⌃Tab / ⌃⇧Tab switch tabs | ❌ | ❌ | ❌ | the active tab doesn't change, even after a click on the page |
| M-23 ⌘1 Go to tab 1 | ❌ | ❌ | ❌ | new; likely the same cause |
| M-09 no F11, Immersive label | ✅ | ✅ | ✅ | |
| M-10 green light "Zoom" | ✅ | ✅ | ✅ | |
| M-14 Details shows .NET text | ✅ | ✅ | ✅ | "Access to the path … is denied." |
| M-15 ⌘O opens the panel | ✅ | ✅ | ✅ | my earlier ❌ were a harness error (panel is layer 8) |
| M-21 Esc leaves Immersive | ✅ | ✅ | ✅ | |
| M-03 quit | ✅ | ✅ | ✅ | |
| M-18 recovery / T1.10 Licences | ✅ / ✅ | ✅ | ✅ | |
| T4.7 print vector, T4.8 no-print | ✅ | ✅ | ✅ | |
| T3.7 menus, T3.7c no Ctrl/F11/⌘Tab labels | ✅ | ✅ | ✅ | |
| T4.12–T4.14, T5.4, T5.5, T5.7, T5.9 | ✅ | ✅ | ✅ | |
| T4.6 passwords | ⚠️ harness (full suite) | ✅ | ✅ | still my typing on 26 in the long run; not Secure Event Input (checked: none held). Dedicated runs pass |
| T4.9 xlsx | ⚠️ | | | harness artefact (marker on sheet 2), as before |
| T5.3 heavy vector | ❌ | | | M-20 |

## Re-test on platform/mac dd67166 (10 Nov) — current state

Run **42718754219** (full suite, 10-run timing sets, all three runners).

| Case | macOS 26 | macOS 15 | 15 Intel | Note / bug |
|---|---|---|---|---|
| T3.5 Esc leaves Immersive | ✅ | ✅ | ✅ | **M-21 fixed** |
| T5.10 quit | ✅ | ✅ | ✅ | M-03 still fixed: 0 crash reports in 63 macOS 26 launches |
| T1.10 Licences | ✅ | | | tabs incl. .NET runtime; Mono notices shown — **T1.10 passes** |
| M-18 recovery | ✅ | ✅ | ✅ | as on b790370 |
| T3.7 menus | ✅ | ✅ | ✅ | |
| T4.0 ⌘O | ❌ | ❌ | ❌ | M-15 (in progress) |
| T4.7 print vector | ✅ | ✅ | ✅ | |
| T4.6 passwords | ⚠️ harness | ✅ | ✅ | on 26 the full suite's keystrokes still don't land after the print cases; the case now reports any leftover Secure Event Input holder (next run) |

T2 on dd67166 (probe, ms, median of 10): cold first render 26 **7 989**, 15 **6 185**, Intel **8 981**; warm first
render 2 958 / 2 517 / 3 009; Open panel → page **349** / 461 / 674. Windows same run: first render 1 689.
**The macOS 26 rise I flagged on b790370 did not continue**: Open panel → page fell from 985 to 349 ms and cold from
11.3 to 8.0 s on the same code path. That is runner noise, not a trend. What stays true across builds: cold starts on
these VMs are 6–9 s and warm first render ~2.5–3 s against Windows' ~1.7 s (M-06).

## Re-test on platform/mac b790370 (10 Nov, D-154) — current state

Runs **42697565346** and **42699530423** (passwords + M-18 recovery, all runners), **42697607808** (full suite, 10-run
timing sets, all runners).

| Case | macOS 26 | macOS 15 | 15 Intel | Note / bug |
|---|---|---|---|---|
| M-18 Accessibility press → recovery | ✅ recovered | ✅ (no crash) | ✅ (no crash) | same screen, tab kept, plain message, log line, no error bar |
| T1.10 Licences screen | ✅ opens | ✅ | ✅ | Licence agreement · Licence · Privacy · Third-party notices · .NET runtime (`screenshots/T1.10-b790370-licences-screen-macos15.png`); the Mono-notices check runs in the next full suite |
| T3.7 menus incl. Settings… ⌘, | ✅ | ✅ | ✅ | M-11 fixed; File has Open a file… ⌘O |
| T4.0 ⌘O opens the panel | ❌ | ❌ | ❌ | M-15 |
| T3.5 Esc leaves Immersive | ❌ | ❌ | ❌ | M-21 |
| T5.10 quit | ✅ | ✅ | ✅ | M-03 fixed (0 crash reports) |
| T4.7 / T4.8 print | ✅ / ✅ | ✅ / ✅ | ✅ / ✅ | |
| T4.6 passwords | ✅ (pw runs) | ✅ | ✅ | the full-suite failure on 26 is my typing, see harness note |
| T5.4, T5.5, T5.7, T5.9 | ✅ | | | |

T2 on b790370 (probe, ms, median (worst) of 10):

| Runner | Cold first render | Warm window / first render | PDF first page warm | Open panel → page |
|---|---|---|---|---|
| macos-26 | 11 290 (12 488) | 1 080 / 2 713 (3 069) | 3 044 | 985 (1 069) |
| macos-15 | 6 019 (7 711) | 651 / 2 600 (3 350) | 2 949 | 394 (492) |
| macos-15-intel | 6 127 (6 690) | 1 307 / 2 314 (2 387) | 2 171 | 713 (819) |
| Windows, same run | — | 622 / 1 683 (6 737) | — | — |

**Watch:** on macOS 26, Open panel → page has risen three builds running (00a5975 154 → 83207af 586 → b790370 985 ms), and
so has the cold first render (4.6 → 7.6 → 11.3 s). The other runners moved both ways. It starts with the
off-Ui-thread page rendering (b41f25c), but one run per build can't separate that from runner noise; see the status.

## Re-test on platform/mac 83207af (10 Nov) — current state

Rebased onto Foundation b41f25c (pages render off the Ui thread); Mac fixes for M-17, M-18, M-19, M-21, M-22 and M-03's
second form. Runs: **42673993820** (passwords + Settings, all runners), **42674315117** (full suite, 10-run timing sets,
all runners — the Intel job ran to the end, but GitHub failed to upload its evidence (`ENOTFOUND`), so Intel results come
from the job log only and it has no T2 numbers), **42676250705** (M-18 with WebKit log capture).

| Case | macOS 26 | macOS 15 | 15 Intel | Note / bug |
|---|---|---|---|---|
| T4.6 passwords | ✅ (pw run) | ✅ | ✅ | M-17 holds. In the full suite on 26 my keystrokes didn't land in the field (value read back empty) — test-side, the dedicated run passed |
| Settings › Appearance | ✅ mouse / ❌ AXPress | ✅ | ✅ | **M-18 re-scoped**: a mouse click works on 26; an Accessibility press crashes WebKit's web process inside Apple's accessibility layer and the Ui doesn't recover (run 42686357055) |
| Error log | ⚠️ | — | — | M-19: `chuvadi.log` now written, but with the follow-on dispose error, not the cause |
| T5.10 quit | ✅ | ✅ | ✅ | **M-03 fixed**: 0 crash reports in 64 macOS 26 launches |
| T3.5 Esc leaves Immersive | ❌ | ❌ | ❌ | M-21 not fixed |
| T4.7 print vector / M-22 | ✅ / ✅ | ✅ | ✅ | the local-network alert now explains itself |
| T4.8 no-print refused | ✅ | ✅ | ✅ | |
| T3.7 menus | ✅ | ✅ | ✅ | File 6 · View 33 · Document 11; no ⌘, (M-11), no ⌘O (M-15), Help empty |
| T4.12b snapshot → PNG | ✅ | ✅ | ✅ | the macOS 26 miss on 00a5975 was the test |
| T4.12, T4.13, T4.14 | ✅ | ✅ | ✅ | |
| T5.3 heavy vector | ❌ | | | never draws (M-20); many pages: first page 1.6 s (0.9 s on c6d7705) |
| T5.5 low memory | ✅ | | | now opens under pressure |
| T5.4, T5.7, T5.9 | ✅ | | | |
| T1.10 Licences | ⏳ | | | run 42689473198: every Settings section clicked with the mouse is fine on 26; the Licences button was still pressed through Accessibility and hit M-18 — harness now clicks it, next build |

**Page rendering — no hang seen.** All 40 timed launches on each runner drew their first frame; launch-with-PDF showed
the page 2/2; Open panel → page 10/10 on every runner. Open panel → first page (median / worst): macOS 26 **586 / 829 ms**
(00a5975: 154), macOS 15 **121 / 141 ms** (295). So it is faster on 15 but slower on 26.

T2 on 83207af (probe, ms, median (worst) of 10):

| Runner | Cold first render | Warm window / first render | PDF first page cold / warm |
|---|---|---|---|
| macos-26 | 7 641 (9 569) | 895 / 2 345 (2 415) | 9 907 / 2 830 |
| macos-15 | 3 315 (4 022) | 420 / 2 114 (2 171) | 3 629 / 2 323 |
| Windows, same run | — | 622 / 1 611 (1 852) | — |

## Re-test on platform/mac 00a5975 (9 Nov, D-148) — current state

Trimmed Catalyst Release launch (AT-03). Runs 42646315081 (full suite, all runners), 42656778614, 42658809276 and
42661249171 (password and M-18 cases, all runners). Anything not listed here is as on c6d7705 below.

| Case | macOS 26 | macOS 15 | 15 Intel | Note / bug |
|---|---|---|---|---|
| T1 build + audit | ✅ | — | — | trimmed bundle builds and launches |
| T3.7 menu bar | ✅ menus full | ✅ | ✅ | File 4 · View 26 · Document 10 everywhere, macOS 26 included (M-01 menus fixed); still no ⌘O (M-15), ⌘, (M-11), Help empty |
| T4.6 passwords | ✅ | ✅ | ✅ | AES-256/128, RC4, wrong → message → right, empty submit, owner-only — **M-17 verified fixed** |
| T4.7 print vector / T4.8 no-print refused | ✅ / ✅ | ✅ / ✅ | ✅ / ✅ | as on c6d7705 |
| T4.12 copy path / T4.13 Show in Finder / T4.14 single instance | ✅ | ✅ | ✅ | |
| T4.12b snapshot → PNG | ⚠️ | ✅ | ✅ | on 26 the drag didn't draw a region (Snapshot mode on, no selection) so only the earlier text was on the pasteboard; passed on 26 on c6d7705 — harness timing, re-run with the next build |
| Settings › Appearance | ❌ | ✅ | ✅ | **M-18 narrowed**: Appearance kills the Ui on macOS 26 from Home or Reader; Settings itself is fine. T1.10 Licences and T3.2 Settings shots unverified on 26 until fixed |
| T3.5 Esc leaves Immersive | ❌ | ❌ | ❌ | M-21 (D-148) |
| T5.10 quit | ❌ | ✅ | ✅ | M-03, 8 crash reports on 26 |
| Error log (D-132) | ❌ | ❌ | ❌ | M-19: 86 log folders, only `startup.log` |
| T5.4 many tabs, T5.7 network, T5.9 fresh/corrupt/read-only | ✅ | | | |
| T5.3 heavy vector, T5.5 low memory | ❌ | | | M-20 (D-148: on Arun's list with B-27) |

T2 on 00a5975 (probe, ms, median of 10): warm first render macOS 26 **2 106**, 15 **2 781**, Intel **3 997**; cold first
render 4 559 / 5 702 / 10 521. Open panel → first page 154 / 295 / 2 054. Windows in the same run: window 596, first
render **1 564** (client-area probe, D-127). Trimming did not change the Mac startup; Intel is slower than on c6d7705
(2 396) — same VM type, so most likely runner variance; I'll watch it on the next build before calling it.

## Re-verification on platform/mac c6d7705 (9 Nov) — current state

Runs 42534074875 (full + 10-run timing sets), 42538220489 (function cases) and 42548656656 (print), all three runners.
Bug statuses live in BUGS.md. The panel's Save-as-PDF sheet could not be driven reliably from outside (the M-22 alert
and the sheet's default name got in the way), so the vector check reads the job macOS hands to CUPS instead — the same
PDF Save as PDF writes.

| Case | macOS 26 | macOS 15 | 15 Intel | Evidence / bug |
|---|---|---|---|---|
| T1 build, tests, restore, bundle audit | ✅ | — | — | 0 warnings; Core 194/194, Hosting 59/59; 279 assemblies all Microsoft or Arun's; icon now in the bundle; legal files 0644; zip 47.7 MB, 495 files identical |
| T1.6 Launch Services | ✅ | ✅ | ✅ | |
| T2.3 launch with a PDF → page | ✅ 22/22 | ✅ 22/22 | ✅ 22/22 | M-02 fixed |
| T3.5 window | ✅ | ✅ | ✅ | 1100×720 centred, page at the top edge, minimise ✅ (M-04, M-07 fixed) |
| T3.6 Immersive ⌃⌘F | ✅ enters / ❌ Esc | ✅ / ❌ | ✅ / ❌ | M-21 |
| T3.7 menu bar | ⚠️ intermittent | ✅ except ⌘O, ⌘, | ✅ except ⌘O, ⌘, | M-01 (26), M-11, M-15 |
| T4.0 ⌘K at launch / ⌘O | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | M-15 (shared patch) |
| T4.1 Open panel → Reader | ✅ | ✅ | ✅ | M-16 fixed |
| T4.6 passwords | ❌ | ⏳ | ⏳ | prompt ✅; any submit kills the Ui — M-17 |
| T4.8 no-print permission | ✅ | ✅ | ✅ | Windows message shown, no panel, no CUPS job |
| T4.7 print → macOS panel, vector | ✅ | ✅ | ✅ | run 42548656656: "Print 2 pages" → native panel (preview) → Print to the paused test queue → the spooled job is a 2-page PDF made by macOS (Quartz PDFContext): fonts embedded as subset TrueType, **no images**, all text extractable incl. the free-text comment, **0 live annotations, 0 form fields** (flattened), marks drawn as vector (`evidence/T4.7-printed-annotated-macos15.pdf`, `screenshots/T4.7-printed-page1-rendered.png`). Page size follows the panel's paper (Letter on the en-US runner). macOS 26 also asks for local-network access (M-22) |
| T4.9 formats | ✅ | | | PDF, docx, xlsx (2 sheets, merged row), md, txt, html, Tamil name; Excel shows raw values (shared Sheets display text not released) |
| T4.12 clipboard text / PNG | ✅ / ✅ | ✅ / ✅ | ✅ / ✅ | File › Copy file path → path; View › Snapshot a region → Copy → `public.png` |
| T4.13 Show in Finder | ✅ | ✅ | ✅ | Finder selection = the file |
| T4.14 single instance | ✅ | ✅ | ✅ | 3 tabs in order, one process |
| T5.1 damaged / hostile | ✅ | | | truncated, bad xref, garbage, empty → "This PDF is damaged… rebuild as a new copy"; missing docx part → clear message; bomb.docx and far-cell.xlsx don't block the next open |
| T5.3 large | ✅ 500 pages / ❌ heavy vector | | | many-pages: first page 0.93 s, RSS 240 MB; heavy vector: M-20 |
| T5.4 many tabs | ✅ | | | 15 opened, RSS 207 → 232 MB, 15/15 restored |
| T5.5 low memory | ⚠️ | | | alive; the heavy file stays "Opening…" (M-20) |
| T5.7 network | ✅ | | | no sockets |
| T5.8 locale | ✅ | | | Ui unaffected by en-IN/de-DE/ta-IN; clock 24 h |
| T5.9 fresh / upgrade / corrupt / read-only | ✅ | | | no sample data on a fresh install now |
| T5.10 quit | ❌ | ✅ | ✅ | M-03 second form on 26 |
| Settings after the Reader | ❌ | — | — | M-18 |
| Error log (D-132) | ❌ | | | M-19 |

### T2 on c6d7705 (ms, median (worst), 10 launches each)

| Runner | Cold window / first render (probe) | Warm window / first render (probe) | Warm first render (app) | PDF first page — cold / warm (probe) | Open panel → first page |
|---|---|---|---|---|---|
| macos-26 arm64 | 2 422 / 4 014 (5 633) | 461 / 2 039 (2 151) | 2 008 | 4 838 (5 224) / 2 689 (2 901) | 161 (651) |
| macos-15 arm64 | 4 005 / 6 693 (9 088) | 870 / 2 916 (3 726) | 2 792 | 9 695 (11 801) / 4 840 (5 456) | 662 (912) |
| macos-15-intel | 4 864 / 6 541 (7 771) | 1 374 / 2 396 (2 782) | 2 431 | 7 436 (11 346) / 4 245 (7 107) | 793 (969) |
| Windows, same run (client-area probe, D-127) | — | 646 / 1 635 (1 890) | — | — | — |

Method as below (same probe, same rule). PDF first page = launch with the file (Finder double-click) → first frame
with the white page and its text. Open panel → first page = from pressing Open in the panel to the page on screen.
Reading: warm first render is 1.25–1.8× Windows' in the same run; window → first render takes 1.0–2.0 s on the Mac
runners against 1.0 s on Windows. Cold Mac launches remain 4–7 s on these VMs (M-06 open; real-Mac numbers will decide).

Runners: `macos-26` = macOS 26.7.2, Apple M1 (virtual), 1920×1080 · `macos-15` = macOS 15.7, Apple Silicon (virtual),
1920×1080 · `macos-15-intel` = macOS 15.7.9, Intel i7-8700B, 1920×1080. **No HiDPI mode on any runner** (every
display mode has pixel size = point size), so Retina could not be tested (real-Mac item). **macOS 12, 13, 14: no runner
images** — not testable here.

Legend: ✅ pass · ❌ fail (bug filed) · ⏳ not yet testable (blocked by a bug, re-run after the fix) · ℹ️ measured ·
🖥 real-Mac only.

## Summary

| Case | macOS 26 | macOS 15 | 15 Intel | Evidence / bug |
|---|---|---|---|---|
| T1.1 clean build, 0 warnings, warnings-as-errors | ✅ | — | — | run 42487095203 T1 job: "Build succeeded. 0 Warning(s) 0 Error(s)" |
| T1.2 Core + Hosting tests on macOS | ✅ 178/178, 48/48 | — | — | `t1-2-*.txt` |
| T1.3 restore audit | ✅ | — | — | 69 packages; every Chuvadi/LiPicons .nupkg SHA-512 = `ci/packages`; rest Microsoft |
| T1.4 universal | ✅ | — | — | the one Mach-O (`ChuvadiReader.Mac`) is x86_64 + arm64 |
| T1.5 Info.plist | ✅ | — | — | id `in.sthraas.chuvadi.reader`, copyright exact, PDF Editor + DOCX/XLSX/md/txt/log/html Viewer, all Alternate, `LSMinimumSystemVersion` 12.0, `UIDeviceFamily` [6], 1.0 (1) |
| T1.5 app icon | ❌ | ❌ | ❌ | **M-05** — no icon in the bundle; Dock shows the blank generic icon (`screen-with-dock`) |
| T1.6 Launch Services | ✅ | ✅ | ✅ | candidate for pdf/docx/xlsx/md/txt/html; default only for .xlsx, where no other app on the runner opens it |
| T1.7 ad-hoc signing | ✅ | — | — | `codesign --verify --deep --strict` ok; entitlements = `app-sandbox false` only; `spctl` rejected (expected unsigned → 🖥 Gatekeeper flow) |
| T1.8 zip round trip | ✅ | — | — | 46.6 MB zip; 484 files identical after `ditto -x` |
| T1.9 minimum OS | ✅ | — | — | `LC_BUILD_VERSION` platform 6 (Mac Catalyst) minos 15.0 = macOS 12 |
| T1.10 legal files | ✅ | — | — | five files in `Contents/Resources/legal`, repo texts byte-identical, DRAFT lines kept; mode bits **M-12** |
| T1.10 Licences tabs in the app | ⏳ | ⏳ | ⏳ | Settings opens cleanly on a fresh launch (T4.0b ✅ all runners); the Licences check waits for the harness's section names and for M-16 not to have fired |
| T1.11 no third-party code | ✅ | — | — | 277 assemblies: 214 Microsoft/.NET/MAUI (by key token or MAUI name), 63 Arun's (Chuvadi.*, ChuvadiReader.*, LiPicons); 0 unclassified; native links only `/System`, `/System/iOSSupport`, `/usr/lib`; 31 font files, all five families in THIRD-PARTY-NOTICES |
| T1.12 no test/dev code | ✅ | — | — | no .pdb, no DevTools, no Test/Preview assemblies |
| T2 startup | ℹ️ | ℹ️ | ℹ️ | below; **M-06** |
| T2.3 first page of a PDF | ❌ | ❌ | ❌ | launching with a PDF never shows it (**M-02**); through the Open panel the tab opens but no page is ever drawn (**M-16**) |
| T3.1 screens | ⏳ partial | | | Home (5 themes), Open panel, error states captured; Reader blocked by **M-16** |
| T3.2 five themes | ✅ Home | | | light, dark, palm, indigo, contrast seeded and shown on Home; kept on relaunch |
| T3.3 interface size 125/150 % | ⏳ | | | Home only; Reader blocked |
| T3.3 Retina | 🖥 | 🖥 | 🖥 | no HiDPI display mode on any runner |
| T3.5 traffic lights left, 15 px, gap 9 | ✅ | ✅ | ✅ | AX: Close @12, Minimize @36, Zoom @60, each 15×15 (pitch 24 = 15 + 9) |
| T3.5 minimise / zoom / close | ✅ | ✅ | ✅ | minimise → AXMinimized; zoom 1024×768 → 1920×971 and back; close quits the app (as Windows) |
| T3.5 zoom label | ❌ | | | **M-10** |
| T3.5 title-bar band | ❌ | ❌ | ❌ | **M-04** |
| T3.5 opening size | ❌ | ❌ | | **M-07** |
| T3.6 Immersive ⌃⌘F / F11 | ⏳ | ⏳ | ⏳ | needs an open document (M-02/M-15); no menu item for ⌃⌘F (M-01) |
| T3.7 menu bar | ❌ | ❌ | ❌ | **M-01**, **M-11** |
| T3.7 ⌘ labels in the Ui | ✅ Home | ✅ | ✅ | left bar "Open ⌘O", "Find ⌘F", top bar chip "⌘K"; Settings › Shortcuts not yet captured — code shows "⌘Tab" and "F11" there (**M-08**, **M-09**) |
| T4.0 keyboard reaches the app | ✅ ⌘K / ❌ ⌘O | ✅ / ❌ | ✅ / ❌ | ⌘K opens the bar right after launch, no click needed; ⌘O does nothing (**M-15**) |
| T4.1 Open panel | ✅ panel / ❌ view | ✅ / ❌ | ✅ / ❌ | Open button → native "Open a document" panel (Documents, sidebar, Cancel/Open); chosen file becomes a tab + recent; Reader never renders (**M-16**) |
| T4.12 clipboard, T4.13 Show in Finder, T4.7/T4.8 print, T4.6 passwords, T4.9 formats, T4.2–T4.5 | ⏳ | ⏳ | ⏳ | each needs a working Reader; after M-16 the Ui ignores every command, so these show nothing yet (no false fails filed) |
| T4.14 single instance | ❌ | ❌ | ❌ | one process (✅); files sent by `open -a` never arrive (**M-02**) — only the panel-opened tab exists |
| T4.15 folders | ✅ | | | state in `~/Library/Application Support/Chuvadi`, logs in `~/Library/Logs/Chuvadi`, WebKit data under the bundle id; nothing in `~/.config` |
| T5.5 low memory | ✅ | | | alive under `memory_pressure -l critical` (WebKit logged the pressure and cleared caches) |
| T5.7 network | ✅ | | | no socket from the app or its WebKit processes during the run, incl. an HTML page with a remote `<img>` (not opened — re-check after M-15) |
| T5.8 locale en-IN / de-DE / ta-IN | ⏳ | | | clock `HH:MM:SS` unchanged by locale; number formats need an open .xlsx |
| T5.9 corrupt settings | ✅ | | | `{ not json` → app starts with defaults, file left as is (not overwritten until a setting changes) |
| T5.9 read-only state folder | ✅ | | | app starts and runs |
| T5.9 upgrade (dark, 125 %) | ✅ | | | both kept |
| T5.9 fresh install | ❌ known | ❌ | ❌ | sample Home data (D-94 H-12, not re-filed) |
| T5.10 quit | ❌ | ✅ | ✅ | **M-03** on macOS 26 (⌘Q and terminate) |
| T5.1, T5.3, T5.4 | ⏳ | | | need a working Reader (M-16) |

## T2 — startup (ms)

Two clocks. **Probe** = my `macdrive firstframe`: from the `NSWorkspace` launch call to (window on screen) and (first
captured frame with painted Ui, ≥ 40 colours — Home). **App** = the app's own `startup.log`, from process start.
Cold = `sudo purge` before each launch; warm = back-to-back. 10 launches each; median (worst).

| Runner | Round | Cold — probe | Cold — app | Warm — probe | Warm — app | Warm: main → WebView ready → first render (app) |
|---|---|---|---|---|---|---|
| macos-26 arm64 | 1 | 3 607 (7 369) | 4 466 (5 567) | 2 381 (3 201) | 2 200 (2 446) | 93 → 360 → 2 200 |
| macos-26 arm64 | 2 | 9 700 (10 614) | 8 475 (9 474) | 3 542 (4 993) | 3 496 (4 059) | 168 → 650 → 3 496 |
| macos-15 arm64 | 1 | 4 656 (5 669) | 4 181 (5 225) | 2 647 (2 858) | 2 431 (2 657) | 126 → 458 → 2 431 |
| macos-15 arm64 | 2 | 3 260 (3 553) | 2 991 (3 357) | 2 080 (2 090) | 1 918 (1 945) | 64 → 239 → 1 918 |
| macos-15-intel x64 | 1 | 8 216 (9 681) | 7 678 (8 431) | 2 403 (5 537) | 2 442 (5 081) | 158 → 1 041 → 2 442 |
| macos-15-intel x64 | 2 | 10 874 (13 805) | 10 464 (12 889) | 4 133 (7 136) | 4 134 (7 048) | 210 → 1 426 → 4 134 |

First launch after install (LaunchServices registration, WebKit first run), probe first render: 6.3 s (26), 6.2 s (15),
15.4 s (Intel).

**Windows, same CI class** (`windows-latest`, `scripts/measure-startup.ps1 -ReadyToRun`, "window shown", 10 runs):
median 618 / 508 / 597 ms in three runs, worst (the first, cold) 3.7–5.3 s. That metric stops at the window, before
WebView2 paints; the Mac "window" mark (warm 385–945 ms probe) is the comparable figure. **Windows first render, same rule as the Mac (D-127, test side only — no app change).** `tests/mac/win_firstframe.ps1`
on `windows-latest`, run 42521735970, ReadyToRun publish, 10 back-to-back launches:

| | Window shown | First painted frame of the Ui |
|---|---|---|
| Windows (WPF + WebView2), warm | median **436** ms (worst 491) | median **1 141** ms (worst 1 301) |
| Mac, macos-15 arm64, warm (round 2 / round 1) | 385 / 573 ms | 2 080 / 2 647 ms |
| Mac, macos-26 arm64, warm (round 1 / round 2) | 545 / 944 ms | 2 381 / 3 542 ms |

**Method, so the comparison is fair.**
- **Same clock start.** Both probes start timing at the launch call: `Start-Process` on Windows, `NSWorkspace` on Mac.
- **Same rule.** Both count the first captured frame of the app's own content showing ≥ 40 distinct colours. On Windows
  that is the client area only, below the WPF title bar. The Mac has no native title bar.
- **Same scope.** Both measure Home on an empty state with the light theme.
- **Different capture rate.** Windows captures with `PrintWindow(PW_RENDERFULLCONTENT)`, which takes 150–250 ms per
  frame on the runner, so the Windows figure can be up to about 0.2 s late. The Mac captures every 10–30 ms.
- **Fixes along the way.** An earlier screen-copy version counted a window still covered by the console as painted.
  The version before that counted the WPF title bar's own colours. Both are corrected; those numbers are discarded.
- **Runners differ.** The Windows and Mac runners are different VMs, so treat the ratio, not the absolute numbers, as
  the finding.

**Reading:** Windows paints Home about 0.7 s after its window appears. The Mac takes 1.5–2.6 s from window to first
paint (2–3× Windows) on every Apple Silicon runner and round. That is the Blazor-in-WKWebView start-up gap behind M-06.

**Linux:** Linux Test reports Blazor first render ≈ 1.25 s on its 2-core sandbox (B-12).

**Reading.** Hosted macOS runners are virtual machines without a GPU and vary 2× between runs (same build, round 1 vs
2), so absolute numbers belong to the friend's Mac (🖥). What is stable in every run on every runner: **WebView is ready
at 0.24–1.4 s and Blazor's first render comes 1.7–2.9 s later** — that gap is the startup cost, not the Mac host's own
work (main 64–210 ms warm). It matches the Mac chat's own §26 finding ("~1.5 s between WebView ready and Blazor's first
render"). Options are in M-06.

## Notes kept for the real Mac (added to the list in REAL-MAC-CHECKS terms)
- Retina sharpness, Gatekeeper first-open flow, a real printer, trackpad gestures — unchanged 🖥 items.
- Startup on real hardware: the runners can't give a meaningful absolute number (see above).

## Decided
- **O-3 → A (D-127, 9 Nov):** Windows first render measured on the test side only; results and method above.
