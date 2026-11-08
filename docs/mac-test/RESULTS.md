# Mac Test — results

Subject: `platform/mac` **7a65178**. Harness: `tests/mac/` + `.github/workflows/mac-test.yml` on `platform/mac-test`.
Runs (one each, read before the next — no retries):

| Round | Run | What changed in the harness |
|---|---|---|
| 0 | 42486517764 | first try — T1 passed up to the assembly-id step (my tool's NuGet config), probes skipped |
| 1 | 42487095203 | full plan; drove the app through the native menu bar and `open -a` |
| 2 | 42490785792 | menu bar and `open -a` found broken (M-01, M-02) → drive through ⌘O / ⌘K instead; quit-crash capture |
| 3 | 42494662734 | ⌘O found not to open a panel → the Open button; app stdout per launch; diagnostic exception build |
| 4 | 42517758923 | panel path set through Accessibility (typing into the Go-to field was lossy) → documents open; timing sets skipped |

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
WebView2 paints; the Mac "window" mark (warm 385–945 ms probe) is the comparable figure. Round 3 ran a Windows probe with the
same first-painted-frame rule (`tests/mac/win_firstframe.ps1`): median 615 ms, worst 1 805 — but the WPF window's own
native title bar already has ≥ 40 colours, so on Windows that rule fires when the window appears, not when WebView2
paints. Not comparable yet; a content-area-only rule is the next step (O-3).
**Linux:** Linux Test reports Blazor first render ≈ 1.25 s on its 2-core sandbox (B-12).

**Reading.** Hosted macOS runners are virtual machines without a GPU and vary 2× between runs (same build, round 1 vs
2), so absolute numbers belong to the friend's Mac (🖥). What is stable in every run on every runner: **WebView is ready
at 0.24–1.4 s and Blazor's first render comes 1.7–2.9 s later** — that gap is the startup cost, not the Mac host's own
work (main 64–210 ms warm). It matches the Mac chat's own §26 finding ("~1.5 s between WebView ready and Blazor's first
render"). Options are in M-06.

## Notes kept for the real Mac (added to the list in REAL-MAC-CHECKS terms)
- Retina sharpness, Gatekeeper first-open flow, a real printer, trackpad gestures — unchanged 🖥 items.
- Startup on real hardware: the runners can't give a meaningful absolute number (see above).

## Open options for the coordinator
**O-3 Windows first-render comparison.** A: crop the probe to the WebView2 content area (below the WPF title bar) —
cheap, same rule as Mac; B: ask the Reader chat for a `first-render` mark in the Windows host's startup log like the
Mac's — exact, but a change to an existing file in chuvadi-reader. **Recommendation: A** (test-side only).
