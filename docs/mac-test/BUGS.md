# Mac Test — bugs

Build under test: `platform/mac` **7a65178**, built from clean by my workflow (run 42487095203, T1 job), installed from
`Chuvadi-mac-universal-unsigned.zip` into `/Applications` on each runner.
Runners: `macos-26` (26.7.2, Apple M1 virtual), `macos-15` (15.7.x, Apple Silicon virtual), `macos-15-intel` (15.7.9,
i7-8700B). All three are virtual machines with no GPU and a 1920×1080 (or 1024×768) non-Retina display.
Severity: **S1** crash / data loss / security · **S2** feature broken · **S3** wrong but usable · **S4** cosmetic.
Owner: **Mac** = Mac chat (host code) · **Shared** = existing Ui/Core/Hosting (Foundation / Reader chat, via Arun) ·
**Library** = Chuvadi library ask. Every bug gets fixed; I re-verify each fix on its commit and mark it here.

| ID | Sev | Owner | Title | Seen on | Status |
|---|---|---|---|---|---|
| M-16 | S1 | Mac | Opening any document through the Open panel adds the tab and the "Pick up where you left off" card, then the Ui dies: Blazor's "An error occurred" bar (hidden behind the status bar — only a red line shows) and the Reader never renders; every later click does nothing until relaunch | 15 (26, 15-intel in run 42517758923) | fixed 69640cb (trimmed Platform DI types, after the tested 7a65178) — re-verify through the Open panel (run 42522959467: hand-over → /reader rendered, error bar hidden, no Error logs). Error bar under the status bar: Shared, for Foundation |
| M-01 | S2 | Mac | macOS menu bar has no Chuvadi commands: File, Document and Help are empty; View has only ⌘K and the system's Enter Full Screen | 26, 15, 15-intel | partly fixed ca3fd1d (View, Document, Print ⌘P, no Enter Full Screen — run 42522959467); File › Open… ⌘O waits on the shared global-commands patch (Foundation) |
| M-02 | S2 | Mac | Files handed over by macOS never open — at launch (Open With / double-click) and while running (`open -a`, Dock); single instance can't work | 26, 15, 15-intel | fixed 09bab61 (+ca3fd1d, 69640cb) — re-verify (run 42522959467: launch file and running hand-over → tabs, one process) |
| M-03 | S1 | Mac | Crash on quit on macOS 26: `ObjectDisposedException` (IServiceProvider) in MAUI's `PageViewController.TraitCollectionDidChange` while AppKit saves window state → SIGABRT, "quit unexpectedly" | 26 (intermittent: 25/41 quits in round 1, 2/2 in round 3's second session, 0/2 in its first) | fixed ca3fd1d — re-verify (run 42522959467: one quit on macOS 26, no crash report — the bug was intermittent, so repeat quits) |
| M-04 | S3 | Mac | An empty 28–32 pt band above the top bar: the hidden native title bar still takes its height, so the page loses height D-10 set out to win | 26, 15, 15-intel | fixed 09bab61 — re-verify (run 42522959467: web view top 0, full height) |
| M-05 | S3 | Mac | No app icon in the bundle (no `Assets.car`, no `.icns`, no `CFBundleIconName`) — Dock and Finder show the generic icon | bundle; Dock on 15 and 26 | fixed ca3fd1d — re-verify (Assets.car + CFBundleIconName in the bundle) |
| M-06 | S3 (perf) | Mac + Shared | Startup: warm first render 2.2–2.6 s, cold 4.2–4.7 s on Apple Silicon runners (7.7 s Intel); ~2 s of every launch is between WebView ready and Blazor's first render | 26, 15, 15-intel | improved 09bab61 (WebKit prewarm, ~260 ms); remaining ~1.1–1.4 s is WebKit's process launch on the VM — breakdown in docs/mac/BUILD-LOG.md session 6; re-measure |
| M-07 | S4 | Mac | Window opens at 1024×768 at the top-left corner, not 1100×720 as `App.CreateWindow` asks (and as Windows does) | 26, 15 | fixed e11011b (+ca3fd1d) — re-verify (1100×720 centred, clamped on a smaller screen) |
| M-08 | S3 | Shared (kit + reader.js) | Next/previous tab is ⌘Tab on Mac (reader.js `isPrimary` = ⌘ only) — macOS takes ⌘Tab for the app switcher, and ⌃Tab is explicitly rejected; Settings › Shortcuts shows "⌘Tab" | code; runtime in round 2 | shared patch sent to Foundation (docs/mac/foundation/M-08-M-09-M-10-mac-conventions.patch) |
| M-09 | S3 | Shared (Ui) + Mac | Immersive is labelled "F11" in the Ui (View rail, Settings › Shortcuts, ⌘K) — on a Mac F11 is Show Desktop; the Mac binding is ⌃⌘F, but that lives only in the (empty, M-01) menu | code; runtime in round 2 | shared patch sent to Foundation (same patch); Mac menu already ⌃⌘F (ca3fd1d) |
| M-10 | S4 | Shared (WindowButtons) | Green traffic light is announced "Exit full screen" while the window is merely zoomed (macOS zoom is not full screen) | 26 | shared patch sent to Foundation (same patch) |
| M-11 | S4 | Mac | No Settings… ⌘, in the Chuvadi menu (macOS convention; the Ui has Settings) | 26, 15, 15-intel | Mac side done ca3fd1d; appears once the shared global-commands patch lands (docs/mac/foundation/M-01-M-11-global-commands.patch) |
| M-12 | S4 | Mac | `DOTNET-*.txt` legal files ship with mode 0744 (executable bit from the NuGet cache) | bundle | fixed ca3fd1d — re-verify (bundle step checks every legal/*.txt is 644) |
| M-14 | S3 | Mac | .NET messages are resource keys, not text ("ObjectDisposed_Generic", "ObjectDisposed_ObjectName_Name") — the Release build strips system resource strings, so every `ex.Message` the Ui shows will be a key (same class as Linux Test B-17) | 26 | fixed 4cc889d — re-verify (run 42522959467: ObjectDisposedException message is text) |
| M-15 | S3 | Mac | ⌘O does nothing; the left bar's Open button (and the Home drop zone) do open the panel. ⌘K works, so the page gets keys — ⌘O alone is lost | 26, 15, 15-intel | with M-01: Open… ⌘O comes from the shared global-commands patch |

Known and already tracked (not re-filed): sample Home data on a fresh install — "Pinned aerb_submission.pdf", "IMCHRC /
PET-CT", Recent `patient_chart.pdf` …, "Watched folder ~/Documents/Chuvadi · 8 documents found" with an empty state folder
(D-94 H-12, Foundation combined patch, not in 7a65178).

---

## M-01 — The macOS menu bar has no Chuvadi commands (S2, Mac)
**Steps.** Install, launch, open a PDF (round 2: through ⌘O), wait, read the menu bar through Accessibility (each top menu
opened, so UIKit validates it): `macdrive menudump Chuvadi out.json --live`.
**Expected.** Handout › Platforms and `docs/mac/BUILD-LOG.md` §10/§12: File (Open…, Close, Save, Save as, Print, Show in
Finder, Copy file path, sessions), View (modes, view group, panels, Go to, ⌘K), Document (the Document ▾ items, Mark /
Protect / Arrange / Tools submenus), each with its ⌘ shortcut; no system Enter Full Screen (Immersive ⌃⌘F replaces it).
**Actual.** On all three runners, with a document open:
- **File: no items.** **Document: no items.** **Help: one separator.**
- **View:** "Find or do anything… ⌘K" and the system's **"Enter Full Screen"** — nothing else.
- Chuvadi / Edit / Window: the system items only.
So no command has a menu item or a menu shortcut (⌘O, ⌘P, ⌘S, ⇧⌘S, ⌘W, ⌘B, ⌘[ ⌘] …), the Document menu promised in the
handout is missing, and REAL-MAC-CHECKS §4 cannot pass.
Evidence: `evidence/M-01-menus-with-pdf-open-macos26.json`, `…-macos15.json` (the whole menu tree with titles,
shortcuts and enabled state).
**Notes for the fix.** Edit › Find and Format are gone, so `MacMenuBar.Build` did run — once, at launch, when
`IAppCommands` was still empty — and the rebuild never repopulated it (`Watch` → `SetNeedsRebuild`). The system re-adds
"Enter Full Screen" to a menu named View on its own (AppKit), so removing `UIMenuIdentifier.Fullscreen` is not enough.

## M-02 — Files handed over by macOS never open (S2, Mac)
**Steps.** (a) App not running: `open -a /Applications/Chuvadi.app five-pages.pdf` (= Finder Open With / double-click),
also through `NSWorkspace.open(_:withApplicationAt:)` in my probe. (b) App running: `open -a … second.pdf third.pdf`.
**Expected.** (a) The app starts and shows the PDF. (b) Both open as tabs in the running window (D-83, HANDOFF).
**Actual.** (a) The app starts on Home with no tab, every time (20 launches with a PDF on each runner; the page never appears in
40 s). (b) Still one process (good) but no new tab, no message. Same for `.docx`, `.xlsx`, `.md`, `.txt`, `.html`,
damaged and encrypted files (round 1 robustness set — those cases are re-run through the Open panel in round 2).
Screenshots: `screenshots/M-02-launched-with-pdf-shows-home-macos15.png`,
`screenshots/M-02-open-with-two-files-no-tabs-macos15.png`.
**Impact.** Open With, double-click on a file, drop on the Dock icon and the approved single-instance behaviour all
depend on this path. The Mac smoke run never opens a file, so CI could not see it.

## M-03 — Crash on quit on macOS 26 (S1, Mac)
**Steps.** macOS 26.7.2 runner: launch, wait for Home, quit (my harness uses `NSRunningApplication.terminate()`, the
same Apple Event as ⌘Q / Quit in the Dock).
**Expected.** Clean exit.
**Actual.** 25 crash reports `ChuvadiReader.Mac-2026-11-08-*.ips` in one run — one per quit. `EXC_CRASH (SIGABRT)`,
"abort() called"; the last-exception backtrace is a managed exception thrown (via `xamarin_process_managed_exception`)
inside **`-[Microsoft_Maui_Platform_PageViewController traitCollectionDidChange:]`**, reached from a CoreAnimation
commit run by **`-[NSPersistentUIManager _waitForPendingChangesToFinish]`** — i.e. while AppKit saves window state
during termination. A `UserNotificationCenter` window (the "quit unexpectedly" alert) was on screen afterwards.
Not seen on macOS 15 (arm64 or Intel): no crash reports there.
Round 3 confirmed it with **⌘Q** itself and captured the app's stderr: *Terminating app due to uncaught exception
'System.ObjectDisposedException' … IServiceProvider … at Microsoft.Maui.Platform.PageViewController.TraitCollectionDidChange*
— the MAUI service provider is already disposed when AppKit's state save triggers a trait-collection change. It is
intermittent (timing of the state save): 25 of 41 quits in round 1, 2 of 2 in one round-3 session, 0 of 2 in another.
Evidence: `evidence/M-03-crash-on-quit-macos26.txt` (crash-report backtrace), `evidence/M-03-quit-stdout-macos26.txt`
(the exception text). Suggested direction: stop the trait-change path touching services after termination starts (e.g.
handle `UIApplication.WillTerminate`/scene disconnect before MAUI disposes its provider) — the Mac chat to choose.
**Impact.** Every person on macOS 26 sees "Chuvadi quit unexpectedly" on every quit; anything saved on quit (tabs,
settings) is at risk.

## M-04 — Empty band above the top bar (S3, Mac)
**Steps.** Launch; capture the window; read the AX frames.
**Expected.** Handout / Mac decision: no native title bar, the Ui's 40 px top bar (traffic lights on the left) at the
window's top edge.
**Actual.** AX: window at y=31, web content starts at y=59 (macOS 26) / window y=25, content y=53 (macOS 15) — a
**28–32 pt strip** of plain background above the Ui top bar on every screen and theme. The title text and buttons are
hidden, but the title-bar area still reserves its height (content is laid out below it, not under it).
Screenshot: `screenshots/M-04-titlebar-band-dark-macos26.png` (dark theme makes the band obvious).
**Impact.** D-10's whole point is page height; this gives ~30 pt back to chrome, and the window looks unlike the handout's
Mac frame.

## M-05 — No app icon (S3, Mac)
**Steps.** Unzip the package; list `Contents/Resources`; read `Info.plist`.
**Expected.** The Chuvadi icon (Brand Assets) in the Dock, Finder, Launchpad, About and the "quit unexpectedly" alert.
**Seen:** the Dock shows a blank generic tile for Chuvadi (round 2/3 screen captures on macOS 15 and 26).
**Actual.** No `Assets.car`, no `.icns`, no `CFBundleIconName` / `CFBundleIconFile` in `Info.plist`. The csproj has
`<MauiIcon Include="Resources\AppIcon\appicon.png" />`, but for Mac Catalyst the icon is only compiled into the asset
catalogue when `Info.plist` names it (`XSAppIconAssets` = `Assets.xcassets/appicon.appiconset`), which this
`Info.plist` doesn't. Round 2 adds a Dock screenshot.

## M-06 — Startup (S3 perf, Mac + Shared)
Numbers and options in `RESULTS.md` › T2. In short: on Apple Silicon runners a warm launch reaches Blazor's first render
at **2.2–2.4 s** (app clock) / **2.4–2.6 s** (my external probe); WebView is ready at ~0.4 s, so **~1.9 s is Blazor
starting inside WKWebView**. Cold (`purge` before each launch): 4.2–4.7 s. Intel: 7.7 s cold, 2.4 s warm. For comparison
the same runner class shows the Windows app's window at 0.6 s (different metric — see RESULTS).

## M-07 — Opening window size and place (S4, Mac)
AX on every runner: `AXWindow @0,25 1024x768` (macOS 15) / `@0,31 1024x768` (26) on a 1920×1080 display.
`App.CreateWindow` sets Width 1100, Height 720 ("same opening size as the Windows host"). Catalyst ignores MAUI's
`Window.Width/Height`; the scene's size restrictions / the NSWindow frame need setting from the host.

## M-08 — Next/previous tab is ⌘Tab on a Mac (S3, Shared)
`src/ChuvadiReader.Ui/wwwroot/js/reader.js:9-12` `isPrimary()` on macOS = `metaKey && !ctrlKey`; line 117 cycles tabs on
primary + Tab. macOS consumes ⌘Tab (app switcher) before any app sees it, and ⌃Tab (the Mac convention — Safari, Finder,
Xcode) fails `isPrimary`. Settings › Shortcuts formats "Ctrl Tab" with `MacKeyLabels` → "⌘Tab". Result: no keyboard way
to switch tabs on a Mac. Suggested fix (Shared): on macOS accept ⌃Tab / ⌃⇧Tab for tab cycling and label it "⌃Tab".
Round 2 presses ⌃Tab with two tabs open to confirm on screen.

## M-09 — Immersive labelled F11 on a Mac (S3, Shared + Mac)
`Reader.razor:1149` `RailButton … Keys="F11"`, `ShortcutsSection.razor:77`, `Reader.Shell.cs:464` keys "F11" — shown
as-is on Mac. F11 on a Mac keyboard is Show Desktop (or a media key). The Mac menu was to give Immersive ⌃⌘F, but M-01
leaves no menu item. Suggested fix: `MacKeyLabels.Format("F11")` → "⌃⌘F" (kit) plus a working ⌃⌘F binding (M-01).
Round 2 presses ⌃⌘F and F11 with a document open.

## M-10 — "Exit full screen" on a zoomed window (S4, Shared)
`Components/Platform/WindowButtons.razor`: the green button's `aria-label` becomes "Exit full screen" (and its icon
"restore") when `IsMaximized` — on a Mac that is Zoom, not full screen. Seen in AX after pressing Zoom on macOS 26.
Suggested: "Zoom" in both states on macOS (the native green button's hover glyphs, not a restore icon).

## M-11 — No Settings… ⌘, (S4, Mac)
The Chuvadi menu has About, Services, Hide, Quit only. Every Mac app has Settings… ⌘, there; Chuvadi has a Settings
page. Natural to add with M-01.

## M-12 — Executable bit on two legal files (S4, Mac)
`Contents/Resources/legal/DOTNET-MACCATALYST-LICENSE.txt` and `DOTNET-RUNTIME-THIRD-PARTY-NOTICES.txt` are `-rwxr--r--`
(copied with the NuGet cache's mode); the other three are `-rw-r--r--`. Harmless, but untidy in a notarised bundle.

## M-14 — .NET messages are resource keys (S3, Mac)
Round 3 stderr at quit: *'System.ObjectDisposedException', reason: 'ObjectDisposed_Generic ObjectDisposed_ObjectName_Name,
IServiceProvider'* — resource keys instead of "Cannot access a disposed object…". The Release Mac Catalyst build strips
`System.Private.CoreLib` resource strings (`UseSystemResourceKeys`, on by default for trimmed Apple builds). The Ui
shows `ex.Message` in error banners and toasts, so on Mac a person sees keys like `IO_FileNotFound_FileName` instead of a
sentence. Linux Test filed the same class as B-17. Fix: `<UseSystemResourceKeys>false</UseSystemResourceKeys>` in the
Mac csproj (costs some bundle size) — or map known exceptions to Ui text (Shared). Re-verify once a document error can be
triggered (needs M-02/M-15 path working).

## M-15 — ⌘O does nothing (S3, Mac)
Launch, wait for Home, ⌘O: no panel in 10 tries on every runner (round 3 T4.0; window list shows no second window).
Pressing the left bar's "Open ⌘O" button opens "Open a document" at once (`screenshots/M-15-open-button-panel-macos26.png`).
⌘K at the same moment opens the command bar, so the page receives ⌘ keys — ⌘O specifically is swallowed, most likely by
the system's File › Open key equivalent that M-01's empty File menu leaves without an action. Likely fixed with M-01; to
be re-verified separately.

## M-16 — Opening a document kills the Ui (S1, Mac)
**Steps.** Launch (fresh state). Press the left bar's **Open ⌘O** → the "Open a document" panel → ⇧⌘G → `/tmp/fixtures/five-pages.pdf` → Open.
(Same with `annotated.pdf`, `noprint.pdf`, and in round 3 with docx/xlsx/md/txt/html.)
**Expected.** The Reader shows page 1 (Windows does).
**Actual.** The tab "five-pages…" appears in the top bar and Home gains "Pick up where you left off · five-p… Page 1 of 5 ·
Reading 1m" — so the document was opened and recorded — but the view stays on Home and a **red strip** appears at the
bottom edge: Blazor's `#blazor-error-ui` ("An error occurred. Reload"), mostly **covered by the status bar** (round 2
showed the full bar on a screen where the status bar was gone). From then on nothing responds (Settings, modes, ⌘K
commands do nothing) until the app is relaunched.
Screenshot: `screenshots/M-16-doc-opens-as-tab-reader-never-shows-macos15.png` (four separate opens).
**Not available from outside:** the exception text — the Release app has no logging provider and Blazor swallows the
detail; my diagnostic build (a module initializer printing first-chance exceptions) produced no output under Mono AOT.
The Mac chat can reproduce in two clicks on any Mac runner; a `ILoggerProvider` writing to `~/Library/Logs/Chuvadi`
would make the next such error visible (suggest keeping one in the product, for Arun's and the friend's Mac too).
**Impact.** Viewing — the core of the app — does not work on Mac. Every T4 function case waits on this.

Secondary, Shared: `#blazor-error-ui` sits under the status bar, so a fatal Ui error shows as a 3-px red line with no
text. Filed here as part of M-16 for the Foundation; not yet checked whether Windows stacks it the same way.
