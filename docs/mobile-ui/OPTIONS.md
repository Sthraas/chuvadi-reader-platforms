# Mobile app UI — options and hooks for the coordinator

Each item: options with pros and cons, my recommendation, and status. Nothing below is applied to an
existing file. **Bold** = what I recommend.

---

## MU-1 How the phone shell appears — existing-file hook (MainLayout) — needs a decision
| Option | For | Against |
|---|---|---|
| **(a) H-1 in MainLayout: `@if (Shell == Phone) { <PhoneShell …>@Body</PhoneShell> } else { existing top bar…status bar }`, passing MainLayout's own `RequestMode`, `ModeDisabledReason`, `AddTab`, `FindNow`, `Go`, `OnDocView`** | No logic duplicated (the phone runs MainLayout's methods); no hidden desktop markup on a phone (no stray pager input, no window drag handler); desktop render path byte-for-byte as today | Moving between phone and tablet at run time (fold / split screen) re-parents `@Body`, so the page component remounts once (tabs, page and zoom are kept by TabsService) |
| (b) Phone shell always rendered beside the desktop chrome, CSS hides one or the other | Smallest diff | Desktop chrome still rendered (and its inputs focusable) on a phone; two sets of event subscriptions |
| (c) Separate Blazor root component registered by the Android host, zero Ui edits | No existing-file edit at all | Must re-implement MainLayout's mode switch, open, find and navigation → drift; each host must register it |

Patch for (a): `docs/mobile-ui/proposal/mobile-ui-hooks-1.patch` — **1 file, +16 lines, 0 removed**:
`<TouchSupport />` (H-2, a no-op on desktop/portal), the `@if/else` around the existing markup (not
re-indented, so the diff stays small), and one `[CascadingParameter] PlatformState? PlatformView`.
**Windows risk: none by construction** — on Desktop the `else` branch renders the same markup.
**Verified:** desktop screenshots of the unchanged foundation tree vs. this branch with the patch
applied, 1440×900 Read, 990×700 (narrow) Read, 1440×900 Arrange: pixel-identical except the live
clock seconds (`tools/mobile-ui/compare.py`). Programme solution 0 warnings; 161 + 18 + 3 tests pass.

## MU-2 The mode views' rails, drawer and cards on a phone — no hook needed
| Option | For | Against |
|---|---|---|
| **(a) Ui CSS keyed on `data-shell="phone"`**: rails fold away, the Pages drawer and Shelf become bottom sheets, settings cards become bottom sheets above the strip, desks stack and scroll sideways | Zero edits to Reader/Bench/Redact; every card keeps its own logic; the sanctioned signal (FOR-UI-CHATS §3) | CSS depends on those pages' class names — guarded by the scoping test and the screenshot run |
| (b) `@if` hooks in Reader, Bench and Redact around the rails | Rails not rendered at all on a phone | Three more existing-file edits in 4 000-line pages the Reader chat is still changing |

## MU-3 Where the strip, View sheet and FAB get their actions — no hook needed
**(a) The commands the views already register for Ctrl K, by id** (`PhoneCommands.cs`): zero edits;
a test fails if an id disappears. (b) A new "rail model" each view publishes: cleaner contract but edits
in every view. Recommend (a).
*Limitation of (a):* the strip highlights the tool you last tapped; it can't see a tool chosen another way
(keyboard, Ctrl K). Exact sync needs the Reader to publish its current tool — a small Reader hook, only if
you want it.

