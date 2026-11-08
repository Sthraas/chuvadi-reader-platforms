# Mac Test — test plan

Chat: **Mac Test** (opened by D-99). Subject under test: `platform/mac` at **7a65178** ("Mac docs: legal texts
verified on the Mac runner (run 42315335992)"). Rule: **nothing passes until I have seen it work** — every
pass/fail is judged on my own evidence (pixels, files on disk, the bundle itself, process state), never on the
Mac chat's reports or CI summaries.

## Environment

There is no Mac in the programme yet. Everything below runs on GitHub-hosted macOS runners (public repo, free
minutes — D-93), from `.github/workflows/mac-test.yml` on branch `platform/mac-test`. One run, then read it — no
retry loops.

| Runner label | macOS | CPU | Used for |
|---|---|---|---|
| `macos-26` | 26 Tahoe | Apple Silicon (arm64) | clean build + package (the only image with Xcode 26.6, which the pinned workload needs), then the full test set |
| `macos-15` | 15 Sequoia | Apple Silicon (arm64) | install the built zip, startup, smoke, function subset |
| `macos-15-intel` | 15 Sequoia | Intel (x86_64) | install the built zip, startup (x64 slice, JIT-free AOT? — measured), smoke, function subset |

**Not testable on runners:** macOS 12 Monterey, 13 Ventura and 14 Sonoma (no hosted images any more; macOS 14 left
GitHub on 2 Nov 2026). The minimum (macOS 12, `LSMinimumSystemVersion`) is checked statically in the bundle
(T1.5, T1.9) and stays a real-Mac item. Real printers, trackpad gestures, Retina panels, two displays, iCloud
Drive, Gatekeeper on a quarantined download and the Dock stay in `docs/mac/REAL-MAC-CHECKS.md`; I add to that
list anything I find runners can't see.

Test tools (testing only, never shipped): my own Swift driver `tests/mac/macdrive.swift` (Accessibility API,
CGEvent, CGWindowList capture, menu-bar walk), `osascript`/System Events, `screencapture`, Python 3 (test-file
generator, image diff), Homebrew `qpdf` and `poppler` (pdffonts, pdfimages, pdftotext, pdfinfo), CUPS with a
file-backed test queue (print capture), headless Chrome (handout frames; the Ui through the Foundation's
dev-only preview host as the Chromium/WebView2 reference), `otool`, `nm`, `lipo`, `codesign`, `spctl`.

## T1 Build and package from clean
| ID | Case | Pass when |
|---|---|---|
| T1.1 | Fresh checkout, empty NuGet cache, `ci/nuget.config`, pinned workload 10.0.401, Xcode 26.6, `dotnet build -c Release` of `ChuvadiReader.Mac` | 0 warnings, 0 errors (TreatWarningsAsErrors is on) |
| T1.2 | Core + Hosting tests on macOS | all pass |
| T1.3 | Restore audit (`project.assets.json` of the Mac project) | only Microsoft.* / System.* / runtime packs, Arun's Chuvadi.* and LiPicons.*; every Chuvadi .nupkg resolved from `ci/packages`, SHA-256 equal to the feed file |
| T1.4 | Universal binary | `lipo -archs` = x86_64 arm64 on the main executable **and every** Mach-O in the bundle (no single-arch dylib) |
| T1.5 | `Info.plist` | `CFBundleIdentifier` = provisional `in.sthraas.chuvadi.reader`; `NSHumanReadableCopyright` exact; `LSMinimumSystemVersion` ≤ 12.0; `CFBundleDocumentTypes` PDF (Editor), DOCX, XLSX (+ md/txt/log/html Viewer), rank Alternate; `UIDeviceFamily` 6; version strings; no stray iOS keys that change behaviour |
| T1.6 | Launch Services | after `lsregister`, the app is a candidate handler for `.pdf`, `.docx`, `.xlsx` (`LSCopyApplicationURLsForURL` via my driver); it does **not** become the default handler for any of them |
| T1.7 | Ad-hoc signing | `codesign --verify --deep --strict` passes; entitlements = only `app-sandbox false`; `spctl -a` result recorded (expected: rejected, unsigned — real-Mac item for Gatekeeper UX) |
| T1.8 | Unsigned zip | `ditto -x` of the zip gives a bundle byte-identical to the built one (file list + SHA-256 of every file); size recorded |
| T1.9 | Minimum macOS | every Mach-O `LC_BUILD_VERSION` minos ≤ 12.0 (Mac Catalyst 15.0); no symbol bound weakly-only that exists after 12 without a guard — `otool -l` per binary |
| T1.10 | Legal | `Contents/Resources/legal/` has LICENSE, EULA, THIRD-PARTY-NOTICES (byte-identical to repo), DOTNET-RUNTIME-THIRD-PARTY-NOTICES, DOTNET-MACCATALYST-LICENSE; DRAFT lines kept; Settings › About › Licences shows every tab incl. ".NET runtime" (screenshot) |
| T1.11 | Bundle audit — no third-party code | every file in the bundle classified: Apple frameworks (linked from `/System`), .NET/MAUI (Microsoft-signed assemblies or Microsoft runtime pack natives), Chuvadi/LiPicons/app assemblies, fonts (listed in notices), web assets from the Ui. Every `.dll` identified by assembly name + public key token; every native linked library from `otool -L` resolves under `/System`, `/usr/lib` or inside the bundle with a Microsoft origin. Anything else = bug |
| T1.12 | No test/dev code shipped | no `Microsoft.AspNetCore.Components.WebView.Maui` DevTools enabled in Release; no Preview/Test assemblies; no `.pdb` |

## T2 Startup speed (ms)
Two independent clocks, cross-checked: (a) the app's own `CHUVADI_STARTUP` marks (process start → main → window →
webview-ready → first-render), read from `~/Library/Logs/Chuvadi/startup.log`; (b) **my external probe** —
`macdrive firstframe` launches through LaunchServices (`NSWorkspace.openApplication`, as a double-click does) and
captures the window ~every 8 ms with CGWindowList, timing from the launch call to: window on screen, first frame
with painted chrome (top bar colour present), and for a PDF the first frame with a white page holding dark
glyph pixels. The probe never relies on the app.
| ID | Case | Runs |
|---|---|---|
| T2.1 | **Cold**: `sudo purge` (file cache) before each launch, app quit fully between runs — first rendered frame | 10 per runner |
| T2.2 | **Warm**: back-to-back launches | 10 per runner |
| T2.3 | **First page of a PDF**: launch with a 5-page vector PDF (`open -a Chuvadi file.pdf`), cold and warm | 10 + 10 per runner |
| T2.4 | First launch after install (LaunchServices registration, WebKit first-run) — reported separately, not in the medians | 1 per runner |
| T2.5 | Report median and worst for arm64 (macos-26, macos-15) and x64 (macos-15-intel); compare with Windows (`scripts/measure-startup.ps1 -ReadyToRun` on `windows-latest`, same run, plus Foundation `STARTUP.md`) and Linux (Linux Test T2 numbers) — method differences stated |

