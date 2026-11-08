# Android Test — bugs

Severity: **S1** blocks release or loses data · **S2** feature broken or wrong · **S3** visible defect with a workaround · **S4** cosmetic / hygiene.
Owner: **Android** (host) · **Mobile UI** (look) · **Foundation** (shared Ui/Core, legal drafts) · **Library** (Arun) · **Coordinator** (decision).
Status: open · fixed (commit) · verified (run).

Composition under test (round 1): Foundation `839d39d` + Mobile UI `95b9d79` + Android `7ec8017`, built from clean in
run [42518447149](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42518447149) (artifact `audit`).

---

## AT-01 · S2 · Android + Foundation · open — Third-party notices leave out AndroidX, Material Components and Kotlin, which ship in the app
**Steps:** build Release; list `obj/Release/net10.0-android/android-arm64/linked/*.dll` and the dex (`audit/assemblies.txt`,
`audit/apk-contents.txt`); open About › Licences.
**Expected:** every third-party component that ships has its notice (Apache-2.0 §4(d) requires it), and the Play data-safety
basis describes the package accurately.
**Actual:** the Release app ships 29 binding assemblies with their Java code in `classes.dex` / `classes2.dex` (15.6 MB):
`Xamarin.AndroidX.*` (Activity, AppCompat, Core, Fragment, Lifecycle, Navigation, RecyclerView, ViewPager2, SwipeRefreshLayout,
CoordinatorLayout, DrawerLayout, CardView, …), `Xamarin.Google.Android.Material`, `Xamarin.Kotlin.StdLib`,
`Xamarin.KotlinX.Coroutines.Core.Jvm`, `Xamarin.KotlinX.Serialization.Core.Jvm`. They come in as MAUI's own dependencies.
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
