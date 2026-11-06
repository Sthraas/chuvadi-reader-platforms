# MU-8 / D-45 — phone Home, Library, Settings: two options each

Mock screenshots: `docs/mobile-ui/mocks/` (`home-options.png`, `library-options.png`,
`settings-options.png`: today | A | B). Source: `mocks/phone-screens.html` (handout tokens, fonts
and LiPicons; content uses the app's real theme names, setting labels and section icons).
**Nothing here is built yet.**

The handout already has a phone Home: `Chuvadi Mobile.dc.html` frame **4a** (copied as
`mocks/reference-chuvadi-mobile-4a.png`). DESIGN-NOTE supersedes only that file's *tablet* frames,
so 4a is still a valid reference — and Arun's rule is "everything else follows the design handout".

What today's build does on a phone (left column of each overview): usable, but Home leads with a
drop zone (nothing to drag on a phone), Library's chips wrap to three rows before any document, and
Settings' section nav takes six rows before Appearance starts.

---

## The shared question first: which bottom bar off-document?
It decides Home A vs B, and applies to Library and Settings too.

| | **A — one bar everywhere (as built)** | **B — 4a's destination bar off-document** |
|---|---|---|
| Bar on Home / Library / Settings | Read · Mark · Arrange · Protect (12g) | Home · Library · Tabs · N · Settings (4a) |
| Bar in a document | same | Read · Mark · Arrange · Protect (12g) |
| Library / Settings | ⋮ menu (2 taps) | 1 tap |
| For | One bar to learn; exactly 12g; already built; modes reopen the active tab from anywhere | Follows the handout's own phone Home (4a) exactly; standard Android split (destinations vs. actions on a document); Tabs reachable everywhere with its count |
| Against | Library/Settings two taps away; with no tab open the four modes are all greyed on Home | The bar changes under the thumb when a document opens (4a and 12g were drawn that way); one more small component (~60 lines) and a rule for which bar shows |

**Recommendation: B** — it is the handout's design (4a + 12g together), and Arun's rule says follow
the handout. The extra cost is small and it is new-file work (no new hook: the H-1 shell decides
the bar from `OnDocView`, which it already receives).

## Home
| | **A** | **B** |
|---|---|---|
| Layout | 4a content (greeting + வணக்கம், count line, search, resume cards sideways, Recent, Pinned), extended **Open** FAB; 12g bar | Same content; avatar in the app bar (4a); 4a's destination bar |
| Dropped from desktop | The drop zone (no drag on a phone — the Open FAB replaces it); the clock eyebrow (the system bar has the time) | same |
| Kept below the fold | Pinned, Library shelf preview, Watched folder (desktop's right panel), in that order | same |
Pros/cons are the shared question above. **Recommendation: B.**

## Library
The existing Library already has a **Table / Shelf** toggle and a real setting for it
(Settings › Library & folders › *Default view*). So the phone needs **both** layouts whatever is
chosen; the only open choice is which one a phone opens with.

| | **A — List first** | **B — Shelf first** |
|---|---|---|
| Layout | Search; one row of category chips (sideways scroll, "All · N" first); List / Shelf; one-line rows with a mono meta line (category · pages · age · signed / encrypted) and ⋮ | List / Shelf; one shelf per category with wooden bookend and books sized by page count, each shelf scrolls sideways; search in the app bar |
| For | ~7 documents per screen; search and filter first; names fully readable; matches the desktop default (Table) | Keeps the Library's signature look; category is the primary grouping |
| Against | The shelf look is one tap away, not first | Rotated names are hard to read at phone size; ~10 books per shelf visible; search is a tap away |

**Recommendation: build both views (both are needed by the toggle); a phone opens with whatever
*Default view* says (its default is Table → List).** No new setting.

## Settings
| | **A — Section list, tap pushes the section** | **B — One page, sticky section chips** |
|---|---|---|
| Layout | 10 rows (real section icons), each with a one-line summary of what is inside; tap opens the section full-screen with ← | Chips across the top (scroll sideways, jump to a section); all sections on one long page |
| For | Standard Android settings pattern; every section one tap; Android back steps out of a section; scales as sections grow | Browse everything by scrolling; no extra screen |
| Against | Two taps to reach a setting | 10 sections make a very long page; most chips are off-screen; back can't step out of a section |

**Recommendation: A.**

## Found while making these (existing files — for the Foundation / platform text)
- Settings text says "computer" where Android needs "phone" / "device": Appearance › *Follow the
  computer's light / dark setting*, Language › *Preferred name* hint ("your computer's name"). These
  belong with `PlatformText` (Foundation). Not changed here.