## T3 Design fidelity
| ID | Case |
|---|---|
| T3.1 | Screens: Home (first run and with recents), Library, Reader in Read / Mark / Arrange / Protect, each rail hover-expanded, Document menu, View menu, ⌘K bar, Print card, Settings (every section), Licences, a Word and an Excel tab, an error state, a password prompt |
| T3.2 | All five themes (light, dark, palm, indigo, contrast) — seeded via `settings.json` `theme` before launch, then confirmed on screen |
| T3.3 | Scale: the runner's own display (1×) and HiDPI 2× if the virtual display offers a HiDPI mode (switched with CoreGraphics); Interface size 100/125/150 % |
| T3.4 | Reference: handout frames (`Reader Side Rails`, `Chuvadi Revamp v3` Mac frame) rendered in headless Chrome at the same CSS size; Windows look = the same Ui in Chromium through the dev-only preview host (WebView2 is Chromium), same theme and window size. Pixel diff with a noise threshold (anti-aliasing / font hinting band stated); every region above noise is reported as a bug or an explained engine difference |
| T3.5 | Mac specifics: traffic lights on the **left**, 15 px dots, 9 px gap, colours #ff5f57/#febc2e/#28c840 (measured from pixels); no native title bar or second set of buttons; red/yellow/green actually close/minimise/zoom (window state via AX); double-click on the bar zooms |
| T3.6 | Full screen: green button and ⌃⌘F (Immersive) behaviour; Esc leaves Immersive; native Enter Full Screen menu item absent (decision 6 Nov) |
| T3.7 | Menu bar: menus exactly Chuvadi, File, Edit, View, Document, Window, Help (no Format); every item's shortcut shown with ⌘/⇧/⌥/⌃ glyphs; **no "Ctrl" text in any label in the menu bar or in the Ui** (Ui scanned through AX text + screenshots: status bar, ⌘K chip, tooltips, Settings › Shortcuts, menus) |
| T3.8 | Fonts really loaded in WKWebView (LiPi Sans, Instrument Serif, Fraunces, Plex Mono, Tiro Tamil) — glyph metrics in the screenshot vs Chromium reference |

