# Android Test — bugs

Severity: **S1** blocks release or loses data · **S2** feature broken or wrong · **S3** visible defect with a workaround · **S4** cosmetic / hygiene.
Owner: **Android** (host) · **Mobile UI** (look) · **Foundation** (shared Ui/Core, legal drafts) · **Library** (Arun) · **Coordinator** (decision).
Status: open · fixed (commit) · verified (run).

Composition under test (round 1): Foundation `839d39d` + Mobile UI `95b9d79` + Android `7ec8017`, built from clean in
run [42518447149](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42518447149) (artifact `audit`).

---

## AT-03 · S1 · Foundation (+ Android CI) · fixed in Foundation c91a581 — to verify on Release — The Release app crashes at every launch (trimmed constructor)
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

## AT-01 · S2 · Android + Foundation · waiting on Arun (rule 3; coordinator 9 Nov) — Third-party notices leave out AndroidX, Material Components and Kotlin, which ship in the app
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

## AT-02 · S4 · Android · open (routed to the Android chat 9 Nov) — Unused MAUI Essentials components are declared in the shipped manifest
**Evidence:** `audit/manifest-xmltree.txt`: `WebAuthenticatorIntermediateActivity`, `IntermediateActivity`,
`microsoft.maui.essentials.fileProvider`, and three broadcast receivers (Essentials Connectivity, Battery, Energy Saver). All
`exported=false`, so not reachable from other apps; the app uses none of them (it has its own `SharedFileProvider`).
**Expected:** only what the app uses (smaller attack surface; nothing in a Play review that looks like connectivity monitoring).
**Fix (proposal):** `tools:node="remove"` entries in the host's `AndroidManifest.xml`. Low risk; verify Share and Open still work.

## AT-04 · S3 · Mobile UI · open (routed 9 Nov) — Desk header on touch still shows the desktop action row (12f, 12i; D-114)
**Steps:** phone or tablet, open a PDF, Arrange.
**Expected (12f / 12i, D-114):** desk header = name, page count, `···`; the desk actions live in the `···` menu on touch.
**Actual:** header shows the colour swatch, name, a "BM" chip, page count, ← → arrows, duplicate, `···` and delete — the desktop
row. The arrows/duplicate/delete are ~20 dp targets and the swatch 16 dp (see AT-06).
**Evidence:** `screenshots/r1/12f-vs-app.png`, `12i-vs-app.png` (API 36, R1, Debug build of the same composition).
Foundation 839d39d's message says H-16 (desk actions in the menu on touch) landed, so either it covers only the desk toolbar or it
isn't keyed on the touch form factor here.

## AT-05 · S3 · Mobile UI · open (routed 9 Nov) — Tablet portrait top bar has no `Document ▾` menu (12f)
**Expected (12f):** tabs · pager · `Document ▾` · search, as in landscape.
**Actual:** tablet portrait shows tabs · pager · search; `Document ▾` is gone, so Properties / Export / Compress / Merge / Split
have no entry point from the top bar in portrait. **Evidence:** `screenshots/r1/12f-vs-app.png`.

## AT-06 · S3 · Mobile UI · open (routed 9 Nov) — Touch targets under 44 dp (handout: 48 dp on tablet and phone)
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

## AT-07 · S4 · Android · fixed in Foundation c91a581 (P-08) — to verify — Tabs and Home's recent cards/rows label themselves with the internal working path
The tablet tab's `title`, and the accessible name/`title` of every Home "Pick up where you left off" card (`.rcard`) and Recent
row (`.rrow`) on phone and tablet, is the working copy path, e.g. `/data/user/0/in.chuvadi.reader/cache/work/open/1429e6d5d0cd4…`
(`design/*-home.layout.json`). TalkBack reads that path aloud. Android shows `title` on long-press/hover with a mouse. **Expected:** the document's name
(or the original location the person chose), never the app's private cache path.

## AT-08 · S3 · Android · open (routed to the Android chat 9 Nov) — Status and navigation bar areas stay cream in the Night, Palm and Indigo themes
**Steps:** phone, Settings › theme Night paper (or Palm leaf / Indigo ink); look at the top (clock, signal) and the bottom
(gesture bar).
**Expected:** the system-bar areas take the theme's paper colour (as the first-paint background in `index.html` already does per
theme), with light icons on Night paper; edge-to-edge as on Windows' title bar.
**Actual:** both strips stay the cream `#F2EAD6` in every theme, so Night paper shows a cream band above a dark app bar and
below a dark bottom bar; Palm and Indigo show a mismatched band.
**Evidence:** `screenshots/r1/themes-phone-home-mark.png` (columns: Cream, Night, Palm, Indigo, High contrast).
**Fix (proposal):** `SystemBars` follows the theme (theme-changed signal → window background / `isAppearanceLightStatusBars`),
or the WebView draws under the bars and pads with `env(safe-area-inset-*)`.

## AT-09 · S3 · Mobile UI · open (routed 9 Nov) — Find reports the match but doesn't bring it into view
**Steps:** tablet (API 36), open `doc-12p.pdf` (12 pages; the word "zephyrine" appears once, near the foot of page 3), Find,
type `zephyrine`.
**Expected:** 1/1, and the view moves so the highlighted match is on screen (page 3, foot).
**Actual:** 1/1, but the view shows the foot of page 2 and the top of page 3; the match stays off screen and the page box still
says 2. **Evidence:** R2 run 42533545934 › results-tablet-api36 › function/04-find.png (`screenshots/r1/r2-find-print.png`, left).
Re-checked next round on phone too (phone typing in R2 was cut short by the test, see notes).

## AT-10 · S2 · Foundation (shared Ui) · open (routed D-149) — The Find box drops typed characters; a plain field doesn't
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

## AT-11 · S2 · Android (host process-death restore; Foundation only if a Ui hook is needed) · open (routed D-149) — On the phone, open tabs are lost when Android ends the app in the background
**Steps:** phone API 36, several tabs open, Home key, `am kill in.chuvadi.reader` (what Android does to a background app under memory
pressure), open the app again.
**Expected:** the tabs come back on the same document.
**Actual:** the phone opens on Home with **0 tabs** ("Pick up where you left off" still lists the document). Rate: **phone 11 of 11
lost** (R3: 1 of 1; R3b: 10 of 10 with 1–3 s in the background), **tablet 0 of 11** (same runs). R2's single phone run passed.
Phone-only points at the phone path of saving the session on `OnPause` (`RaiseSuspendingAsync` isn't awaited, and the phone shell
may not save tabs at all), not at the kill timing. Anyone who switches apps on a phone with low memory loses their tabs.
**Evidence:** R3 run 42537723474 and R3b run 42539596914 › results-phone-api36 › function/results.jsonl (F-15, F-15b),
10-after-process-death.png.

## AT-12 · S3 · Android · open — Opening a file that is already open adds a duplicate tab (Windows focuses the open tab)
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

## AT-13 · S2 · Foundation (shared Ui; library if it's the renderer) · open, intermittent (routed D-149) — A page with one large image sometimes never paints
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

## Questions for the coordinator (not filed as bugs)
- **Q-1 Same file opened again → new tab** — answered by the coordinator (9 Nov 07:12): Windows is the reference. Checked the shared
  code and filed the difference as **AT-12** (Android).
