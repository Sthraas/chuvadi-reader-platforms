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

## AT-06 · S3 · Mobile UI · **verified** R10 run 42938865447 (Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36): every control measured is ≥ 44 dp — phone 42 of 42, tablet 30 of 30, including the leftovers listed in round 8 — Touch targets under 44 dp (handout: 48 dp on tablet and phone)
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

## AT-09 · S3 · Mobile UI · **verified** R8 run 42802779369 (Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8, Release, API 36): phone 1/1 on page 3; tablet now scrolls the match into view (`screenshots/r8/r8-find-shape-redact.png`). The tablet page box still says 2 while page 3 fills the screen — that is the page-box drift, tracked as AT-16 — Find reports the match but doesn't bring it into view
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

## AT-12 · S3 · Android · **verified** R8 run 42802779369 (Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8, Release, API 36): Open with of the open file keeps 4 tabs and focuses it, phone and tablet — Opening a file that is already open adds a duplicate tab (Windows focuses the open tab)
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

## AT-13 · S2 · Foundation (shared Ui; library if it's the renderer) · **verified**, still repeating: R10 run 42938865447 5/5 phone (5.6–6.3 s) and 5/5 tablet (8.1–8.5 s); no blank page in any run since the fix — A page with one large image sometimes never paints
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

## AT-14 · S3 · Foundation (open sequencing) · **partly fixed** R10 (D-164 A landed and works; C not achieved): cold Open-with to page 1 — phone 5,150 → 4,074 ms, tablet 7,572 → 9,149 ms (trace build, medians of 10). See the round 10 table below — Cold "Open with" takes 3.9 s (phone) / 6.0 s (tablet) to paint page 1 on Release
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

### AT-14 round 7 (run 42795565556) — where the cold Open-with time goes, and Chuvadi-only full AOT
**Variants (10 cold Open with each, API 36, same runner per row):**
| | Phone page 1 median / worst | Tablet page 1 median / worst | `.apk` | `.aab` | Chuvadi AOT images |
|---|---|---|---|---|---|
| Baseline (as shipped) | 5,028 / 11,878 | 9,031 / 15,997 | 42.97 MB | 42.58 MB | 1.3 MB |
| **Chuvadi assemblies in full** on top of profiled AOT | 4,958 / **5,313** | 9,431 / **10,142** | 46.84 MB (+9 %) | 46.46 MB (+9 %) | 12.0 MB |
| Full AOT | 4,886 / 5,586 | 9,316 / 10,478 | 64.15 MB (+49 %) | 63.76 MB (+50 %) | 22.9 MB |
Medians are within noise of each other; precompiling only trims the **worst** case. JIT is not the bottleneck.

