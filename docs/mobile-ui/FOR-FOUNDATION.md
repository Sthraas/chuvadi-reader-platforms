# Mobile app UI → Foundation: hooks for the combined patch (D-26)

Branch `platform/mobile-ui`, up to date with `platform/foundation` **be4498a** (chuvadi-pdf 3.31.2).
The patches were generated against 60dca85; MainLayout and Reader.razor are unchanged since, and they
apply cleanly to be4498a with `git apply` (re-checked). They are **not** applied on
`platform/mobile-ui`; `tools/mobile-ui/preview.sh` applies them in a scratch copy for testing.

| Patch | File | Decision | Lines |
|---|---|---|---|
| `proposal/H1-mainlayout-phone-shell.patch` | `Ui/Layout/MainLayout.razor` | D-40, D-41, D-43 | +19 / −0 |
| `proposal/H3-reader-pen-finger.patch` | `Ui/Pages/Reader.razor` | D-42 | +3 / −0 |
| `proposal/mobile-ui-hooks-2.patch` | both of the above, concatenated | — | — |

Hosts must also link `_content/ChuvadiReader.Ui/css/mobile.css` after `shell.css` (Android chat, D-49).

## H-1 — phone shell and touch (MainLayout)
- `@if (Kind != Windows && FormFactor != Desktop) { <TouchSupport /> }` — pinch, double-tap, swipe,
  tap-for-strip, Arrange long-press, tablet desk counter.
- `@if (FormFactor == Phone) { <PhoneShell …>@Body</PhoneShell> } else { …existing top bar → status bar… }`.
  PhoneShell gets MainLayout's own `RequestMode`, `ModeDisabledReason`, `AddTab`, `FindNow`, `Go`,
  `OnDocView`, `SwitchTab`, `CloseTab` — nothing is re-implemented (close still asks about unsaved changes).
- The existing markup is wrapped, not re-indented, so the diff stays small.
- Gates read plain properties (`Platform.Kind`, `Platform.FormFactor`), not the `Shell()` extension,
  so Windows JITs nothing new. `FormFactor == Phone` ⇔ `Shell() == Phone` by `ShellLayouts.From`.

## H-3 — tablet pen draws, finger pans (Reader.razor, `MkDown`)
```csharp
if (!_markup || e.Button != 0) return;
// Tablet with a pen (Portal & Android 12e): the pen draws, a finger pans (mobile.css lets it).
if (Platform.FormFactor == ChuvadiReader.Platform.FormFactor.Tablet && e.PointerType == "touch"
    && Platform.Input.HasFlag(ChuvadiReader.Platform.InputKinds.Pen)) return;
```
**Correction to my MU-5 note:** the Mark-layer drawing is Blazor `@onpointerdown="MkDown"` in
`Reader.razor`, not `reader.js`. Same decision (a hook in the drawing code on the pointer type), one
line, in the right file. The CSS half (`touch-action: pan-x pan-y` on `.mk-layer` for
`html[data-shell="tablet"][data-input~="pen"]`) is in `mobile.css`, no hook.
Keyed on `FormFactor == Tablet` so a Windows Surface with a pen is unchanged.

## Not needed any more
- **D-46 Bench desk-counter hook:** done with **no** existing-file edit. `ShellService.CounterHandler`
  is public; `TouchSupport` (tablet only) publishes "desk n / N" while Arrange shows (Bench publishes no
  counter there) and scrolls to the desk; `mobile.css` adds the word "desks". Coordinator: if you'd still
  rather Bench own its counter (clearer ownership), say so and I'll write that diff — cost: Bench.razor +
  Bench.Shell.cs edits and a bench.js export.
- **D-48 TabsService restore de-duplication: please don't apply — my report was wrong.** A test showed
  `OpenAsync` persists at once, so opening before the first restore *replaces* the saved session (earlier
  tabs dropped, no duplicate), and the de-dup changes nothing. The duplicates I saw came from my preview
  host calling `TabsService` directly before restore. Real hosts hand files over through
  `OpenDocumentService.Request`, which the Reader takes only after restoring — so no bug on any host.
  Host rule instead (for the Android chat's share/open intents): **always use `OpenDocumentService`,
  never `TabsService.OpenAsync`.**

## Evidence (hooks applied in a scratch copy of 60dca85 + this branch)
- Programme solution: **0 warnings, 0 errors**; tests **161 + 27 + 4 pass**.
- **Desktop pixel-identical** (unchanged 60dca85 vs. with H-1 + H-3): Read 1440×900, Read 990×700,
  Arrange 1440×900, Mark 1440×900 — only the live clock seconds differ (`tools/mobile-ui/compare.py`).
- **Startup (Windows profile, `tools/StartupProbe`, published Release, 25 interleaved runs):**

  | | services | first render | total | JIT methods | assemblies |
  |---|---|---|---|---|---|
  | 60dca85 | 20.1 ms | 150.7 ms | 196.6 ms | 1,415 | 43 |
  | + H-1 + H-3 | 20.2 ms | 150.9 ms | 198.8 ms | 1,416 | 43 |

  +1 method, +2.2 ms total — inside your 7 ms A/A noise floor. Rendered HTML identical to 60dca85
  apart from one whitespace text node (scoped-CSS hashes unchanged).
- Contract tests (`tests/ChuvadiReader.MobileUi.Tests`) fail if a command id the phone uses disappears,
  if a `mobile.css` rule isn't scoped to tablet/phone, or if MainLayout's pager loses the
  `aria-label="@Shell.CounterUnit number"` the desk label keys on.