## T4 Function (parity with the Windows Reader)
Driven by the native menu bar (every Chuvadi command is there), ⌘ shortcuts, and AX presses on Ui buttons; results
checked on disk with qpdf/poppler, not on screen alone.
| ID | Case |
|---|---|
| T4.1 | Open: File › Open panel (path typed with ⇧⌘G), `open -a`, Finder-style Open With (LaunchServices `openURLs`), launch with a file; view, zoom (⌘+ ⌘− ⌘0, View rail), page nav, Find (⌘F) hit count |
| T4.2 | Annotate (Mark: highlight, note, ink, text, stamp), Save (⌘S) and Save as; reopen; `qpdf --json` shows the annotations; `pdftotext` unchanged text |
| T4.3 | Forms: fill a text field and a checkbox, save, values in the AcroForm; Sign (certificate signature with a test .pfx — F6 fix on Mac Catalyst) and signature verification banner |
| T4.4 | Redact: text really removed (`pdftotext` no longer finds it), not just covered |
| T4.5 | Arrange / Bench: reorder, rotate, delete, merge (3 files), split; page counts and order of the output |
| T4.6 | Encryption: Password-protect a copy (AES-256), open it with right and wrong password; open user-password and owner-only files |
| T4.7 | Print: File › Print → macOS print panel → PDF › Save as PDF (and a CUPS file-backed test queue): output **vector** — `pdffonts` lists fonts, `pdfimages -list` has no page-sized images, `pdftotext` matches the source, page sizes/orientation kept; page ranges "3, 1" and current page; flattened (no live annotations / form fields left in the printed PDF, D-57) |
| T4.8 | A file whose permissions forbid printing (`qpdf --print=none`): Print locked with the Windows message; the panel never opens; no CUPS job. Owner-password case recorded against D-71 |
| T4.9 | Word and Excel: open `.docx` / `.xlsx` (text, table, formats, merged cells, several sheets) — as far as Docs 1.1.0 / Sheets 1.1.2 allow (Layout not released: noted, not a bug) |
| T4.10 | Panels: Open (types filter, multiple for Bench), Save (name pre-filled, asks before replace), folder chooser (New Folder) |
| T4.11 | Drag from Finder: 1 file, 3 files (3 tabs in drag order), Bench open (all to shelf), an unsupported `.zip` (nothing, no error) — synthesised drag session via the driver; real Finder drag stays a real-Mac item if the runner can't synthesise it |
| T4.12 | Clipboard: copy text from a page → `pbpaste`; copy page/region as image → pasteboard has `public.png`, decodes, right size and colours |
| T4.13 | Show in Finder: Finder window opens with the file selected (AX of Finder) |
| T4.14 | Single instance: app running with a file; `open -a` two more files, Open With, and a second `open -n` attempt → one process, one window, each file in its own tab, in order |
| T4.15 | Folders: state in `~/Library/Application Support/Chuvadi`, logs in `~/Library/Logs/Chuvadi`, saves default to `~/Documents`; nothing written in `~/.config`, the bundle, or `/tmp` left behind after quit; not sandboxed (by design, D-15) — files outside the home folder (e.g. `/Volumes`, `/tmp`) open and save |
| T4.16 | Links: http/https/mailto in a PDF go to the default handler; `javascript:`/`file:` refused |

