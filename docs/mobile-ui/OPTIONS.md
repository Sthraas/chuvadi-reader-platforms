# Mobile app UI — options and hooks for the coordinator

## Status of every item (7 Nov, session 3)
| Item | Decision | State on `platform/mobile-ui` |
|---|---|---|
| MU-1 phone shell hook | D-40 (a) | **Applied by Foundation** (63af90f, H-1). Follow-up: H-5 passes SwitchTab / CloseTab (`FOR-FOUNDATION.md`) |
| MU-2/3/4 CSS, command ids, touch | D-41 (a) | Built. Session 3 fixed the emulator bugs (swipe, fit flip, long-press); device re-run needed |
| MU-5 pen draws, finger pans | D-42 (a) | **Applied by Foundation** in reader.js (`penSplit`); my CSS half removed (reader.js handles it) |
| MU-6 Tabs sheet | D-43 (a) | Built; switch / close need H-5 |
| MU-7 phone landscape | D-44 (b) | Built; the off-document bar is icon-only in landscape too |
| MU-8 phone Home / Library / Settings | D-45: bar B, Home B, Library both, Settings A | **Built.** Settings A needs H-6. 7 Nov polish: every Library control ≥ 44 px (checkbox, + tag, chips, name, Search, view toggle), folder paths hidden on phone and tablet, search box fills its field. Open points below |
| MU-9 Protect FAB | D-46 | Built: Save redacted copy |
| MU-9 desk counter | D-46 | Bench's (Foundation 63af90f). Mine removed so the two don't fight; please confirm |
| MU-10 title | D-47 file name | As built |
| TabsService duplicates | D-48 | Applied by Foundation (I'd withdrawn the report in session 2; the fix is harmless) |
| Android host fixes | D-49 | Android chat |
| chuvadi-pdf 3.31.2 | D-54 | Done (in 63af90f) |
| F-4 PlatformState cascade | — | Done: TouchSupport and PhoneShell use `IPlatformInfo` + `ShellLayouts.Shell` |
| Web portal PhoneShell slot | Coordinator, 7 Nov | Done: `OpenLabel`, `OpenIcon`, `MenuFooter` (Web UI chat's request patch). The Home Open button uses `OpenLabel` too |
| Android run 42276742988 findings | Coordinator, 7 Nov | Run used pinned f29b6a6. H-8 bug fix (Document › Print / Export / Press, → counter); compose.sh and test changes for the Android chat (`FOR-FOUNDATION.md`) |
| D-88 Home search + Settings summaries | Coordinator, 7 Nov 04:55: yes to both | **H-10** (Dashboard) and **H-11** (Settings) written; desktop Home HTML byte-identical; startup +0.4 ms |
| D-89 drop zone | Coordinator: option C (Foundation words it "open" where DropFiles is false) | Nothing to build; check on phone and tablet when it lands |
| Phone over-wide page / Fit page 456 vs 342 | Coordinator: fix at the source via the combined patch | **H-9** (reader.js): the first fit was measured on the points-sized placeholder. Proven headless; the Android probe should confirm it on the device |
| MU-8 open point 3, Library Default view | Coordinator, 7 Nov: approved (leave it to the Reader chat's setting) | Nothing to build here |

### MU-8 open points (need a decision)
1. **Decided (D-88): H-10 written.** ~~Home search pill sits above the greeting**, not below the count line as in 4a. Dashboard has no
   slot there; PhoneShell puts it above the page content.
   (a) Keep it as is: no hook, and search is the first thing under the thumb.
   (b) A Dashboard hook (≈3 lines, phone only) to render it exactly where 4a has it. Matches the handout.
   **Recommend (b)** (Arun's rule: follow the handout), but it's an existing-file edit.
2. **Decided (D-88): H-11 written.** ~~Settings list rows have no one-line summary** (the mock had one under each section name).
   (a) Leave them out: no hook.
   (b) A `Summary` per entry in Settings' `Sections` table (Settings hook, ~10 lines of text).
   Recommend (b) if Arun wants the mock exactly; (a) is clean and usable.
3. **Library "Default view" is a placeholder** (Settings shows it greyed "Soon"; Library always opens
   Table), so the phone opens with List.
   (a) Keep it until the Reader chat builds the setting; the phone follows it automatically then.
   (b) A phone-only hook in Library to open with Shelf.
   **Recommend (a)**: it matches D-45 ("phone opens with Settings › Default view").
4. **Redaction view on a phone**: decided (coordinator, 7 Nov): fit width on phones. Hook H-7
   written (`FOR-FOUNDATION.md`), for Foundation's next combined patch.
5. **Phone landscape, Arrange Shelf: my choice, kept (coordinator, 7 Nov).** Lifting a page out of the
   open Shelf drops the sheet back to its peek, so the desks it covered (all of them in landscape) can
   take the drop. The handout doesn't show this; I chose it because otherwise a Shelf page can't reach a
   desk in landscape.
6. Tablet desk counter reads "1 / 1 desks" (no singular). Bench's counter text; cosmetic.

---

## Original options (6 Nov, morning) — kept for the record

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
