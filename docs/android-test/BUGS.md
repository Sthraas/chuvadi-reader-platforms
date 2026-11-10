# Android Test — bugs

Severity: **S1** blocks release or loses data · **S2** feature broken or wrong · **S3** visible defect with a workaround · **S4** cosmetic / hygiene.
Owner: **Android** (host) · **Mobile UI** (look) · **Foundation** (shared Ui/Core, legal drafts) · **Library** (Arun) · **Coordinator** (decision).
Status: open · fixed (commit) · verified (run).

Composition under test (round 1): Foundation `839d39d` + Mobile UI `95b9d79` + Android `7ec8017`, built from clean in
run [42518447149](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42518447149) (artifact `audit`).

---

## AT-03 · S1 · Foundation (+ Android CI) · **verified** (Foundation f88f9ef + Mobile UI d34d542 + Android d134c74, run 42739175820: as-built Release 0 crashes in 3 launches on phone API 35, phone API 36, tablet API 36) — The Release app crashes at every launch (trimmed constructor)
**Steps:** install the Release `.apk` from the build above (the same build as the Play `.aab`) on any emulator; tap the icon,
or Open with a PDF.
**Expected:** the app starts.
**Actual:** it dies in `MainActivity.OnCreate` before the first frame, every time (15 of 15 crash entries in `dumpsys dropbox`
on phone API 35 and tablet API 35; `am start -W` never reports a TotalTime):
```
FATAL EXCEPTION: main  Process: in.chuvadi.reader
[System.InvalidOperationException]: NoConstructorMatch, ChuvadiReader.Platform.NoAppInstance
  at Microsoft.Extensions.DependencyInjection.ServiceLookup.CallSiteFactory.CreateConstructorCallSite
  … ServiceProvider.GetService … MauiContext+WrappedServiceProvider.GetService
  at ChuvadiReader.Android.MainActivity.Service / Deliver / OnCreate
```
Evidence: run 42518447149, artifacts `results-phone-api35/…/dropbox.txt`, `…/logcat.txt` (same on tablet).
**Cause:** `ChuvadiReader.Platform.csproj` sets `IsTrimmable` / `IsAotCompatible`, so the Android Release build (MAUI's
partial trimming, `AndroidLinkMode=SdkOnly`) trims that assembly. The host kit registers the seam defaults
(`NoAppInstance`, `NoopUiScale`, `NoExternalLinks`, `NoopWindowControls`, `NoopPrintService`, `NoHostNotices`, `NoDroppedFiles`,
`NoFileWriteBack`, `NoAppLifecycle`, `NoFileManager`, …) from `(Type Service, Type Impl)` tuples in
`ChuvadiReader.Hosting/ChuvadiReaderServices.cs`, which carry no `[DynamicallyAccessedMembers]`; the trimmer can't see that their
constructors are used and removes them. No trim warning appears because Hosting itself isn't marked trimmable, so ILLink doesn't
analyse it. `UseSystemResourceKeys` hides the full message ("A suitable constructor … could not be located").
**Why nobody saw it:** the Android workflow installs only the **Debug** x64 `.apk` on the emulators (no trimming there);
Release was built and uploaded but never run.
**Fix options (for the coordinator):**
- (a) **Annotate the registration tables** — e.g. a small `readonly record struct Seam(Type Service, [DynamicallyAccessedMembers(PublicConstructors)] Type Impl)`
  or `DynamicDependency` on the table — in Hosting. *Pros:* correct for every trimmed host (Android now, Mac Catalyst Release
  too, any future AOT); keeps Foundation's non-generic registrations, so no desktop startup cost. *Cons:* shared-code edit (Foundation
  combined patch); needs the trim analyser turned on for Hosting to prove nothing else is missed.
- (b) **Drop `IsTrimmable`/`IsAotCompatible` from ChuvadiReader.Platform.** *Pros:* one-line, no runtime change. *Cons:* hides the
  problem rather than fixing it; any other trimmable assembly with the same pattern stays exposed.