## T5 Robustness
| ID | Case |
|---|---|
| T5.1 | Damaged PDFs (truncated, bad xref offset, garbage, empty), damaged docx/xlsx (zip bomb, missing parts, far cell) — message, no crash, no hang, later opens still work (Linux Test B-07..B-11 re-checked on Mac) |
| T5.2 | Encrypted: user password RC4/AES-128/AES-256, owner-only, wrong password |
| T5.3 | Very large: the 7.9 MB vector CAD PDF (**not reachable from here — needs Arun's file**); stand-ins: generated 8 MB heavy-vector page, 500-page text PDF — open time, scroll, memory |
| T5.4 | Many tabs (30), memory (RSS) over time, quit and relaunch restores tabs |
| T5.5 | Low memory: memory pressure (`memory_pressure -l critical`) while documents are open; app stays responsive or fails with a message |
| T5.6 | No printer (runner default) — Print still offers Save as PDF, no error; CUPS stopped |
| T5.7 | No network: outbound blocked with the macOS packet filter (`pfctl`) — app starts, opens, prints to PDF; and a check that the app makes **no network connection at all** in normal use (`nettop`/`lsof -i` sampled during the run) |
| T5.8 | Locale: region en-IN (`defaults write -g AppleLocale en_IN`), also de_DE and ta_IN — dates, numbers, sizes, clock; Tamil file names |
| T5.9 | Fresh user (state folders and WebKit data removed); upgrade with existing settings (seeded `settings.json` from a previous build, corrupt `settings.json`, read-only state folder) |
| T5.10 | Quit with unsaved marks (⌘Q) — asks or recovers as on Windows; crash recovery file on next start |

## Reporting
- `docs/mac-test/RESULTS.md` — every case, pass/fail, evidence (run id, artifact, file).
- `docs/mac-test/BUGS.md` — each bug: steps, expected, actual, evidence, severity **S1** crash/data loss/security ·
  **S2** feature broken · **S3** wrong but usable · **S4** cosmetic; owner **Mac** (host) · **Shared** (existing Ui/Core/
  Hosting — goes to Arun/Foundation as a listed change) · **Library** (Chuvadi library ask). Bugs already filed by
  Linux Test that reproduce on Mac are cross-referenced, not re-filed.
- `docs/mac-test/screenshots/` — evidence images (PNG, kept small).
- Every bug goes to the Mac chat through the coordinator; I re-verify each fix on its commit.

## Options for the coordinator
**O-1 Time to first PDF page — whose clock**
| Option | Pros | Cons |
|---|---|---|
| A. External probe only (screen capture, ~8 ms resolution) | No app change; measures what a person sees | Resolution bound by capture rate; needs Screen Recording on the runner |
| B. Ask the Mac chat for a `first-page` mark in `StartupTimeline` (host-only, new code) | Exact, cheap, also visible on Arun's and the friend's Mac in `startup.log` | A small Mac-host change; first-page is only known to the Ui (needs a hook the Mac host can see) |
| **Recommendation:** A now (no dependency); B as a follow-up if the Mac chat can do it without touching existing files. | | |

**O-2 Windows reference for design fidelity**
| Option | Pros | Cons |
|---|---|---|
| A. Ui in Chromium via the dev-only preview host | Same engine family as WebView2; runs anywhere; deterministic | Not the WPF window itself (no WPF chrome) |
| B. Real WPF app screenshots on `windows-latest` | The real Windows build | The runner's interactive desktop is 1024×768 by default and may not render WebView2 GPU-composited; heavier |
| **Recommendation:** A for every screen, B for Home + Reader in light/dark as a spot-check. | | |