**Timeline (trace build: Console markers → logcat, plus the page's own clocks; phone / tablet, median ms after the launch, 10 runs):**
| Milestone | Phone | Tablet | Step cost (phone) |
|---|---|---|---|
| process started | 53 | 71 | |
| `CreateMauiApp` starts (= .NET runtime + assemblies up) | 658 | 1,479 | **605** runtime start |
| MAUI app built | 737 | 1,571 | 79 |
| `MainActivity.OnCreate` / done | 797 / 881 | 1,648 / 1,752 | 144 |
| WebView provider loaded | 952 | 1,845 | 71 |
| WebView navigation starts | 1,121 | 2,044 | 169 |
| host page loaded | 1,281 | 2,296 | 160 |
| Android first frame (splash) | 1,445 | 2,477 | |
| `blazor.webview.js` loaded | 1,689 | 2,872 | **408** script load |
| DOMContentLoaded | 1,739 | 2,900 | |
| Blazor app root rendered (in the DOM) | 2,012 | 3,207 | 273 |
| library open of the PDF (start → end) | 2,146 → 2,269 | 3,380 → 3,530 | **123** parse |
| **first paint of the WebView** | **3,602** | **5,356** | 1.3 s after the app root was in the DOM |
| `TabsService.OpenAsync` (the tab opens) | **4,233** | **6,296** | **~2.0 s / 2.8 s after the PDF was already open** |
| page boxes in the DOM | 4,314 | 6,434 | |
| page 1 render (start → end) | 4,643 → 4,753 | **8,569** → 8,701 | **110** render; tablet waits **2.1 s** after the boxes |
| page 1 SVG in the DOM → painted | 4,828 → **4,920** | 9,228 → **9,319** | |
(The trace build also had the Chuvadi-full AOT: MSBuild's build nodes kept the edited targets. Fixed for R7b.)

**Reading:** the library is fast (open 123 ms, render 110 ms). The cold first page is spent in (1) **~2–2.8 s of waiting between
the PDF being opened and the tab opening** — the incoming file waits for the app's ready signal, which `MainLayout` raises only
after a chain of sequential JS round-trips on first render (platform attributes, save folders, profile, theme, apply theme,
storage, the `shell.js` module import); the WebView doesn't even paint until 3.6 s; (2) on the tablet, **2.1 s between the page
boxes and the first render request**; (3) the .NET runtime start (0.6 s phone, 1.4 s tablet); (4) loading `blazor.webview.js` (0.4 s).
R7b adds markers on each hydrate step, the ready signal, the release of the waiting file and the render request to pin (1) and (2).

### AT-14 round 7b (run 42800207093) — the wait pinned down
Same trace build with finer markers (and without the Chuvadi-full AOT this time); phone / tablet, median ms after the launch, 10 runs:
| Milestone | Phone | Tablet |
|---|---|---|
| host has copied the incoming file (`Opened from another app`) | **991** | **1,554** |
| `IncomingFiles.Receive` (file handed to the kit; parked until Ready) | 1,226 | 1,826 |
| Blazor up: `MainLayout` first render | 2,051 | 2,591 |
| a PDF open starts — caller `EnsureLoadedAsync` (last session's tab being restored, not the incoming file) | 2,190 | 2,754 |
| save folders / profile / theme hydrated, theme applied | 2,280 → 2,296 | 2,912 → 2,928 |
| `shell.js` import begins | 2,441 | 4,346 (2,614 at best) |
| WebView's first paint (Home) | 3,799 | 4,224 |
| **`Ready.SignalReady()` → file released → open requested** | **4,268** | **5,087** |
| `TabsService.OpenAsync` | 4,414 | 5,222 |
| page boxes in the DOM | 4,503 | 5,321 |
| **first render request for page 1** | 4,834 | **7,320** |
| page 1 render start → end | 4,843 → 4,976 | 7,330 → 7,427 |
| page 1 in the DOM → painted | 5,043 → **5,150** | 7,485 → **7,572** |

**Where the cold first page goes (phone 5.15 s; tablet 7.57 s):**
1. **Waiting for Ready: ~3.0 s phone / 3.3 s tablet.** The file is copied and handed over at ~1.0–1.8 s, but `IncomingFiles` holds it
   until `MainLayout.OnAfterRenderAsync` reaches `Ready.SignalReady()` — after the hydrate calls, `ApplyThemeAsync`, a storage read
   and `import("shell.js")` + `init`, all awaited one after another. From "theme applied" to Ready is **~2.0–2.2 s**, during which the
   WebView is doing Home's first layout and paint (first paint lands at 3.8–4.2 s) and the JS calls queue behind it.
2. **Home is painted first, then thrown away** for the Reader (~1.5 s of first paint that an Open-with launch doesn't need).
3. **Tablet only: 2.0 s between the page boxes and the first render request** (5,321 → 7,320; phone 0.33 s).
4. Smaller: .NET runtime start 0.6 s phone / 1.2 s tablet; `blazor.webview.js` 0.35 s; the previous session's tab is reopened
   first (2,190) even though an incoming file is waiting.
5. **Not** the bottleneck: library open **~120 ms**, page render **~100–130 ms**, SVG into the DOM and paint ~170 ms, JIT (AOT variants above).

**Options (Foundation; each measurable by this chat the same way):**
- (A) **Don't park the incoming file behind Ready.** Start the open as soon as Blazor is up (2.05 s) — or begin the library open on the
  host's copy (0.99 s) — and route straight to the Reader. *Pros:* removes most of (1) and (2): about **−2 to −2.5 s**; shared code, so
  every platform's "open with" gains. *Cons:* the Reader must render before theme/profile hydration finishes (first-paint theme is
  already in `index.html`); ordering care with session restore.
- (B) **Raise Ready earlier / shorten the chain:** signal before `shell.js` import and the storage read, run the hydrates concurrently.
  *Pros:* small change, ~−1.5 to −2 s. *Cons:* Home is still painted first.
- (C) **Tablet render-request gap (3):** find what the tablet shell waits for between page boxes and the first render (~−2 s tablet).
- (D) Leave the build settings as shipped; no AOT change (Chuvadi-only full AOT: +9 % size for no median gain, only a steadier worst case).
**Recommendation:** (A) + (C), with (B) as the first step if (A) is too large for now; (D) for the build. Expected on these emulators:
phone ≈ 2.5–3 s, tablet ≈ 3.5–4 s for a cold Open with; a real phone is several times faster than this software-rendered emulator.
### AT-14 round 10 (run 42938865447; Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36) — after D-164 (A)
Measured the same way as round 7b (test-only trace build, cold Open with, 10 runs, median ms from process start).

| Milestone | Phone R7b | Phone R10 | Tablet R7b | Tablet R10 |
|---|---|---|---|---|
| open request reaches the shared code | 4,268 | **976** | 5,087 | **2,334** |
| PDF opened (library) | — | 1,857 | — | 3,766 |
| first paint of the shell | — | 2,836 | — | 5,764 |
| page boxes laid out | — | 3,253 | — | 6,022 |
| shell script imported | — | 3,563 | — | 7,498 |
| Ready signal | — | 3,751 | — | 8,618 |
| page 1 render requested | — | 3,778 | — | 8,702 |
| **page 1 painted** | **5,150** | **4,074** | **7,572** | **9,149** |

As-built Release, same intent, `startup.py` (10 runs): phone median 4,862 ms (worst 7,725) against 5,028 (11,878) in round 7;
tablet 9,398 (15,510) against 9,031 (15,997).
**Reading:** (A) did what it was meant to: the file is being opened 3.3 s (phone) / 2.8 s (tablet) earlier, and the phone gains
about 1.1 s. **(C) is not there yet:** the first page render is still requested only just after the Ready signal (27 ms after on
the phone, 84 ms on the tablet), so the early open is waiting for the shell. On the tablet the page boxes are laid out at 6.0 s
and the render is not asked for until 8.7 s — 2.7 s of pure waiting (0.5 s on the phone). The tablet emulator run was also slower
overall in this round (runtime start 1,216 → 1,456 ms), so its absolute numbers are not a like-for-like regression; the 2.7 s gap is.
**Remaining fix (Foundation):** ask for page 1's render as soon as the PDF is open and the page boxes exist, not on Ready; and
look at why first paint is at 2.8 s / 5.8 s. Expected gain if the render follows the page boxes: about 0.5 s phone, 2.5 s tablet.

## AT-15 · S2 · Foundation (routed 10 Nov, with the page drift) · **partly verified** R8 run 42802779369 (Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8, Release, API 36): shapes by finger drag work (phone "1 shape"; tablet rectangle drawn, screenshot), the Protect redaction box draws on tablet ("1 box"), and a finger tap with Mark › Text now creates the box. Still wrong: the new text box doesn't take the caret — see AT-17 — Mark › Text: a finger tap on the page makes no text box (phone and tablet)
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

## AT-16 · S3 · Foundation (shared Ui) · **verified** R10 run 42938865447 (Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36): its own check (`ci/drift.py` DR-7: Find jump, then the page box against the page under the middle of the screen) passes on phone and tablet; the other six drift checks pass too (7 of 7 each) — Page box drifts from the page on screen (tablet, after Find)
**Steps:** tablet API 36, open `doc-12p.pdf`, Find `zephyrine` (one match, foot of page 3).
**Expected:** the page box says 3 — page 3 fills the screen.
**Actual:** the match is shown and page 3 fills the screen, but the page box says **2** ("2 / 12"). Phone says "3 / 12".
**Evidence:** R8 run 42802779369 (Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8, Release, API 36) › results-tablet-api36 › function/04-find.png (`screenshots/r8/r8-find-shape-redact.png`, second frame);
results.jsonl F-03. **Seen again in R8b (run 42807280851): 2 of 2 on tablet.** A dedicated check (`ci/drift.py`: box vs the page under the middle of the screen after a cold open, a scroll,
a second document, a reopen, a rotation and a restart) ran in R8b: cold open, second document, reopen and rotation agree on phone and
tablet (box = page on screen, steady for 6–8 s). Its "move to page 5" and "restart" steps were wrong in my script (it scrolled the page
from script, and a plain launch opens on Home); corrected for round 9. So the only drift seen so far is the tablet one after Find.
**Round 10:** fixed — see the heading. Kept in the drift suite for every round.

## AT-17 · S2 · Foundation (shared Ui, markup) · **verified** R10/10b (Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36): the caret is in the new box after the first tap (`TEXTAREA` focused) and "chuvadimark" types into it — tablet runs 42938865447, 42948523807, 42951440189; phone run 42948523807 — Mark › Text: the new box doesn't take the caret; typing fires one-key shortcuts instead
**Steps:** phone or tablet, open a PDF, Mark › Text, tap the page (a box appears — AT-15 fixed that), type `chuvadimark`.
**Expected:** the caret is in the new box (and the on-screen keyboard opens); the letters go into the box.
**Actual:** an editor element exists but focus stays on the page area (`DIV.rdesk`); nothing is typed into the box, and the letters
run the shell's one-key commands — the `i` in "chuvadimark" opened the system image picker ("Images in Downloads") over the app
(seen in R4d, R4f and R8, phone). With a hardware keyboard that is exactly what a person would hit; on glass the keyboard
doesn't open until the box is tapped again. **Confirmed R8b (run 42807280851), phone and tablet:** a second tap on the box puts the
caret in it (`TEXTAREA.mk-ta`), the keyboard opens and "chuvadimark" is typed correctly (`screenshots/r8/r8b-textbox-form-redact.png`).
**Evidence:** R8 run 42802779369 (Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8, Release, API 36) › results-*-api36 › function2/ (02–04 screenshots; results.jsonl F-04a: `editors: 1`,
`active: DIV.rdesk`); `screenshots/r8/r8-find-shape-redact.png` (first frame: the picker).
**Fix (proposal):** focus the box's editor in the same pointer-up handler that creates it (JS side, inside the user gesture, so
Android also raises the keyboard); and don't run one-key shortcuts while a markup draft/box is selected.
Blocks: text markup + Save, and the Mark text box part of AT-10.
**Round 10:** fixed — see the heading. This also clears the Mark text box part of AT-10 (a burst of 11 keys all arrive).

## AT-18 · S1 · Android (host) · **fixed; verified on tablet for 8 paths, on phone for 3; phone Save as new PDF still unproven (AT-22)** — R10/10b/10c, table below — Nothing that saves to a new file works on Android: the host's save pickers are switched off
**Steps:** Release, phone or tablet. Any of: Mark › draw a rectangle › **Save as new PDF**; Protect › draw a redaction box ›
**Save redacted copy**; Arrange › pages on a desk › **Bind all**.
**Expected:** Android's "save to" picker opens, the file is written where the person chose.
**Actual:** nothing happens — no picker, no file, no message. The button can be tapped again and again. (Round 8c, run 42840233328,
Foundation 741930b + Mobile UI 2b29227 + Android 7c8e2d8: 0 files from Save as ×2, Save redacted copy, Bind all, on phone and tablet,
while print → "Save as PDF" in the same run produced its file.) So today a person can mark up, redact or arrange on Android and
**has no way to keep the result** (phone has no in-place Save; redaction and Bind only ever save to a new file).
**Cause:** `AndroidFilePicker.SavePickersEnabled` is hard-coded `false` (`src/ChuvadiReader.Android/Platform/AndroidFilePicker.cs:24`,
still so at Android 8f173c9): `PickSavePdfAsync`, `PickSaveImageAsync`, `PickSaveSessionAsync` and `PickFolderAsync` return null at once.
The comment says "switch on once the Ui's CommitAsync hooks are in (A-02 / F-1)". Those hooks **are** in Foundation now
(`WriteBackExtensions.DeliverOrThrowAsync`, called from Reader, Bench, Redact, Split and Merge), so the switch looks simply left behind.
The Android chat's own rounds never exercised a save to a new file, and neither had mine until the save suite.
**Fix (Android chat):** set the switch on (or remove it), then confirm each save site delivers. Round 9 runs my save suite twice:
on the Release as built, and on a test-only build with only this switch flipped, so the saved files are read back either way.
**Also:** a save that can't proceed should say so; silence is the worst outcome (Foundation, low priority once the switch is on).
**Round 9 / 9b (runs 42867016981, 42875987375; Android 8f173c9 + Foundation dd59362 + Mobile UI 3ecbc75, Release):** confirmed on the
build as handed over — Save as new PDF, Save redacted copy and Bind all open no picker and write no file, phone and tablet.
On the **test-only build with only this switch turned on** (tablet): Save as new PDF wrote `sv-shape-edited.pdf` with the rectangle on
page 1 and `sv-form-edited.pdf` with the form values intact; Save redacted copy wrote `sv-redact-redacted.pdf` with the covered heading
gone from the page content and everything else kept. So the shared code behind the switch works; the switch is the fault.
**Round 10 / 10b / 10c (runs 42938865447, 42948523807, 42951440189; Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36, the build as handed over).**
Each saved file was pulled off the device and read back with a separate PDF reader.

| Path | Tablet | Phone |
|---|---|---|
| Save (in place, text box) | PASS — text in the picked file | (phone has no in-place Save) |
| Mark › Save as new PDF (rectangle) | PASS — `sv-shape-edited.pdf`, mark on page 1, 12 pages, original untouched | **not saved — AT-22** |
| Save as after markup on a filled form | PASS — patient "Ravi", ward "Cardiac" still in the file | not saved — AT-22 |
| Protect › Save redacted copy | PASS — heading gone from text and bytes, rest kept, original untouched | PASS — same checks |
| Protect › Password › Save protected copy | PASS — encrypted, opens with the password, 12 pages, original still open | not proven: the Confirm field stayed empty in my run, so the button was (rightly) disabled; script fixed in 10c, phone leg of 10c hung |
| Document › Flatten forms & marks | PASS — `sv-flatten (flattened).pdf`, 12 pages, text kept | PASS |
| Document › Reduce file size (Press) | not proven — the Press card opens; my script did not press its `Press →` button | not proven (same) |
| Save as on a /Rotate 90 page | PASS — mark where it was drawn, `/Rotate 90` kept | not saved — AT-22 |
| Arrange › Bind all (folder picker) | PASS (10c) — folder chosen, 2 desks → 2 PDFs with the right pages; but see AT-21 | not proven — 10b used the wrong picker steps (Bind asks for a folder); fixed in 10c, phone leg hung |
| Print › Save as PDF (vector) | PASS — 12 pages, text kept, no page images | PASS |

Not exercised by anyone yet: snapshot image, desk session file, Split, Merge, Export pages as images, Lift, Combine.
No crash or ANR in any save run.

## AT-19 · S2 · Android (build) · **verified in CI** R10 (clean build on the pinned SDK and workload set: 0 errors, 0 warnings, three runs) — one leftover: the pin exists only inside the workflows, see the note at the end — The clean build breaks on the .NET SDK patch released 10 Nov (10.0.404): the toolchain isn't pinned
**Steps:** clean runner, `actions/setup-dotnet` with `10.0.x` (what the Android workflow and mine use), `dotnet workload install
maui-android`, publish Release (run 42863203546, 10 Nov 17:16 UTC; Android 8f173c9 + Foundation dd59362 + Mobile UI 3ecbc75).
**Expected:** builds, as it did earlier the same day on SDK 10.0.403.
**Actual:** Release and Debug both fail:
`ChuvadiReader.Android.csproj(80,5): error : The app must ship .NET's third-party notices; not found at
~/.nuget/packages/microsoft.netcore.app.runtime.mono.android-arm64/10.0.15/THIRD-PARTY-NOTICES.TXT`.
The `ChuvadiRuntimeNotices` target builds the path from `$(BundledNETCoreAppPackageVersion)` (now 10.0.15), but that isn't the
runtime pack the Android build actually resolves under the new SDK, so the file isn't there.
**Why it matters:** a release build made tomorrow fails, or — worse, once fixed loosely — silently ships a different runtime than the
one tested. Nothing in the repo fixes the SDK version (no `global.json`).
**Fix options (Android chat / Foundation for `global.json`):**
- (a) **Pin the SDK** (`global.json` with `rollForward: disable` or `latestPatch` off, and the same version in every workflow) and
  move it deliberately. *Pros:* what is tested is what ships; byte-stable builds. *Cons:* security patches need a conscious bump.
- (b) **Take the notices from the resolved runtime pack** (`@(ResolvedRuntimePack)` → `PackageDirectory`) instead of composing the
  path. *Pros:* survives SDK patches. *Cons:* alone, builds still float with the SDK.
- **Recommendation: both** — (b) so the target is correct, (a) so releases are reproducible.
My workflow is pinned to 10.0.403 from round 9 on (and now fails the step when publish fails; it used to carry on).
**Round 10:** the workflows pin SDK 10.0.403 and workload set 10.0.403 (D-178) and the clean build is clean.
**Leftover (small, Foundation + Android):** there is no `global.json` in the repo at Android ce890a6 or Foundation 07ed3ca — the
Android workflow writes one into the composed checkout at build time, and `docs/android/README.md` still says ".NET SDK 10.0.x".
So a release built by hand from the repo (not through the workflow) is not pinned and can pick up 10.0.404 or later.
- (a) **Check `global.json` into the repo root (Foundation)** and correct the README. *Pros:* every build, anywhere, is the tested
  toolchain. *Cons:* one more file to bump on purpose.
- (b) Leave it CI-only and state "release builds come only from the workflow". *Pros:* nothing to change. *Cons:* relies on habit.
- **Recommendation: (a).**

## AT-20 · S2 · Android / Mobile UI · open, still unproven after R10c — needs the Android chat's gesture check or a real tablet — Tablet: long-press drag from the Shelf doesn't put a page on a desk
**Steps:** tablet API 36 portrait, one PDF open, Arrange (Shelf sheet shows pages 1–12, Desk 1 says "Drag pages here"); long-press
shelf page 3 and drag it onto the desk.
**Expected:** the page lands on the desk (it does on the phone: two pages dragged, then reordered by long-press drag, R9b).
**Actual:** the desk stays at 0 pages. Tried with Android's own `input draganddrop` (long press + drag, rotation-aware) and with the raw
touch script, twice each per run, in R9 and R9b: 0 of 8. `Bind all` therefore stays disabled.
**Caveat:** this is the one result here that rests on synthetic gestures only, and the raw script is known not to follow the tablet's
rotation; the Android chat's own gesture check covers this drag — please say whether it passes on the tablet in portrait. If it
does, this is my tooling and I'll close it.
**Round 10b / 10c (tablet, portrait):** still 0 of 4 shelf → desk drags, and now also 0 of 2 desk reorders by long-press drag, with
both synthetic gestures. The same script moves and reorders pages on the phone (2 of 2 and 1 of 1, run 42948523807). The tablet is
not stuck without it: Reader › "Send this page to a desk in Arrange" put two pages on desks and Bind all then wrote them (10c).
Still the same caveat — synthetic gestures only. **Question stands:** does the Android chat's gesture check pass shelf drag and
desk reorder on the tablet in portrait?

## AT-21 · S4 · Android (host) · open — After Bind all, the message shows the app's internal working path instead of the folder the person chose
**Steps:** tablet API 36, Arrange with pages on desks › **Bind all** › choose `Download/at-bind` in Android's folder picker › Allow.
**Expected:** "Bound 2 desks into at-bind" (the folder's own name), as AT-07 settled for tabs and recents.
**Actual:** "Bound 2 desks into /data/user/0/in.chuvadi.reader/cache/work/folder/b7b7ff383d02410990fcbf082bdd5ba6". The files
themselves are in the chosen folder and correct. (Run 42951440189, Android ce890a6 + Foundation 07ed3ca + Mobile UI 8699719, Release, API 36; `screenshots/r10/r10c-tablet-press-desks-bind.png`, third frame.)
**Cause:** the host hands the shared code a working folder and copies out afterwards; the shared message prints the path it was given.
**Fix (Android chat):** give the message the picked folder's display name (the same display-name route used for AT-07). Any other
"saved to …" message that prints a path (Export, Scatter, Press) should be checked the same way.

## AT-22 · S2 · Mobile UI (phone look) / Foundation if the card is shared · open, needs one confirming look — Phone: after drawing a mark, its property card covers **Save as new PDF**, and the card has no close control
**Steps:** phone API 36, open a PDF, Mark › Rectangle (or Text), draw on the page. The mark's card ("Rectangle" / "Text box":
stroke, fill, rotation, Duplicate, Delete) slides up over the lower half of the screen.
**Expected:** the person can still reach Save as new PDF, or the card has an obvious way to be put away.
**Actual:** the Save as new PDF button sits underneath the card (`SECTION.fcard` is the element at the button's position). The card's
only buttons are its property controls, **Duplicate** and **Delete** — no Close, no handle. 4 of 4 Save-as attempts on the phone ended
with no file for this reason (text box, rectangle, form, rotated page; run 42948523807, `screenshots/r10/r10b-phone-saves.png`,
frames 1–3 and 6). On the tablet the card sits beside the page and Save as works.
**What I have not shown:** whether a swipe down on the card or a tap on an empty part of the page puts it away — round 10c tried
exactly those, but its phone leg hung and was cancelled (see RESULTS.md). So this is S2 "blocks saving on the phone unless the person
discovers a gesture", pending that one look.
**Fix options (Mobile UI):**
- (a) Give the card a visible handle / Close, like the other phone sheets. *Pros:* discoverable, consistent. *Cons:* one more control.
- (b) Keep the Save button above the card (float it over the card's top edge) while there are unsaved marks. *Pros:* saving never
  hides. *Cons:* crowds a small screen.
- (c) Make the card a short peek (title row only) that expands on tap. *Pros:* page stays visible while marking. *Cons:* more work.
- **Recommendation: (a) now, (c) when there is time.**

## Questions for the coordinator (not filed as bugs)
- **Q-1 Same file opened again → new tab** — answered by the coordinator (9 Nov 07:12): Windows is the reference. Checked the shared
  code and filed the difference as **AT-12** (Android).
- **Q-R10-1 Form filling:** the Reader has no Fill form tool on any platform (greyed "until built", PHASE1-PARITY). Is form filling
  by touch expected in this release? If yes it is a feature gap for Foundation, not an Android bug; if no I'll stop listing it.
- **Q-R10-2 Tablet drag (AT-20):** does the Android chat's gesture check pass shelf → desk drag and desk reorder on the tablet in portrait?
- **Q-R10-3 `global.json` (AT-19 leftover):** check it into the repo root — recommended (a) above. Who owns it, Foundation?