- (c) **Android host roots the assembly** (`<TrimmerRootAssembly Include="ChuvadiReader.Platform" />`). *Pros:* host-only, today.
  *Cons:* Mac Catalyst Release likely has the same crash and needs its own copy; papers over the shared cause.
**Recommendation:** (a), with the trim analyser enabled on Hosting/Platform (`EnableTrimAnalyzer`) so CI fails on the next
case, **plus** the Android workflow running the Release `.apk` on at least one emulator per round. **The Mac Test chat should
check the Mac Catalyst Release build for the same crash.** Until (a) lands, this chat tests a Release build with (c) applied in
the test composition only, marked as such, so startup and design results reflect the shipping configuration.

## AT-01 · S2 · Android + Foundation · **verified** R6 run 42751641303 (Foundation 846706e, Release): About › Licences › Third-party notices names AndroidX, Material, Kotlin, kotlinx, Glide, Tink, Gson, JetBrains, and all 29 binding assemblies in the Release app; ".NET runtime" tab present (phone and tablet) — Third-party notices leave out AndroidX, Material Components and Kotlin, which ship in the app
**Steps:** build Release; list `obj/Release/net10.0-android/android-arm64/linked/*.dll` and the dex (`audit/assemblies.txt`,
`audit/apk-contents.txt`); open About › Licences.
**Expected:** every third-party component that ships has its notice (Apache-2.0 §4(d) requires it), and the Play data-safety
basis describes the package accurately.
**Actual:** the Release app ships 29 binding assemblies with their Java code in `classes.dex` / `classes2.dex` (15.6 MB):
`Xamarin.AndroidX.*` (Activity, AppCompat, Core, Fragment, Lifecycle, Navigation, RecyclerView, ViewPager2, SwipeRefreshLayout,
CoordinatorLayout, DrawerLayout, CardView, …), `Xamarin.Google.Android.Material`, `Xamarin.Kotlin.StdLib`,
`Xamarin.KotlinX.Coroutines.Core.Jvm`, `Xamarin.KotlinX.Serialization.Core.Jvm`. They come in as MAUI's own dependencies. The dex listing (R1c › audit › dex-packages.txt) adds Java libraries
with no .NET binding of their own: **Google Tink** (`com/google/crypto`, 2,152 classes, via AndroidX Security for Essentials'
SecureStorage), **Glide** (`com/bumptech/glide`, 655 classes, MAUI's image loader), **Gson** (`com/google/gson`), AndroidX
ConstraintLayout, Window, Emoji2, Browser (custom tabs), ProfileInstaller, JetBrains annotations — about 11,000 third-party
classes in all.
Neither `legal/THIRD-PARTY-NOTICES.txt` nor the two bundled .NET notices (`assets/notices/dotnet-runtime.txt`,
`dotnet-android.txt`) mention AndroidX, Material Components, Kotlin or kotlinx (checked against dotnet/android's
THIRD-PARTY-NOTICES.TXT). `legal/store/PLAY-DATA-SAFETY.md` says "The only libraries are Chuvadi's own and Microsoft's .NET/MAUI".
**Fix (proposal):** the Android host adds a third notices asset generated at build time from the resolved `Xamarin.*` packages
(each package's licence + the Google/JetBrains Apache-2.0 NOTICE), shown on the ".NET runtime" tab; Foundation corrects the
data-safety basis line ("…and Google's AndroidX/Material and JetBrains' Kotlin libraries that MAUI depends on; none collects data").
**For the coordinator (rule 3):** these are Google and JetBrains code that MAUI pulls in, not Microsoft's. I read them as
"ships with MAUI" (allowed); please confirm.

## AT-02 · S4 · Android · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): no Essentials activities/receivers/provider in the manifest — Unused MAUI Essentials components are declared in the shipped manifest
**Evidence:** `audit/manifest-xmltree.txt`: `WebAuthenticatorIntermediateActivity`, `IntermediateActivity`,
`microsoft.maui.essentials.fileProvider`, and three broadcast receivers (Essentials Connectivity, Battery, Energy Saver). All
`exported=false`, so not reachable from other apps; the app uses none of them (it has its own `SharedFileProvider`).
**Expected:** only what the app uses (smaller attack surface; nothing in a Play review that looks like connectivity monitoring).
**Fix (proposal):** `tools:node="remove"` entries in the host's `AndroidManifest.xml`. Low risk; verify Share and Open still work.

## AT-04 · S3 · Mobile UI · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): desk header = name + `···` (phone and tablet) — Desk header on touch still shows the desktop action row (12f, 12i; D-114)
**Steps:** phone or tablet, open a PDF, Arrange.
**Expected (12f / 12i, D-114):** desk header = name, page count, `···`; the desk actions live in the `···` menu on touch.
**Actual:** header shows the colour swatch, name, a "BM" chip, page count, ← → arrows, duplicate, `···` and delete — the desktop
row. The arrows/duplicate/delete are ~20 dp targets and the swatch 16 dp (see AT-06).
**Evidence:** `screenshots/r1/12f-vs-app.png`, `12i-vs-app.png` (API 36, R1, Debug build of the same composition).
Foundation 839d39d's message says H-16 (desk actions in the menu on touch) landed, so either it covers only the desk toolbar or it
isn't keyed on the touch form factor here.

## AT-05 · S3 · Mobile UI · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): `Document actions` in the tablet portrait top bar — Tablet portrait top bar has no `Document ▾` menu (12f)
**Expected (12f):** tabs · pager · `Document ▾` · search, as in landscape.
**Actual:** tablet portrait shows tabs · pager · search; `Document ▾` is gone, so Properties / Export / Compress / Merge / Split
have no entry point from the top bar in portrait. **Evidence:** `screenshots/r1/12f-vs-app.png`.

## AT-06 · S3 · Mobile UI · **still open** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): same sizes (phone avatar 32, pager 36 high, sheet handle, library search 27.6, tag chips 32; tablet top bar 36–40, brand 22.5) — Touch targets under 44 dp (handout: 48 dp on tablet and phone)
Measured in the page (CSS px = dp), every visible control, all screens, R1 API 36 (`design/*.layout.json`):
| Form | Control | Size (dp) |
|---|---|---|
| Phone | Account avatar (Home app bar) `.ph-av` | 32 × 32 |
| Phone | Pager chip `.ph-pager` ("1 / 12", "Bind all") | 56 × 36 |
| Phone | Sheet handle "Close" `.ph-handle` | 64 × 17–20 (landscape 64 × 9) |
| Phone | Library search button `.libp-go` / tag chips `.tagchip` | 71 × 28 / ~70 × 32 |
| Phone + tablet | Desk swatch `.desk-swatch`, desk ← → / duplicate / delete | 16 × 16, ~20 × 20 |
| Tablet | Top bar: previous/next page `.tb-pg-btn` | 36 × 36 |
| Tablet | Top bar: page box `.tb-pg-box` | 34 wide |
| Tablet | Top bar: Find/command `.tb-cmd` | 40 × 40 |
| Tablet | Brand / Home `.tb-brand` | 83 × 22.5 |
**Expected:** ≥ 44 dp everywhere (Android's own minimum is 48 dp; the handout asks 48 on tablet rails and phone bars). A larger
hit area (padding / `::after` inset) keeps the drawn size.

## AT-07 · S4 · Android · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): no control labelled with a /data/ path on any screen — to verify — Tabs and Home's recent cards/rows label themselves with the internal working path
The tablet tab's `title`, and the accessible name/`title` of every Home "Pick up where you left off" card (`.rcard`) and Recent
row (`.rrow`) on phone and tablet, is the working copy path, e.g. `/data/user/0/in.chuvadi.reader/cache/work/open/1429e6d5d0cd4…`
(`design/*-home.layout.json`). TalkBack reads that path aloud. Android shows `title` on long-press/hover with a mouse. **Expected:** the document's name
(or the original location the person chose), never the app's private cache path.

## AT-08 · S3 · Android · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): Night paper set by a real Settings tap → dark status and navigation bars with light icons, phone and tablet — Status and navigation bar areas stay cream in the Night, Palm and Indigo themes
**Steps:** phone, Settings › theme Night paper (or Palm leaf / Indigo ink); look at the top (clock, signal) and the bottom
(gesture bar).
**Expected:** the system-bar areas take the theme's paper colour (as the first-paint background in `index.html` already does per
theme), with light icons on Night paper; edge-to-edge as on Windows' title bar.
**Actual:** both strips stay the cream `#F2EAD6` in every theme, so Night paper shows a cream band above a dark app bar and
below a dark bottom bar; Palm and Indigo show a mismatched band.
**Evidence:** `screenshots/r1/themes-phone-home-mark.png` (columns: Cream, Night, Palm, Indigo, High contrast).
**Fix (proposal):** `SystemBars` follows the theme (theme-changed signal → window background / `isAppearanceLightStatusBars`),
or the WebView draws under the bars and pads with `env(safe-area-inset-*)`.

## AT-09 · S3 · Mobile UI · **still open on tablet** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): 1/1 but the page box stays on 2; phone passes — Find reports the match but doesn't bring it into view
**Steps:** tablet (API 36), open `doc-12p.pdf` (12 pages; the word "zephyrine" appears once, near the foot of page 3), Find,
type `zephyrine`.
**Expected:** 1/1, and the view moves so the highlighted match is on screen (page 3, foot).
**Actual:** 1/1, but the view shows the foot of page 2 and the top of page 3; the match stays off screen and the page box still
says 2. **Evidence:** R2 run 42533545934 › results-tablet-api36 › function/04-find.png (`screenshots/r1/r2-find-print.png`, left).
Re-checked next round on phone too (phone typing in R2 was cut short by the test, see notes).

## AT-10 · S2 · Foundation (shared Ui) · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): Find box and Library search keep every key of a burst, phone and tablet (Mark text box untestable until AT-15) — The Find box drops typed characters; a plain field doesn't
**Steps:** API 36, open a PDF, Find, type on the on-screen keyboard path (`adb shell input text`, i.e. real key events through the IME).
**Expected:** every character arrives, as in any text field.
**Actual (R3, run 42537723474):**
| Input | Find box got | Plain `<input>` added to the same page, same input |
|---|---|---|
| burst "burstwordtest" — phone | `burtwordt` | `burstwordtest` |
| burst "burstwordtest" — tablet | `butwort` | `burstwordtest` |
| "zephyrine" one key every 250 ms — tablet | `zphyrine` → 0/0 matches | — |
So characters are lost at an ordinary typing speed, not only in bursts. The plain field on the same page, same keyboard, keeps
everything, which points at the Find box's binding (value written back on re-render while keys are still arriving), not at the host
or the IME. The Android chat's "garbled typing" (D-81) was this. Other Blazor-bound text fields (Library search, Mark text boxes,
form fields, desk names) likely share the pattern; to check next round.
**Evidence:** R3 › results-*-api36 › function/results.jsonl (F-03b); `screenshots/r1/r3-print-dialog-find-typing.png` (right).

## AT-11 · S2 · Android (host process-death restore; Foundation only if a Ui hook is needed) · **verified** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): tabs back after a background kill 11 of 11, phone and tablet — On the phone, open tabs are lost when Android ends the app in the background
**Steps:** phone API 36, several tabs open, Home key, `am kill in.chuvadi.reader` (what Android does to a background app under memory
pressure), open the app again.
**Expected:** the tabs come back on the same document.
**Actual:** the phone opens on Home with **0 tabs** ("Pick up where you left off" still lists the document). Rate: **phone 11 of 11
lost** (R3: 1 of 1; R3b: 10 of 10 with 1–3 s in the background), **tablet 0 of 11** (same runs). R2's single phone run passed.
Phone-only points at the phone path of saving the session on `OnPause` (`RaiseSuspendingAsync` isn't awaited, and the phone shell
may not save tabs at all), not at the kill timing. Anyone who switches apps on a phone with low memory loses their tabs.
**Evidence:** R3 run 42537723474 and R3b run 42539596914 › results-phone-api36 › function/results.jsonl (F-15, F-15b),
10-after-process-death.png.

## AT-12 · S3 · Android · **still open** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release): Open with of the open file → tabs 4 → 5, phone and tablet (Android's DocumentLinks, see the analysis) — Opening a file that is already open adds a duplicate tab (Windows focuses the open tab)
**Shared behaviour (chuvadi-reader main 2b8899d, PR #11):** `IncomingFiles.Receive` → `OpenDocumentService.Request(path)` →
Reader → `TabsService.OpenAsync(path, …)`, which **focuses the existing tab when a tab with the same path is already open**
(`TabsService.cs:123–131`, case-insensitive path match). On Windows, opening an already-open file from Explorer hands the same
full path over (`DesktopSingleInstance` → `IncomingFiles`), so it focuses that tab — no duplicate. The shared code is right.
**Android:** `DocumentImport` → `DocumentLinks.Import` copies every incoming content URI into a **new** working folder
(`work/open/<new GUID>/<name>`, `DocumentLinks.cs:56, 86`), so the same document arrives under a new path each time and
`OpenAsync` can't recognise it.
**Steps:** open `doc-12p.pdf` with Open with; open it again from the same app.
**Expected (as Windows):** the existing tab comes to the front; Home's Recent keeps one entry.
**Actual:** a second tab with the same name each time (13 tabs of `design-doc.pdf` in R1: "13 of 13 tabs"; Home › Recent lists
`startup-doc.pdf` three times).
**Evidence:** R1 run 42518447149 › results-phone-api36 › design/phone-portrait-light-tabs-sheet.png and `*-home.layout.json`;
`screenshots/r1/themes-phone-home-mark.png` (Recent list).
**Fix options (for the Android chat):**
- (a) **Reuse the working copy for a URI already linked** — `Import` first looks up `_links` for the same content URI; if that
  working file still exists, return its path (so `OpenAsync` focuses the tab). Refresh the copy's bytes only when no tab holds it
  (or when the source changed and the tab has no unsaved edits). *Pros:* matches Windows exactly, also fixes the Recent duplicates,
  host-only. *Cons:* the same file reached through two different URIs (e.g. MediaStore and the Files provider) still looks like two
  documents; needs care not to overwrite a copy with unsaved edits.
- (b) Key the working folder on a hash of the URI instead of a new GUID. *Pros:* tiny change. *Cons:* overwrites the open tab's
  working copy on every re-open, unsaved edits included — unsafe.
- (c) Leave as is. *Cons:* differs from Windows; tabs and Recent fill with duplicates.
**Recommendation:** (a).

## AT-13 · S2 · Foundation (shared Ui; library if it's the renderer) · passing: R5 1/1 each; R6 **5/5 phone** (4.0–5.0 s) and **5/5 tablet** (7.4–13.9 s) — keep repeating — A page with one large image sometimes never paints
**Steps:** open `heavy-image.pdf` (one A4 page holding a 6000 × 6000 px JPEG; 28 MB file) with Open with; wait.
**Expected:** page 1 painted within a few seconds (it does, when it works: 3.9 s and 4.5 s).
**Actual:** in 2 of 4 runs the page stayed on its "page 1" placeholder for the whole wait (90 s, 120 s), app alive, CPU idle
(`top`: 0.0 %), no ANR, no exception in logcat — the render looks dropped, not slow:
| Run | Phone | Tablet |
|---|---|---|
| R4 (42543057904) | **not painted in 90 s** (and the next Open with waited behind it) | 3.9 s |
| R4b (42546917921) | 4.5 s | **not painted in 120 s** (the next document then opened fine) |
Idle CPU with no page points at a render request that is lost or dropped (a cancelled/timed-out render that isn't retried —
compare Foundation's B-24 "a stalled read never freezes the Reader") rather than the library being slow. Debug build; to repeat on
Release once AT-03 lands. **Evidence:** R4 › results-phone-api36 › robust/; R4b › results-tablet-api36 › robust/ (screenshots,
results.jsonl with PSS and `top`).

## AT-14 · S3 · Android (build settings) / Foundation (render path) · measured R6/R6b — decision needed — Cold "Open with" takes 3.9 s (phone) / 6.0 s (tablet) to paint page 1 on Release
**Evidence:** R4e (run 42741617577), table in RESULTS §2: from the launch to page 1 painted, median 3,920 ms phone and 6,028 ms
tablet over 12 cold runs, while the activity's first frame is ~1.2–1.5 s. The Release uses MAUI's default **profiled AOT**: the
startup profile covers MAUI and the BCL, but Chuvadi's assemblies get 4–14 KB AOT images each (B-08), i.e. the PDF open, parse
and render path is JIT-compiled on every cold start.
**Expected:** Arun asked for loads in milliseconds; first page well under 2 s on a mid-range phone.
**Options (for the coordinator; each to be measured by this chat before deciding):**
- (a) **Record a Chuvadi AOT profile** (startup + Open with + first render) and ship it with MAUI's (`AndroidAotProfile` items).
  *Pros:* precompiles exactly the hot path; small size cost. *Cons:* a recording step to keep current (CI can record it on the
  emulator each release).
- (b) **Full AOT** (`AndroidEnableProfiledAot=false`). *Pros:* everything precompiled, no profile to maintain. *Cons:* bigger
  download (typically +30–60 %), longer build.
- (c) **Leave as is.** *Cons:* 4–6 s first page.
**Recommendation (first):** let me build (a) and (b) as test-only variants in one run and report both numbers and sizes; then decide.

**Result of the variants (R6 run 42751641303, R6b run 42754433645; Foundation 846706e + Mobile UI c5c0b7e + Android 9ce073b;
API 36; cold Open with → page 1 painted, ms, 10 runs each; baseline and full AOT built and measured on the same runners):**
| | Phone median | Phone worst | Tablet median | Tablet worst | `.apk` | `.aab` |
|---|---|---|---|---|---|---|
| Baseline (as shipped, MAUI profile) — R6 | 3,616 | 7,172 | 7,749 | 13,272 | 42.97 MB | 42.58 MB |
| (b) Full AOT — R6 | **2,966** (−18 %) | **3,284** | **6,873** (−11 %) | **7,196** | 64.15 MB (+49 %) | 63.76 MB (+50 %) |
| Baseline — R6b | 4,842 | 9,051 | 8,776 | 16,120 | same | same |
| (b) Full AOT — R6b | **4,097** (−15 %) | **4,408** | **8,489** (−3 %) | **9,460** | same | same |
| (a) Recorded Chuvadi profile | **not built** — see below | | | | | |
Runner speed varies a lot between runs (baseline 3.6 s vs 4.8 s on the same phone image), so compare within a run. Build time:
baseline ~200–230 s, full AOT ~180–190 s.

**(a) can't be recorded with what ships in .NET 10 for Android.** `-t:BuildAndStartAotProfiling` works, but `-t:FinishAotProfiling`
calls `tools/Linux/aprofutil`, which isn't in the Linux SDK pack (`not found`), and the tool is in **none** of the 36.1.118 packs
(Linux, Windows, macOS — checked the Windows and macOS `.nupkg`s: only the prebuilt `startup.aotprofile` / `dotnet.aotprofile`).
The remaining recorder is the community `Mono.AotProfiler.Android` NuGet package (MIT), added to the project while recording.

**What the numbers say:** JIT is a minority of the cold first-page time. Full AOT — the upper bound for any profile — saves
0.3–0.9 s on the median and roughly **halves the worst case** (7.2 → 3.3 s phone, 13.3 → 7.2 s tablet in R6), at +21 MB. The other
~3–8 s is parse + render + paint of page 1 (the tablet's bigger page costs more), i.e. Foundation/library work, not build settings.

**Options now (for the coordinator):**
- (a′) Record the Chuvadi profile with `Mono.AotProfiler.Android` in CI each release. *Pros:* most of (b)'s gain, small size cost.
  *Cons:* a third-party tool in the release pipeline (rule 3 question: it only produces a data file, nothing of it ships); gain is
  capped by (b)'s 0.3–0.9 s.
- (b) Full AOT. *Pros:* no recording, steadier worst case. *Cons:* +21 MB `.apk`/`.aab` (+49 %).
- (c) Keep MAUI's profile; put the effort on the render path (page 1 first at screen resolution, defer other pages' work).
  *Pros:* attacks the larger 70–85 %. *Cons:* Foundation/library work.
**Recommendation:** (c) as the main fix, plus (a′) only if Arun accepts the recorder as build tooling; (b) only if size doesn't
matter. I'll measure any Foundation render change the same way (10 runs, phone and tablet).
Startup trimming / work deferral in Foundation (B-29) already applies; this is about JIT on the open/render path.

## AT-15 · S2 · Foundation (routed 10 Nov, with the page drift) · **still open** R5 run 42746209649 (Foundation f88f9ef + Mobile UI c5c0b7e + Android 9ce073b, Release) — Mark › Text: a finger tap on the page makes no text box (phone and tablet)
**Steps:** Release (f88f9ef composition), API 36, open a PDF, Mark, choose Text (button shows as on), tap the page — quick tap, then
a slow tap (finger held 400 ms) elsewhere on the page.
**Expected:** a text box appears where the finger touched (`MkUpCore`: "tiny drag = a click → default-sized box"), with the caret in it.
**Actual:** nothing: the header stays "0 text · 0 shapes · 0 images", no editor appears, focus goes to the desk (`DIV.rdesk`).
Same on phone and tablet, quick and slow taps. **Evidence:** R4f (run 42744098247) › results-*-api36 › function2/ (02, 03 screenshots,
results.jsonl F-04a/F-04b); `screenshots/r4/at15-mark-text-tap.png`.
**What the page receives** (pointer log from the page, quick tap): `pointerdown` on `.mk-layer.textmode` (touch-action none) →
`touchstart` on the layer → **`pointerup` on `.rdesk`** (touch-action pan-y) → `touchend` / `click` on the layer. The layer's
`@onpointerup="MkUp"` never sees the pointer going up, so the draft is never committed. Also `MkDown` awaits `CacheLayerRect` before
it sets `_mkMode`, so even an `up` on the layer can arrive while the mode is still `None`.
**Fix (proposal):** on `pointerdown` in the markup layer, `setPointerCapture(e.pointerId)` (a few lines in the existing markup JS) so
`move`/`up` come back to the layer; set `_mkMode`/draft synchronously before the awaited rect read (or read the rect first on tool
selection). **R5 adds shapes:** Mark › Rectangle, a 600 ms finger drag → "0 shapes"; the page log shows `pointerdown` on `.mk-layer.drawmode`,
then **all 21 `pointermove`s and the `pointerup` on `.rdesk`** (touch-action pan-y). So something holds the pointer for the desk —
most likely the phone/tablet swipe-and-pan handling on `.rdesk` (mobile.js) capturing the pointer on `pointerdown`, which steals
every markup gesture on touch (text, shapes, freehand, probably the Protect redaction box). Owner: whoever owns that handler
(Mobile UI's mobile.js, or Foundation's reader.js); the markup layer should win when a markup tool is active.

## Questions for the coordinator (not filed as bugs)
- **Q-1 Same file opened again → new tab** — answered by the coordinator (9 Nov 07:12): Windows is the reference. Checked the shared
  code and filed the difference as **AT-12** (Android).
