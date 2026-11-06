# Android — decisions

Arun has delegated design decisions and existing-file edits on the platform branches to the
coordinator; Arun keeps the final check before anything reaches `arunshivab/chuvadi-reader`.
Every option is put with pros, cons and a recommendation; the coordinator decides.

Status key: **OPEN** · **DECIDED** (date, by) · **FINAL CHECK** (Arun, before publishing).

---

## A-01 Play Store application id — FINAL CHECK
Placeholder `in.chuvadi.reader` stays (coordinator, 6 Nov). Arun (6 Nov): the publisher will be
**Sthraas Intelligence Pvt Ltd**; the Play developer account follows the company registration; the
final id is set before release from the final domain (likely `chuvadi.in`). Nothing is published
before then.

## A-02 How Android files reach the path-based Core — DECIDED (coordinator, 6 Nov)
Working copy + write-back = Foundation F-1 option C. Built in the host:
`DocumentLinks` (working path ↔ content/tree URI, persisted grants), `AndroidFilePicker` (SAF
open / create / tree), `AndroidFileWriteBack` (`IFileWriteBack`). Save and folder pickers stay
off (`AndroidFilePicker.SavePickersEnabled`) until the Ui calls `CommitAsync` after its writes —
Foundation's Group A/B Ui hooks. Until then, **Save in place writes only the working copy** on
Android; this stays on the blocker list.

## A-03 Host styling — DECIDED (coordinator, 6 Nov)
No host CSS keyed on Ui class names. Window buttons disappear through Foundation's
`ShellChrome.Buttons = None`; tablet sizing and the phone shell are built inside the Ui by the
Mobile app UI chat (`platform/mobile-ui`), keyed on `data-form-factor`. The host's `android.css`
now only pads the page for the system bars. The earlier tablet CSS (commit d945db1) was removed;
it remains in history as a reference for the Mobile app UI chat.

## A-04 Printing — DECIDED (coordinator, 6 Nov)
Android print framework with the PDF as-is (`AndroidPrintService`). Page ranges and
password-protected files: chuvadi-pdf `PageOperations.Assemble` writes the chosen pages as a new
unlocked PDF, which is printed and then deleted. Chuvadi.Print.Ipp later only if wanted.

## A-05 MAUI projects — DECIDED (coordinator, 6 Nov; Mac agrees)
Two projects (`ChuvadiReader.Android`, Mac's own), both registering through Foundation's
`AddChuvadiReader(...)`. Done: the Android host no longer keeps its own service list.

## A-06 Existing-file changes — DECIDED (coordinator, 6 Nov)
P-01 individual chuvadi-pdf packages: approved, applied centrally by Foundation. P-02 Sheets
2.0.1: waits on the Reader chat. P-03 phone hooks: Mobile app UI chat. P-04 shared host pieces:
covered by Foundation's kit.

## A-07 Phone layout — DECIDED (coordinator, 6 Nov)
Built by the Mobile app UI chat as new files in `ChuvadiReader.Ui`; this chat integrates them.

## A-08 Package feed — DECIDED (coordinator, 6 Nov)
The Reader's committed `ci/packages` feed (byte-identical to what Windows ships). Re-packing from
tag v3.31.1 only as a check.

## A-09 App icon — DRAFT DONE, FINAL CHECK
Drafted from `Brand Assets.dc.html` in `docs/android/branding/`: path-only SVG master, Play
Store 512 px icon, adaptive background / foreground / monochrome layers, the generator script and
a side-by-side with the handout. The app now uses the adaptive layers. Review sheet
`branding/icon-review.png` sent to the coordinator (6 Nov) for approval; Arun may change it before
the final release. Not drafted: the handout's Night / High-contrast variants and the small "no leaf"
sizes (≤ 32 px) — Android launchers don't use them.

## A-10 Name shown on Home — OPEN (new)
Home greets the person by name: Core's `UserProfileService.Name` uses the name set in Settings,
else falls back to the operating-system account name. On Android that is the app's sandbox user,
so the CI tablet screenshot shows "Good evening, **U0_a216**".
| Option | For | Against |
|---|---|---|
| (a) No OS-name fallback on Android: `Name` returns null (Core already handles null: greeting without a name) until the person sets one in Settings | Honest; one line; no permission. | Existing Core file (P-05). |
| (b) Device owner name from the Contacts profile | Personal. | Needs a contacts permission — against "no permissions" and the Play data-safety answer. |
| (c) Leave it | No work. | Looks broken to every Android user. |

Recommendation: **(a)**, exact diff in `EXISTING-FILE-PROPOSAL.md` P-05. (If Foundation later moves
the name to `IAccount.DisplayName`, the same rule applies there.)
