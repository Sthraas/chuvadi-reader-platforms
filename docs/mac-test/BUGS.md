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
| M-16 | S1 | Mac | Opening any document through the Open panel adds the tab and the "Pick up where you left off" card, then the Ui dies: Blazor's "An error occurred" bar (hidden behind the status bar — only a red line shows) and the Reader never renders; every later click does nothing until relaunch | 15 (26, 15-intel in run 42517758923) | **verified fixed** — re-verified on c6d7705 (runs 42534074875, 42538220489): Open panel → Reader on all three runners; PDF, docx, xlsx, md, txt, html, Tamil file name; 15 tabs opened and restored |
| M-17 | S1 | Mac? | Submitting a PDF password killed the Ui ("An error occurred", blank page) | 26 on c6d7705 | **verified fixed on 00a5975**, and still fine on **83207af** (run 42673993820, all runners): right password first, wrong → message → right, owner-only. The c6d7705 repro most likely submitted an empty password (value set through Accessibility) |
| M-18 | S2 (accessibility) | Mac + Apple | **Re-scoped 10 Nov:** on macOS 26 an **Accessibility press** (AXPress — what VoiceOver's VO-Space and my harness use) on Settings › Appearance crashes WebKit's web process inside Apple's `AccessibilityPlatformTranslation` (`-[AXPMacPlatformElement _synthesizeMouseClick:]` → Swift array index on an empty array → SIGTRAP). The WebView then reloads the Ui and Blazor dies ("An error occurred"). **A mouse click on the same element works** | 26 only | open — run 42686357055: mouse click → Appearance fine (macOS 26, from Home and Reader); AXPress → WebContent crash report each time. My earlier S1 "Settings is broken" was produced by the test method; a mouse user is not affected. What is left for the app: recover from a web-process crash with a clean reload and log it (M-19). Options to the coordinator in the session status |
| M-19 | S2 | Mac | The new error log (D-132) stays empty when the Ui fails: no `chuvadi.log` in 47 saved log folders, while M-17/M-18 fired | 26 | fixed further 4a4b419 — re-verify: a second load of the Ui page (WebKit's content process ended) is now logged as the error, ahead of the follow-on DisposeAsync error; page errors since 5f34138 |
| M-20 | S3 | Shared/Library? | The 8 MB one-page vector stand-in never draws in 20 s ("page 1" placeholder, RSS 409 MB); under memory pressure it stays on "Opening…" | 26 | open — 83207af: under memory pressure the heavy file now opens (T5.5 passes, RSS 437 MB), but the page still never draws in 20 s (RSS 420 MB). **D-148:** Windows comparison on Arun's list with B-27 (real CAD PDF) |
| M-22 | S2 | Mac | Opening the macOS print panel makes macOS ask "Allow 'Chuvadi' to find devices on local networks?" (generic text — no `NSLocalNetworkUsageDescription`) | 26 | fixed 5f34138 — re-verify: NSLocalNetworkUsageDescription names printers only (bundle step checks it); privacy-notice line A2b sent to Foundation (docs/mac/foundation/D-148-privacy-notice-mac-printers.patch) |
| M-21 | S3 | Mac | Esc doesn't leave Immersive on Mac (⌃⌘F enters; the "exit" button leaves) | 26, 15, 15-intel | not reproduced on b41f25c+: real ⌃⌘F enters Immersive, real Esc reaches the page (keys=[Escape]) and leaves it (Mac chat smoke, HID key events) — re-verify |
| M-01 | S2 | Mac | macOS menu bar has no Chuvadi commands: File, Document and Help are empty; View has only ⌘K and the system's Enter Full Screen | 26, 15, 15-intel | **menus fixed** (00a5975, still on 83207af: File 6 · View 33 · Document 11 on all runners). Open for Open… ⌘O (M-15), Settings… ⌘, (M-11, Mac chat still investigating) and the empty Help menu |
| M-02 | S2 | Mac | Files handed over by macOS never open — at launch (Open With / double-click) and while running (`open -a`, Dock); single instance can't work | 26, 15, 15-intel | **verified fixed** — re-verified on c6d7705 (runs 42534074875, 42538220489): launch with a PDF shows page 1 (22/22 per runner); `open -a` two files into the running app → 3 tabs in order, one process, all runners |
| M-03 | S1 | Mac | Crash on quit on macOS 26: `ObjectDisposedException` (IServiceProvider) in MAUI's `PageViewController.TraitCollectionDidChange` while AppKit saves window state → SIGABRT, "quit unexpectedly" | 26 (intermittent: 25/41 quits in round 1, 2/2 in round 3's second session, 0/2 in its first) | second form fixed d390abc — re-verify with repeated quits on 26. Quit detached every window incl. UIKit's keyboard window (UITextEffectsWindow/UIInputWindowController) — the backtrace; now only MAUI's windows (run 42682869087 on 884b529, all 38 checks green: no crash report over three quits, two after typing) |
| M-04 | S3 | Mac | An empty 28–32 pt band above the top bar: the hidden native title bar still takes its height, so the page loses height D-10 set out to win | 26, 15, 15-intel | **verified fixed** — re-verified on c6d7705 (runs 42534074875, 42538220489): web content at the window's top edge, traffic lights in the Ui bar, no band |
| M-05 | S3 | Mac | No app icon in the bundle (no `Assets.car`, no `.icns`, no `CFBundleIconName`) — Dock and Finder show the generic icon | bundle; Dock on 15 and 26 | **verified fixed** — bundle has `Assets.car`, `appicon.icns`, `CFBundleIconName`; the Dock shows the Chuvadi icon |
| M-06 | S3 (perf) | Mac + Shared | Startup: warm first render 2.2–2.6 s, cold 4.2–4.7 s on Apple Silicon runners (7.7 s Intel); ~2 s of every launch is between WebView ready and Blazor's first render | 26, 15, 15-intel | **still open** — 83207af (pages off the Ui thread), warm first render median: macOS 26 **2 345** ms, 15 **2 114** ms (Intel: no numbers, its evidence upload failed); cold 7 641 / 3 315; Windows same run 1 611. macOS 26 cold is much slower than on 00a5975 (4 559) while 15 is faster (5 702 → 3 315) — the two moved in opposite directions on the same build, so I read it as runner variance for now and will watch macOS 26 cold on the next build. Numbers in RESULTS |
| M-07 | S4 | Mac | Window opens at 1024×768 at the top-left corner, not 1100×720 as `App.CreateWindow` asks (and as Windows does) | 26, 15 | **verified fixed** — 1100×720 centred (410,91 on 1920×1080) |
| M-08 | S3 | Shared (kit + reader.js) | Next/previous tab is ⌘Tab on Mac (reader.js `isPrimary` = ⌘ only) — macOS takes ⌘Tab for the app switcher, and ⌃Tab is explicitly rejected; Settings › Shortcuts shows "⌘Tab" | code; runtime in round 2 | open — waits on the shared patch (Foundation); Ui still shows the old labels |
| M-09 | S3 | Shared (Ui) + Mac | Immersive is labelled "F11" in the Ui (View rail, Settings › Shortcuts, ⌘K) — on a Mac F11 is Show Desktop; the Mac binding is ⌃⌘F, but that lives only in the (empty, M-01) menu | code; runtime in round 2 | open — waits on the shared patch; the View rail still says "Immersive (full screen) F11" (AX, macOS 26) |
| M-10 | S4 | Shared (WindowButtons) | Green traffic light is announced "Exit full screen" while the window is merely zoomed (macOS zoom is not full screen) | 26 | open — waits on the shared patch |
| M-11 | S4 | Mac | No Settings… ⌘, in the Chuvadi menu (macOS convention; the Ui has Settings) | 26, 15, 15-intel | fixed a7c46be — re-verify. go.settings also sat under View › Go to and UIKit dropped the app-menu copy as a duplicate; now only in the Chuvadi menu (run 42682869087 on 884b529, all 38 checks green) |
| M-12 | S4 | Mac | `DOTNET-*.txt` legal files ship with mode 0744 (executable bit from the NuGet cache) | bundle | **verified fixed** — all five `legal/*.txt` are 0644 |
| M-14 | S3 | Mac | .NET messages are resource keys, not text ("ObjectDisposed_Generic", "ObjectDisposed_ObjectName_Name") — the Release build strips system resource strings, so every `ex.Message` the Ui shows will be a key (same class as Linux Test B-17) | 26 | fixed per the Mac chat (4cc889d); my runs have not yet surfaced a .NET message to check — kept open until one does |
| M-15 | S3 | Mac | ⌘O does nothing; the left bar's Open button (and the Home drop zone) do open the panel. ⌘K works, so the page gets keys — ⌘O alone is lost | 26, 15, 15-intel | open — waits on the shared patch; ⌘O still opens nothing (all runners) |

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

---

## Re-verification on c6d7705 (9 Nov) — what changed
Runs 42534074875 (full, with 10-run timing sets) and 42538220489 (function cases), both on all three runners.

### M-03 — quit crash, second form (S1, Mac)
The managed `ObjectDisposedException` is gone. What is left on macOS 26 is an Objective-C exception at quit:
`-[UIKeyboardSceneDelegate inputViews]` → `doesNotRecognizeSelector:`, thrown while a `UIInputWindowController`
deallocates in a CoreAnimation after-commit block, driven by `NSApplication terminate:` (NSPersistentUIManager
`discardAllPersistentStateAndClose`) or the quit Apple Event's `_shouldTerminate` loop. 17 reports over two runs, every
one at quit; none on macOS 15. Backtrace: `evidence/M-03-c6d7705-quit-crash-macos26.txt`. The keyboard scene delegate
UIKit expects is presumably the `SceneDelegate` added for M-02 (it doesn't answer `inputViews`) — the Mac chat to judge.

### M-17 — PDF password submit kills the Ui (S1)
Open `aes256.pdf` (user password `user1`) through the Open panel → the prompt "This PDF is password-protected" appears
(✅). Focus the Password field, enter `wrong` and Return → blank page + "An error occurred". Relaunch, reopen, enter
`user1` and Return → the same. Same for AES-128 and RC4. Screenshots: `screenshots/M-17-password-submit-ui-error-macos26.png`
(wrong left, right right). The value is set through Accessibility, then Return — the same events a person's typing ends
with. Not yet run on 15 (password cases are in the full suite only).

**Re-test on 00a5975 — verified fixed.** The harness now presses "show", types with real key codes and reads the value
back from the Accessibility tree before pressing Return (`value="user1"` confirmed on every runner). Run 42661249171:

| File | macOS 26 | 15 | 15-Intel |
|---|---|---|---|
| AES-256 / AES-128 / RC4, right password first | page 1 ✅ | page 1 ✅ | page 1 ✅ |
| AES-256, `wrong` then `user1` | message, then page 1 ✅ | ✅ | ✅ |
| Empty submit (run 42656778614) | "That password doesn't open this file." ✅ | ✅ | ✅ |
| Owner-password only | opens, no prompt ✅ | ✅ | ✅ |

No "An error occurred" anywhere. Honest correction: on c6d7705 I set the field through Accessibility, which WebKit does
not pass to Blazor as input, so what I submitted was most likely an empty password — the crash was real, but on the
empty-submit path rather than for every password. Screenshots: `screenshots/M-17-00a5975-wrong-password-macos26.png`,
`screenshots/M-17-00a5975-right-password-page-macos26.png`.

### M-18 — Settings › Appearance on macOS 26 (S1)
First seen on c6d7705 as "Settings after the Reader". **Narrowed on 00a5975** (run 42658809276, M-18 case: six paths,
each from a fresh launch, `ui_error()` after every step):

| Path | macOS 26 | 15 | 15-Intel |
|---|---|---|---|
| PDF → Mark → Read → Library → Settings | ok | ok | ok |
| PDF → Settings | ok | ok | ok |
| PDF → Settings → **Appearance** | **"An error occurred"** | ok | ok |
| PDF → Document ▾ → Settings | ok | ok | ok |
| PDF → ⌘K → Settings | ok | ok | ok |
| Home (no document) → Settings → **Appearance** | **"An error occurred"** | ok | ok |

So the trigger is the Appearance section on macOS 26, not the Reader. In the full run (42646315081) every theme's
Settings › Appearance shot is the blank page with the red bar, and so are all later sections (About, Licences,
Shortcuts …) because the Ui is already dead. Screenshots: `screenshots/M-18-00a5975-home-settings-appearance-macos26.png`,
`screenshots/M-18-00a5975-reader-settings-appearance-dark-macos26.png`. Guess for the Mac chat: something Appearance
reads that only macOS 26 answers differently (system appearance / accent colour / font list). No log line (M-19).
Consequence: T1.10 (Licences screen) and T3.2's Settings shots are unverified on macOS 26 until this is fixed.

**Re-scoped on 83207af (10 Nov).** Run 42676250705 kept the WebKit log and found two WebContent crash reports from the
moment Appearance was pressed (`evidence/M-18-83207af-WebContent-crash-AXPress-macos26.ips`): `EXC_BREAKPOINT` in
`libswiftCore` `_assertionFailure`. The array read is in `__SwiftNativeNSArrayWithContiguousStorage.objectAtSubscript`,
called by `-[AXPMacPlatformElement _synthesizeMouseClick:]` ← `accessibilityPerformPress` ← `NSAccessibilityPerformEntryPointBOOL`.
In other words, Apple's macOS 26 accessibility layer turns my AXPress into a synthetic click and indexes an empty
array. Run 42686357055 then added paths that press the same element with a **real mouse click**. Those paths are fine on
macOS 26, from Home and from the Reader (`screenshots/M-18-83207af-appearance-mouse-click-ok-macos26.png`), while the
AXPress paths crash again. macOS 15 / 15-Intel: no crash either way.

So this is not "Settings is broken for everyone" (my earlier S1). It is: on macOS 26, a VoiceOver or other
Accessibility press on that control kills the web process, and the app is left dead instead of recovering. I've
changed the harness to click Settings sections with the mouse, so the Settings, About and Licences screens can be
checked on macOS 26 again.

### M-19 — error log empty when it matters (S2)
My harness now keeps `~/Library/Logs/Chuvadi` before each case. Across 47 cases (M-17 and M-18 included) the folder
only ever held `startup.log` — never `chuvadi.log`. So the Blazor renderer's unhandled exceptions (what "An error
occurred" reports) don't reach the D-132 logger; those are exactly the errors Arun and the friend would need to send.

### M-20 — heavy vector page (S3)
`heavy-vector.pdf` (A1, ~8 MB uncompressed content stream of 200 k line segments — my stand-in for the 7.9 MB CAD PDF):
after 20 s the page is still the white "page 1" placeholder; RSS 409 MB. Under `memory_pressure -l critical` the tab
stays on "Opening heavy-vector.pdf…". Likely the shared renderer, not the Mac host — needs the same file on Windows.

### M-21 — Esc and Immersive (S3)
⌃⌘F enters Immersive on every runner (✅, chrome hidden, "exit" button). Esc does not leave it; the "exit" button does.
The plan expected Esc to leave (as F11 mode does on Windows?) — please confirm the Windows behaviour; if Windows leaves
on Esc this is a Mac/Shared bug, otherwise close it.

### Not bugs (recorded)
- Immersive is an in-app mode everywhere (no window full screen); the macOS green button zooms. Consistent with the
  6 Nov decision.
- Excel cells show raw values (`1234.5` for ₹1,234.50, `46334` for the date) — the shared Sheets display-text work
  (SHEETS-FMT) isn't released; same in every locale.

### M-22 — local-network permission prompt from the print panel (S2, Mac)
**Steps.** macOS 26 runner, fresh install. Open `annotated.pdf`, Print (rail or ⌘P) → "Print 2 pages" → the macOS print
panel opens (✅, with preview).
**Actual.** A system alert appears over the panel at once: **"Allow 'Chuvadi' to find devices on local networks? This
will allow the app to discover, connect to, and collect data from devices on your networks."** The text is macOS's
generic one because `Info.plist` has no `NSLocalNetworkUsageDescription`. It comes from the print panel browsing for
printers (Bonjour) inside the app's process. Screenshot: `screenshots/M-22-print-local-network-prompt-macos26.png`
(top: the alert over the Save-as-PDF sheet; bottom: still there a step later).
**Why it matters.** The status bar says "offline · on this device" and the promise is "nothing leaves this device"; a
person asked to let Chuvadi "collect data from devices on your networks" will reasonably refuse or distrust it — and if
they refuse, network printers may not appear in the panel.
**Options for the Mac chat / coordinator (my view, not a decision):**
| Option | Pros | Cons |
|---|---|---|
| A. Add `NSLocalNetworkUsageDescription` ("Chuvadi looks for printers on your network only when you print. Nothing is sent anywhere.") | Honest prompt, printers keep working, tiny change | The prompt still appears once |
| B. Same as A, plus a line in the privacy notice about printer discovery | Legal texts match what the person sees | Lawyer's text to update (DRAFT anyway) |
| C. Try to keep printing out of process so the app itself never browses | No prompt at all | Not under the app's control with UIKit printing; research needed |
**Recommendation: B** (A + the privacy-notice line), and add it to REAL-MAC-CHECKS: refuse the prompt on a real Mac and
confirm a USB / saved printer still prints.