## MU-4 Touch gestures — no hook needed
**(a) `mobile.js` translates touch into what reader.js/bench.js already understand**: pinch → Ctrl+wheel
(the Reader's own cursor-anchored zoom), double-tap → Fit width ⇄ Fit page, swipe → next/previous page
(Read mode, page not wider than the view), tap → per-page strip (the desktop's hover strip), Arrange
long-press → replays the press to bench.js so its own drag runs; a quick swipe scrolls.
(b) Touch handling inside reader.js/bench.js: one place, but edits to two large existing files.
Recommend (a); it is verified for layout, but **the gestures still need a real-device test** (Android chat's emulator run).

## MU-5 Tablet "pen draws, finger pans" (12e) — needs a decision
Today a finger on the Mark layer draws. Options: (a) a hook in reader.js that ignores `pointerType=="touch"`
on the Mark layer when the device reports a pen (`data-input~="pen"`); (b) a capture shim in mobile.js that
swallows touch on the Mark layer and pans the desk itself. (a) is the right place but edits reader.js;
(b) avoids the edit but re-implements panning. **Recommend (a)** — I'll write the exact diff on your word.

## MU-6 Switching tabs on a phone — not designed (needs Arun)
12g shows "1 of 4 tabs" but no way to switch. Options: (a) **tap the title → a Tabs sheet** (same sheet as
View: each tab, close ×, "Open…"); (b) a Tabs section in the ⋮ menu; (c) Home only. Recommend (a).
Not built until decided.

## MU-7 Phone in landscape — not designed (needs Arun)
At 816×392 the app bar + bottom bar take 136 px of 392 (screen in `screens/`). Options: (a) keep as is;
(b) **in landscape the bottom bar drops the verbs (icons only, 56 px) and the app bar is 48 px**; (c) bars
hide while reading and return on a tap. Recommend (b). Not built until decided.

## MU-8 Phone Home, Library, Settings — not designed (handout "Open items")
Today they render inside the phone shell (app bar shows "Library"/"Settings", back → Home) with their
desktop layout, which is cramped at 392 px. Needs phone designs from Arun / Claude Design.

## MU-9 Arrange details on a phone
- The FAB is **Add desk** (12i). Protect has no FAB in 12j; **Save redacted copy** is in the redaction view's
  ⋮ → it's reachable but less visible. Option: add it as the Protect FAB (matches Mark). Recommend yes; needs Arun.
- The Shelf rests as a 52 px peek above the bottom bar; tap or swipe up opens it (handout: "Shelf as
  swipe-up sheet"). Built.
- 12f shows "‹ 2 desks ›" in the tablet counter; Bench doesn't publish a desk counter today, so the
  counter is empty in Arrange. Needs a Bench hook if wanted.

## MU-10 Title on the phone app bar
12g shows the document title ("Discharge summary — Meena R."). The Ui knows the file name only; the PDF's
own Title would need the Reader to publish it. Today: file name. Recommend keeping the file name (always
present; titles are often empty or junk) unless Arun wants the metadata title.

---

## For the Android chat (via the coordinator)
1. **Bug (Android host): `wwwroot/index.html` does not link `ChuvadiReader.Android.styles.css`.** All the
   Ui's scoped component CSS (Reader.razor.css, Bench.razor.css, cards, viewers…) is missing on Android.
   Fix: add `<link rel="stylesheet" href="ChuvadiReader.Android.styles.css" />` after `prefs.css`, as Windows does.
2. Link `_content/ChuvadiReader.Ui/css/mobile.css` after `shell.css`.
3. Remove the tablet block and the `.topbar .traffic` rule from `android.css` (now in the Ui, keyed on
   `data-shell`; Foundation's `WindowButtons` already draws none on Android), and the `body` safe-area padding
   (the Ui pads the shell itself; keeping both double-pads). `android.js`'s `data-form-factor` writer is
   superseded by `PlatformRoot` — the host should report the form factor through `IPlatformInfo.FormFactorChanged`.
4. Please register `IAppLifecycle` and raise `BackRequested`: the phone shell closes its open sheet on back.

## Possible bug in existing code (for Arun, rule 5/7)
`TabsService.RestoreAsync` (Core) appends the saved tabs without checking for tabs already open. If anything
opens a tab before the first Dashboard/Reader restore (the preview host did; a host that opens a file at
start-up through `TabsService` directly would too), the same file shows twice. Today's hosts go through
`OpenDocumentService`, which the Reader consumes after restoring, so it doesn't happen on Windows.
Fix: skip a saved path that is already open (one `if`). Low risk; marked "bug fix" for your decision.
