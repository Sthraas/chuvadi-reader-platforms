# Android Test — bugs

Severity: **S1** blocks release or loses data · **S2** feature broken or wrong · **S3** visible defect with a workaround · **S4** cosmetic / hygiene.
Owner: **Android** (host) · **Mobile UI** (look) · **Foundation** (shared Ui/Core, legal drafts) · **Library** (Arun) · **Coordinator** (decision).
Status: open · fixed (commit) · verified (run).

Composition under test (round 1): Foundation `839d39d` + Mobile UI `95b9d79` + Android `7ec8017`, built from clean in
run [42518447149](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42518447149) (artifact `audit`).

---

## AT-03 · S1 · Foundation (+ Android CI) · open — The Release app crashes at every launch (trimmed constructor)
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

## AT-01 · S2 · Android + Foundation · open — Third-party notices leave out AndroidX, Material Components and Kotlin, which ship in the app
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

## AT-02 · S4 · Android · open — Unused MAUI Essentials components are declared in the shipped manifest
**Evidence:** `audit/manifest-xmltree.txt`: `WebAuthenticatorIntermediateActivity`, `IntermediateActivity`,
`microsoft.maui.essentials.fileProvider`, and three broadcast receivers (Essentials Connectivity, Battery, Energy Saver). All
`exported=false`, so not reachable from other apps; the app uses none of them (it has its own `SharedFileProvider`).
**Expected:** only what the app uses (smaller attack surface; nothing in a Play review that looks like connectivity monitoring).
**Fix (proposal):** `tools:node="remove"` entries in the host's `AndroidManifest.xml`. Low risk; verify Share and Open still work.

## AT-04 · S3 · Mobile UI · open — Desk header on touch still shows the desktop action row (12f, 12i; D-114)
**Steps:** phone or tablet, open a PDF, Arrange.
**Expected (12f / 12i, D-114):** desk header = name, page count, `···`; the desk actions live in the `···` menu on touch.
**Actual:** header shows the colour swatch, name, a "BM" chip, page count, ← → arrows, duplicate, `···` and delete — the desktop
row. The arrows/duplicate/delete are ~20 dp targets and the swatch 16 dp (see AT-06).
**Evidence:** `screenshots/r1/12f-vs-app.png`, `12i-vs-app.png` (API 36, R1, Debug build of the same composition).
Foundation 839d39d's message says H-16 (desk actions in the menu on touch) landed, so either it covers only the desk toolbar or it
isn't keyed on the touch form factor here.

## AT-05 · S3 · Mobile UI · open — Tablet portrait top bar has no `Document ▾` menu (12f)
**Expected (12f):** tabs · pager · `Document ▾` · search, as in landscape.
**Actual:** tablet portrait shows tabs · pager · search; `Document ▾` is gone, so Properties / Export / Compress / Merge / Split
have no entry point from the top bar in portrait. **Evidence:** `screenshots/r1/12f-vs-app.png`.

## AT-06 · S3 · Mobile UI · open — Touch targets under 44 dp (handout: 48 dp on tablet and phone)
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

## AT-07 · S4 · Foundation · open — Tabs and Home's recent cards/rows label themselves with the internal working path
The tablet tab's `title`, and the accessible name/`title` of every Home "Pick up where you left off" card (`.rcard`) and Recent
row (`.rrow`) on phone and tablet, is the working copy path, e.g. `/data/user/0/in.chuvadi.reader/cache/work/open/1429e6d5d0cd4…`
(`design/*-home.layout.json`). TalkBack reads that path aloud. Android shows `title` on long-press/hover with a mouse. **Expected:** the document's name
(or the original location the person chose), never the app's private cache path.

## AT-08 · S3 · Android · open — Status and navigation bar areas stay cream in the Night, Palm and Indigo themes
**Steps:** phone, Settings › theme Night paper (or Palm leaf / Indigo ink); look at the top (clock, signal) and the bottom
(gesture bar).
**Expected:** the system-bar areas take the theme's paper colour (as the first-paint background in `index.html` already does per
theme), with light icons on Night paper; edge-to-edge as on Windows' title bar.
**Actual:** both strips stay the cream `#F2EAD6` in every theme, so Night paper shows a cream band above a dark app bar and
below a dark bottom bar; Palm and Indigo show a mismatched band.
**Evidence:** `screenshots/r1/themes-phone-home-mark.png` (columns: Cream, Night, Palm, Indigo, High contrast).
**Fix (proposal):** `SystemBars` follows the theme (theme-changed signal → window background / `isAppearanceLightStatusBars`),
or the WebView draws under the bars and pads with `env(safe-area-inset-*)`.

## Questions for the coordinator (not filed as bugs)
- **Q-1 Same file opened again → new tab.** Opening the same PDF with Open with twelve times gave 13 tabs of `design-doc.pdf`
  (phone "13 of 13 tabs"), and Home › Recent lists `startup-doc.pdf` three times. Is that the Windows behaviour too? If Windows
  focuses the existing tab / keeps one recent entry per file, Android should match (on Android each Open with arrives as a new
  working copy, so the same document looks new each time).
