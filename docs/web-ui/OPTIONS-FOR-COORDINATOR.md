# Web portal UI — options and questions for the coordinator

## Decided (6 Nov: D-31 to D-39, then U-9 to U-11 and F-2 to F-4 at 23:54) — how each was applied on `platform/web-ui`
| Item | Decision | Applied |
|---|---|---|
| U-1 | D-31: pitch and status keep "encrypted at rest"; promise 1 "Files live only for your session, then are wiped"; promise 3 "Sign out and your files are gone from the server" | Done in `PortalSignIn`; icons as designed; test pins the three lines |
| U-2 | D-32: narrow browsers reuse Mobile UI phone/tablet components + portal additions | Tablet: `AccountMenu` sizes for `data-shell="tablet"`; H1–H4 apply as is. Phone: `PortalPhoneAccount` (account block for the ⋮ sheet) + H5 + a slot request to Mobile UI (HOOKS §2) |
| U-3 | D-33: desktop component, hook deferred; gating list as the handout | No change (list keeps "Sync across devices"); hook stays in "Later hooks" |
| U-4 | D-34: Sangam ID as login hint, no password field | Password field and "Forgot?" removed; `OnSubmitId` hands over the ID as typed. **Sangam check → U-9** |
| U-5 | D-35: Account settings → Sangam's page; desktop-app URL is config, placeholder https://chuvadi.in/download; `IAccount.Unit` by the Foundation | `PortalLinks(DesktopAppUrl, AccountSettingsUrl)`, `PortalLinks.PlaceholderDesktopAppUrl`. "· Unit" in `AccountMenu` (Foundation) and in `PortalPhoneAccount` (session 3) |
| U-6 | D-36: keep theme toggle and version | Nothing to do |
| U-7 | D-37: blue server dot | Applied by the Foundation (hook + `shell.css`); `portal.css` dropped; `PortalPhoneAccount` uses the same two colours |
| U-8 | D-38: one position | As built |
| F-1 | D-39: divider fix in the Foundation's combined patch | Nothing to do here |
| U-9 | Coordinator 6 Nov 23:54: (a) only "Continue with Sangam" + the desktop-app line; (c) goes to Arun as a Sangam ask | `PortalSignIn.ShowSangamIdDefault = false`; the field and `OnSubmitId` stay in the component for (c) — the host sets `ShowSangamId="true"` if Arun agrees |
| U-10 | (a) account block at the foot of the phone ⋮ sheet | As built; slot request + H5 regenerated against 63af90f (HOOKS) |
| U-11 | (a) the Foundation adds both Home lines to the Web wording in its combined patch | Nothing to do here |
| F-2, F-3 | Approved bug fixes for the Foundation | Nothing to do here |
| F-4 | Passed to the Mobile UI chat | Nothing to do here (their files on foundation already use `IPlatformInfo`) |
| U-13 | Coordinator 7 Nov 01:34: (a) plain "Terms of use" link; (b)/(c) to Arun with the portal Terms of Use and privacy notice; static `/terms` approved (Web chat) | As built (session 4). The EULA draft (`legal/EULA.txt` on foundation a4acc56) says "By installing, copying or using the software you agree to it", which fits (a). Note: that draft is written for the installed app (and forbids offering it "as a hosted service to others"); the portal's own Terms of Use is the separate document already with Arun |
| D-75 | Phone account block (H5), Portal status-bar spans, two-argument `PortalLinks` | Mobile UI's slot is on `platform/mobile-ui` 1a27cd6 — identical to my request; H5 compiles and works against it (session 5). Portal files are on foundation |

## ✔ decided — U-9 `login_hint` — Sangam does not pre-fill it (D-34 asked me to report)
Checked `arunshivab/sangam` main **d43a5ff** (1.0.0-rc.16), read only:
- `/connect/authorize` (OpenIddict 7.7.2) accepts `login_hint` — it is a standard parameter, and Sangam's own review lists it as accepted (`docs/security/cache-and-parameters-review.md:31`).
- But **nothing reads it**: the authorize endpoint redirects to `/login?returnUrl=<whole authorize URL>` (`ConnectEndpoints.cs:105`), and `Login.cshtml.cs` `OnGetAsync` (89–125) only pre-fills `Identifier` from its own in-progress sign-in cookie. No code under `src/` or `tests/` mentions `login_hint`. So an ID typed on our page would have to be typed again on Sangam's.
- The password route (U-4 b) is not possible either: Sangam enables authorization code, refresh, client credentials, device and token exchange flows only (`Program.cs:171–177`) — no password grant.
- The Web chat reached the same finding independently (`docs/web/SANGAM-INTEGRATION.md`, S-02).

Options:
- **(a) Show only "Continue with Sangam"** (+ the desktop-app line); Sangam asks for the ID on its own screen. Pros: honest; one step; no Sangam change; nothing to build (the Web host passes `ShowSangamId="false"`). Cons: departs from 12a (no ID field).
- **(b) Keep the field and send `login_hint` anyway.** Pros: exactly 12a; starts working the day Sangam pre-fills. Cons: today the person types their ID twice — looks broken.
- **(c) Ask Arun for a small Sangam change**: pre-fill `Identifier` from `login_hint` in the returnUrl (a few lines in `Login.cshtml.cs`). Pros: 12a works as designed. Cons: Arun's rule is "never change Sangam" — his decision only.

Recommendation: **(a) now**, and put **(c)** to Arun as an ask (it would let us restore the field with no Ui change: the component already has it). Same as the Web chat's S-02.

## ✔ decided — U-10 Where the portal account block sits in the phone ⋮ sheet
Built at the **foot** of the sheet (slot `MenuFooter`). On Home/Library/Settings it is visible without scrolling; on a document view it is under the Document rows (~15), so it needs a scroll (`screenshots/chromium-phone-reader-menu.png` vs `…-menu-account.png`).
- **(a) Foot (as built).** Pros: Android convention (account and Sign out last); one slot in PhoneShell. Cons: a scroll on document views.
- **(b) Identity at the top, rows at the foot.** Pros: who is signed in is always visible. Cons: two slots in Mobile UI's PhoneShell; pushes Upload/Find down.
- **(c) Top, everything.** Cons: Sign out is the first thing a thumb reaches.

Recommendation: **(a)**.

## ✔ decided — U-11 Home lines that are untrue on the portal (existing Ui text, not mine)
Seen in the preview at every Web size (`screenshots/chromium-phone-home-menu.png`):
- Home summary (`Pages/Dashboard.razor:32`): "0 documents in your library · 1 encrypted · **nothing leaves this device**".
- Drop zone (`Dashboard.razor:52`): "Drop a document, or **click to open**".

D-20 reworded the other device-only lines; these two were not covered. Options: (a) the Foundation adds them to the same Web wording in the combined patch (e.g. "… · processed on the Chuvadi server · removed when you sign out" and "click to upload"); (b) leave. Recommendation **(a)** — wording for Arun, as with D-20.

## Findings for other chats (existing code; not touched) — F-2/F-3 → Foundation, F-4 → Mobile UI (decided)
- **F-2 (Reader chat / Foundation):** Home greets "Good morning, Arun S.." — the template (`Pages/Dashboard.razor:252`, `$"Good {part}, {Profile.Name}."`) adds a full stop after a name that already ends with one. The name is data and stays as it is; the fix is in the greeting (skip the full stop when the name ends with "."). Cosmetic.
- **F-3 (Web chat, then Reader chat):** `OpenDocumentService` holds **one** pending path. Two `Request(...)` calls before the Reader consumes the first leave one tab named after the second file showing the first file's pages. Windows only ever requests one (`MainWindow.xaml.cs:83`, `supported[0]`), so desktop cannot hit it today. The Web host's upload must not call `Request` once per file for a multi-file upload; the Reader chat may want to harden the service (queue or ignore while pending).
- **F-4 (Mobile UI chat, FYI):** their hook H-1 and `TouchSupport.razor` still use the `PlatformState` cascade the Foundation removed (startup rule). `IPlatformInfo` + `ShellLayouts.Shell(...)` works — tested locally while checking H5.

## U-12 Web chat: one-line change when this branch lands (routine, no options)
`platform/web` 4761662 builds `PortalLinks(o.DesktopAppUrl, …AccountSettingsUrl, …ForgotPasswordUrl)` — the session-1 shape from the combined patch. With D-34 there is no password field and no "Forgot?" link, so this branch's `PortalLinks` has two arguments. The Web chat drops the third argument (and `PortalOptions.ForgotPasswordUrl` / its appsettings key). Kept as a breaking change on purpose: a dead parameter would suggest a feature that does not exist. (Session 4 adds an **optional** third argument, `TermsUrl` — U-13 — so the two-argument call stays valid.) Nothing else the Web host calls changes (it does not render `PortalSignIn` yet; when it does: `OnContinueWithSangam`, optional `OnSubmitId`, `Busy`, `Error`).

## ✔ decided — U-13 Terms of use on the sign-in page (coordinator 7 Nov: link the terms if 12a has room)
**Room: yes.** With U-9 (a) the card lost the ID field and its Sign in button, so it is about half its designed height. Built: one line under "Download the desktop app" — **"Terms of use"** linking to `PortalLinks.TermsUrl` (new, optional, default null → the line is hidden; the Web chat's two-argument call still compiles). Screenshots: `screenshots/webkit-desktop-signin.png`, `firefox-phone-signin.png`. About is not needed for the portal; the desktop's About is the Foundation's (it adds LICENSE/EULA).

Open choice — the wording (legal, Arun's):
- **(a) "Terms of use" link only** (built). Pros: makes no legal claim; smallest change to 12a. Cons: no recorded acceptance — a portal user is bound only if the EULA itself says use means acceptance.
- **(b) "By continuing with Sangam you accept the Terms of use."** Pros: the usual click-through form; acceptance tied to the sign-in action. Cons: a legal statement Arun must approve; one more sentence on the card.
- **(c) A checkbox before "Continue with Sangam".** Pros: strongest record of acceptance. Cons: friction on every sign-in; nothing in 12a; for free software rarely needed.

Recommendation: **(a)** unless Arun's EULA requires explicit acceptance, then **(b)** — a one-line text change. Also needed: the EULA's URL. The Web chat serves the Foundation's EULA (suggest `/terms`, a static page, readable signed-out) and passes it as `TermsUrl`.

## ✔ decided (a) — U-14 Settings › Account says "Not signed in" on the portal
Built in session 6: `PortalAccountRows` + `proposal/web-ui-hooks-4-account.patch` (see HOOKS).

On the portal the person is always signed in with Sangam, but `Components/Settings/AccountSection.razor:7–10` shows **"User: Not signed in"** and **"Sign in with Sangam"** (desktop placeholders for the future Sangam sign-in). It is reached from Settings on every portal size, and on a phone it is **where the Home avatar ("AS", Mobile UI's new phone Home, D-61) leads** (`/settings?section=account`) — so on phone Home the account button opens a page that says you are not signed in and has no Sign out. (Sign out is reachable from the ⋮ sheet on Library, Settings and document views; Home has no ⋮.) Screenshot: `screenshots/phone-home-account.png`.

Options:
- **(a) On the portal, the "Signed in" card shows the real account** — name, Sangam ID · Unit, "Account settings" (Sangam's page), Sign out — via a new component of mine (`PortalAccountCard`, same rows as `PortalPhoneAccount`) and a one-line hook in `AccountSection` (`@if (Platform.Chrome.AccountMenu) { <PortalAccountCard /> } else { …existing card… }`), Foundation's combined patch. Roles / Audit trail / sign-in method / lock rows stay as they are (they are desktop features, marked "new"). Pros: fixes the untrue lines on every portal size; the phone avatar lands on a truthful page with Sign out; desktop untouched (`AccountMenu` false). Cons: one more hook in an existing file.
- **(b) The phone Home avatar opens the account sheet instead of Settings** (Mobile UI change: PhoneShell `OnAccount` override, or the avatar opens the ⋮ sheet with `MenuFooter` when set). Pros: one tap to Sign out on phone Home. Cons: Settings › Account still says "Not signed in" on every portal size; touches Mobile UI's files.
- **(c) Both.** Pros: most direct on phone, truthful everywhere. Cons: two changes in two chats' files.

Recommendation: **(a)** — it fixes the false statement at its source and makes the avatar's existing route correct, with one hook. Also hide the portal-irrelevant rows? Not proposed: they are design-time desktop features and not untrue, only inapplicable; if the coordinator wants them hidden on the portal, it is the same hook.

## W — exact wording for the Foundation's `PlatformText` (coordinator 7 Nov: O-1 to O-3 go to the next combined patch)
Desktop (Windows / Mac / Linux) keeps every string character for character. Each proposal says on which platforms it changes.

| # | Where | Today | Proposed | Applies to |
|---|---|---|---|---|
| W-1 (O-1) | Library empty state, `Pages/Library.razor:105` (the "Nothing matches these filters." branch unchanged) | "No PDFs in Chuvadi Documents yet. Drop files into a category folder to see them here." | **"No PDFs here yet. Use Upload to open documents. Files are removed when you sign out."** | Web (`Capabilities.ServerSide`), every size |
| W-2 (O-2) | Settings › Appearance toggle, `PlatformText.FollowSystemTheme` | "Follow the computer's light / dark setting" | **"Follow the browser's light / dark setting"** | Web, every size (Android keeps "phone's" / "device's") |
| W-3 (O-2) | Settings › Language › Preferred name hint, `PlatformText.PreferredNameHint` | "Leave blank to use your computer's name. Stored locally, never sent anywhere." | **"Leave blank to use your Sangam name. Kept until you sign out."** | Web |
| W-4 (O-3) | Home tip, `Pages/Dashboard.razor:62` | "Tip: Ctrl K finds any file or action. Try typing “merge”." | **"Tip: tap “Find or do anything” to reach any file or action. Try typing “merge”."** | Phone layout (Web phone and Android phone); tablets and desktop keep the Ctrl K tip |

Why each is true:
- W-1: the portal has no category folders; "Use Upload" names the portal's own button (H2) and does not depend on whether the Home drop zone works (D-78 is still open); "removed when you sign out" is the D-31 / `HomeServerLine` promise. It also stays true whether or not uploaded files appear in the Library (that is the Web chat's detail: the session's "Chuvadi Documents" is the download outbox).
- W-2: on the portal the theme can only follow the browser (which follows the device); it is the browser's setting the page can read.
- W-3: on the portal the default name is the Sangam display name (Web H6: account name first). Settings live in the session's memory today (`SessionAppStorage`); D-29 moves only *appearance* settings to browser storage, so the name is kept until sign-out either way. "Never sent anywhere" is not true on a server.
- W-4: phones have no Ctrl key; "Find or do anything…" is the phone Home search box (Mobile UI 4a, `PhoneShell.razor:28`) that runs the same command bar. Keyed on the phone layout, not on input: the Android host always reports a keyboard (`AndroidHostServices.cs:30`), so input flags cannot tell.

Suggested code (the Foundation's file, for its convenience):
```csharp
public static string FollowSystemTheme(IPlatformInfo platform) =>
    platform.Kind == PlatformKind.Web
        ? "Follow the browser's light / dark setting"
        : $"Follow the {DeviceNoun(platform)}'s light / dark setting";

public static string PreferredNameHint(IPlatformInfo platform) =>
    platform.Kind == PlatformKind.Web ? "Leave blank to use your Sangam name. Kept until you sign out."
    : platform.Kind == PlatformKind.Android
        ? $"Leave blank to show no name. Stored on this {DeviceNoun(platform)}, never sent anywhere."
        : "Leave blank to use your computer's name. Stored locally, never sent anywhere.";

/// <summary>Library empty state (no filters).</summary>
public static string LibraryEmpty(IPlatformInfo platform) =>
    platform.Capabilities.ServerSide
        ? "No PDFs here yet. Use Upload to open documents. Files are removed when you sign out."
        : "No PDFs in Chuvadi Documents yet. Drop files into a category folder to see them here.";

/// <summary>Home tip: phones have no Ctrl key.</summary>
public static string CommandTip(IPlatformInfo platform) =>
    ShellLayouts.Shell(platform) == ShellLayout.Phone
        ? "Tip: tap “Find or do anything” to reach any file or action. Try typing “merge”."
        : $"Tip: {platform.Keys.Format("Ctrl K")} finds any file or action. Try typing “merge”.";
```
(`Dashboard.razor:62` then renders `<p class="tip">@PlatformText.CommandTip(Platform)</p>` — same markup on desktop.)

## Observations on the portal for other chats (existing text; not touched) — now W-1 to W-4 above
- **O-1 (Foundation, Web wording like U-11):** Library empty state "No PDFs in Chuvadi Documents yet. Drop files into a category folder to see them here." (`Pages/Library.razor:105`) — the portal has no folders.
- **O-2 (Foundation, `PlatformText`):** Web gets "computer" everywhere (`DeviceNoun` is "computer" for every non-Android kind): a phone browser shows "Follow the computer's light / dark setting" — on the portal it follows the browser's setting; and `PreferredNameHint` says "Leave blank to use your computer's name. Stored locally, never sent anywhere." — on the portal the name comes from Sangam and the setting is in browser storage (D-29). Suggest: Web → "Follow the browser's light / dark setting"; hint → "Leave blank to use your Sangam name. Stored in this browser."
- **O-3 (Mobile UI / Foundation):** phone Home tip "Tip: Ctrl K finds any file or action" (`Dashboard.razor:62`) on a touch phone with no keyboard — on Web phone and Android phone.

## ✔ decided (a), D-97 — built session 9 — U-15 Terms of use and Privacy from the account menu (coordinator 7 Nov 04:55: "propose one if the handout has no place")
**12a (sign-in): built.** "Terms of use · Privacy" on one line under the desktop-app line (`PortalLinks.TermsUrl`, new optional `PortalLinks.PrivacyUrl`; each hidden when null). The Web host passes `"/terms"` and `"/privacy"` (the Foundation's `Licence` page, served before sign-in).

**12b (account menu): the handout has no place for them.** The card holds the person, the storage meter (out of scope), My files / Shared with me (out of scope), Get the desktop app, Account settings, Sign out. Options:
- **(a) A small footer line at the bottom of the card, under Sign out: "Terms of use · Privacy"** (12 px, muted, same style as the 12a line). Same line at the foot of the phone account block (`PortalPhoneAccount`). Pros: one click from anywhere while signed in; matches 12a; adds no menu row, so the actions keep their weight; keeps the DPDP notice "readily accessible". Cons: a small departure from the 12b frame.
- **(b) Two menu rows ("Terms of use", "Privacy") between "Account settings" and "Sign out".** Pros: same look as the other items; bigger touch targets on phones. Cons: legal links compete with the real actions; the card grows by two rows (on a phone the ⋮ sheet is already long on document views).
- **(c) Nothing in the menu; rely on Settings › About › Licences**, which already shows the licence agreement and (on the portal) the terms and privacy texts. Pros: no change. Cons: three taps deep; a person looking for "privacy" will not think of "Licences".

Recommendation: **(a)**. Not built until decided (it touches `AccountMenu`, which the Foundation edited for Unit — I would send the change as a small diff on its current copy).

## ✔ decided (a), D-103 — done session 10 — U-16 The 12a sign-in pitch still says "encrypted at rest" (D-98 follow-up)
D-98 changed the status bar (and the draft Terms) because, under D-28, documents live only in memory and memory itself is not encrypted. The same claim is in the 12a pitch (`PortalSignIn`, D-31 kept it): "…On the portal, files are processed on our server, **encrypted at rest**, and visible only to you." Not changed yet — the decision named only the status bar.
- **(a) Same wording as D-98:** "…On the portal, files are processed on our server, **kept in memory only**, and visible only to you." Pros: true; matches the status bar and the promises ("Files live only for your session, then are wiped"). Cons: departs from the handout text (as D-98 already does).
- **(b) Drop the clause:** "…files are processed on our server and visible only to you." Pros: shortest. Cons: loses a reassurance that is true.
- **(c) Keep as is.** Cons: untrue under D-28 — the same reason D-98 gave.

Recommendation **(a)** — a one-word-group change in my file, ready as soon as you say.

## ✔ decided (b), D-104 — diff sent session 10 — D-89 Home drop overlay — checked (Foundation's `PortalDropCatcher`, on foundation since the fifth patch)
Behaviour is right: catches only file drags (`types` includes "Files"), lets image-only drags through to the Reader, never lets the browser open a dropped file, clears on drop, `dragend` and window blur, and is rendered only on the portal (`IsPortal && DropFiles`; desktop and Android never). Multi-file: up to 64 per drop, the rest reported.
**One gap against the handout:** the catcher is **invisible by design** ("nothing to see — the desktop window shows nothing either"), but the handout draws a drag-over state (Walkthrough "Drop to open": dashed 2 px binding border inset 24 px, radius 14, light wash, upload icon, "Drop to open" in Instrument Serif 28 px). Options:
- **(a) Keep it invisible.** Pros: same as the desktop today; nothing to build. Cons: on the web there is no sign that the page — not the browser — will take the file, until it opens.
- **(b) The portal shows the handout's overlay while files are dragged** (the catcher already toggles an `on` class; the visual is CSS + one icon and one line, no new logic), without the file-name line (browsers don't expose names before the drop). Pros: matches the handout; clear feedback where it matters most. Cons: portal differs from desktop until the desktop gets the same.
- **(c) Both portal and desktop.** Cons: desktop needs work in the Windows host (WebView drop), outside this chat.

Recommendation **(b)**. It is the Foundation's component; I can send the CSS + markup as a diff for it if you prefer.

## U-17 "Drop to open" over Home's own drop zone — **decided (b), D-109**
The handout draws "Drop to open" over a document. On **Home**, the page already has its own drop zone in the middle ("Drop your first document here", States 8b), so while a file is dragged the overlay's icon and title sit on top of the zone's icon and title, seen through the 55 % wash — two upload icons, two titles (`screenshots/chromium-drop-over.png`; in Night paper the Home zone also shows its own drag highlight, `webkit-drop-over-dark.png`). Elsewhere (Library, Settings, a document) it reads cleanly.
- **(a) Keep as built** — exactly the handout's panel everywhere. Pros: literal handout; no more change. Cons: the doubled text on Home, where people drop most.
- **(b) While a drag is on, Home's drop zone hides its own contents** (the zone's frame stays): `portal-drop.js` also toggles a class on `<html>` (e.g. `chvd-dragging`), and one CSS rule in the Home styles hides `.dropzone > *` under it. Pros: one clean "Drop to open" everywhere; the handout's panel unchanged; desktop untouched (the class is only set by the portal script). Cons: touches the Foundation's script and the Home styles (two more small diffs).
- **(c) No overlay on Home** — Home keeps 8b's zone as the visible target. Pros: uses the designed 8b state there. Cons: the drop is still caught full-window, so the visible target and the real one differ; inconsistent between pages.

Recommendation **(b)**. **Decided (b), D-109** — sent to the Foundation as `proposal/web-ui-home-drop-zone.patch` (HOOKS).

## D-54 (chuvadi-pdf 3.31.2) — what I will check when the Foundation's overlay lands
Handout references: **Walkthrough "Drop to open"** (drag-over state) and **States & Feedback 8b** ("Home with nothing yet").
1. Drag-over overlay: full window, **inset 24 px**, **2 px dashed** border in the binding colour (`#8a3a1c` in Cream), **radius 14 px**, background `rgba(251,247,236,.55)` (theme-tinted in the other themes), upload icon in the binding colour, **"Drop to open"** in Instrument Serif 28 px.
2. **Heads-up:** the handout's second line ("scan-lab-0931.pdf · 1 page · from the scanner folder", IBM Plex Mono 12 px) **cannot be shown before the drop in a browser** — `DataTransfer` exposes no file names or contents during `dragover` (only after `drop`; Chromium gives types at most). Suggest: no second line during drag on the portal, or a type-only line ("1 file") where the browser gives a count; the file name can show in the upload progress after the drop.
3. 8b on the portal: icon, "Drop your first document here", sub-line, and the buttons — with the portal's Upload wording (W-1 / D-89 C) rather than "Open a file…" / "Choose a library folder" (no folders on the portal).
4. The overlay must not appear for drags that are not files (text, links) and must clear on `dragleave` out of the window and on Escape.
5. Dropping several files opens each in its own tab (D-83); a non-supported type shows the 8e-style "Can't open" message, not a silent no-op.
6. Phone and touch tablet: no drag-over state (no drag source); the 8b zone acts as the Upload button.
7. Desktop (Windows profile) pixel-identical; Android keeps option B wording.

## D-54 (chuvadi-pdf 3.31.2)
Landed on `platform/foundation` (be4498a) during this session; `platform/web-ui` is rebased onto it and re-checked (BUILD-LOG session 2 §7).

## ✔ decided (c) — Q-3 / D-119 Home wording on the portal (coordinator 02:30, confirmed 03:07)
"Files in this session" for the Storage map heading, and "Nothing shelved this session — open the Library" for the empty shelf. The example line, "Your shelves for this session are empty — …", wraps to two lines, which would be a layout change, so I used the shorter line that keeps the "this session" wording and the layout. The diff went to the Foundation (HOOKS). The hide-on-Web version was prepared and then dropped.

## ✔ decided (b), D-187 — U-18 "Sign with certificate" is live on the portal since patch 26 (found 11 Nov) — D-27 says "off now"
Diff sent to the Foundation: `proposal/web-ui-portal-certificate-off.patch` (HOOKS). Rail word settled 16 Nov 00:40: "soon", as every other greyed rail item on the portal shows.

**What changed.** Windows PR 15 (chuvadi-pdf 3.32.0, real signing) removed `DisabledReason = CertificateSignService.WaitingReason` from the three places the action appears: the Reader's Protect rail, Redact's Tools rail, and the Ctrl K command "Sign with certificate". Until then it was greyed out on every platform only because the library wasn't ready. No capability flag covers signing, and the 12c `SangamGate` was never hooked (`EDITS-FOR-APPROVAL.md` line 82).

**What a portal user sees now** (preview, Web profile; `screenshots/chromium-portal-sign-with-certificate.png`): an enabled "Sign with certificate" button, and a card with "Choose certificate (.pfx)…", "Certificate password" and "Save signed copy". On the real Web host the picker returns nothing (`PortalOptions.AllowCertificateUpload` is false by default, W-08), so no private key reaches the server and the security side of D-27 (a) holds. But the button looks live and does nothing.

**Options** (shared Ui files, so whichever is chosen goes to the Foundation as a diff):
- **(a) Hide it on the portal**: no rail button, no Ctrl K command, and the Sign card's note "For a certificate signature use Protect › Sign with certificate" dropped when `Kind == Web`. Pros: "off" means off; nothing dead on screen; works on touch. Cons: the Protect and Redact rails are one button shorter than the handout's; nobody learns that the desktop app can do it.
- **(b) Keep it, greyed out, with the reason "Certificate signing is in the desktop app. Your private key never leaves your computer."**: the same `DisabledReason` mechanism as before. Pros: the rails stay as the handout draws them; it explains why and points to the desktop app ("Get the desktop app" is in the account menu). Cons: on touch the reason is a tooltip that can't be seen (the WT-09 problem), unless the card opens with that sentence in place of the fields.
- **(c) Open the 12c Sangam gate from it.** Pros: it is the handout's design for signing. Cons: D-27 (c) puts Sangam's e-signature ceremony later; today the gate would lead nowhere, since the person is already signed in with Sangam.

**Recommendation: (b), with the card showing the sentence in place of the fields on touch**, so the reason is readable everywhere. If you would rather have the smallest change, (a).

## Observations for the Foundation from the patch 26 re-check (not portal-only; no decision needed from me)
- **Find box in Excel and Word doesn't take the cursor.** With a PDF, Find (button or Ctrl F) focuses the box (`_findBoxRef.FocusAsync()` in `OpenFind`). The Office box (`Reader.razor` line 371, `_viewerFindOpen`) has no `@ref` and no focus call, so focus stays on the button (or the page) and the person has to click into the box. The same in Chromium, Firefox and WebKit, and on a phone the keyboard doesn't come up. It has been so since the v3 revamp (d8f32d9), not from patch 26. I can send a small diff if wanted.
- **Find hits in hidden rows and columns can't be seen.** `layout.xlsx`, Find "hidden": "4 found", tab badges Layout 2 · Secret 1 · Deep 1. The two Layout hits are A5 (hidden row) and C6 (hidden column), so the sheet shows no outlined cell. The tests say hidden cells stay findable (D-171); this is only to note that the person gets a count with nothing to look at.
- **Phone:** "4 found" wraps onto two lines in the Find box (390 px), and the hit badges of sheets further along the tab strip are off-screen until the strip is scrolled.
- **Declared already** (audit E-07): a merged range that crosses the frozen line is cut at it. `layout.xlsx` A1:B2 shows "Title merge", and the yellow fill stops at column A.

## ✔ decided (a) now, (b) later when Office Find gets next and previous — D-188 — U-19 Find matches inside hidden rows and columns: how the person sees where they are (asked for by the coordinator, 15 Nov; an option, not a diff)
**Today** (`layout.xlsx`, Find "hidden"): "4 found", tab badges Layout 2 · Secret 1 · Deep 1. The two Layout matches are A5 (row 5 is hidden) and C6 (column C is hidden), so nothing is outlined on the sheet. Matches in hidden *sheets* are already reachable: the tab carries the count and opens on a click. D-171 keeps hidden cells findable, so the question is only how to show them.

- **(a) A line under the Find box naming them.** For the sheet on screen: "2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)". With more than five: the first five, then "and 12 more".
  - Pros: says where, in words, with the cell address; readable on touch; the grid doesn't change; small (the viewer already knows each match's cell and which rows and columns are hidden).
  - Cons: the Find box grows by a line (two on a phone at 390 px); it names the place but doesn't show the value.
- **(b) Step through the matches, and let the value bar show each one.** Enter goes to the next match (as Excel's Find Next does). For a hidden one the value bar reads "A5 · hidden row" with the stored value, and nothing moves on the grid.
  - Pros: every match, hidden or not, gets an address and its value; it uses the value bar that is already there; it also gives Office Find the next / previous it lacks today.
  - Cons: the biggest piece of work (stepping, a current match, scrolling to visible ones); the value bar gains a second kind of content.
- **(c) Mark the gap on the sheet.** The header line between rows 4 and 6 (and between columns B and D) is drawn in the match colour, with the tooltip "Match in hidden row 5 (A5)".
  - Pros: shows the place on the sheet itself, where the eye already is.
  - Cons: a tooltip can't be read on touch; easy to miss; several hidden matches in one gap share one mark.
- Not offered: leaving hidden cells out of Find. That would go against D-171.

**Recommendation: (a) now.** It is the smallest change that answers "where is it?" everywhere, phone included. (b) is the fuller answer and is worth doing when Office Find gets next / previous anyway. (c) only as an extra on top of (a).

## ✔ sent to the Foundation as a task (coordinator 16 Nov 00:40) — Ctrl F does nothing on Word, Excel, Markdown and text files (found 15 Nov; old, every platform)
The Find button's tooltip says "Find (Ctrl F)", and for a PDF the key opens Find. For the other formats it opens nothing. The key handler lives in `reader.js` `init(deskEl, …)` (line 280), which runs only when a PDF's desk is set up (`Reader.razor` line 3480), and it calls `OpenFind`, the PDF Find. I tried routing `OpenFind` to the viewers' Find for view-only formats: no effect, because the handler isn't attached at all while an Office file is shown. So this is a piece of its own (attach the keys for the viewers too); it is **not** in my Find-focus patch. The same in Chromium, Firefox and WebKit, on the Web and Windows profiles.

## ✔ decided (a), D-192 — U-20 The hidden-matches line sits under the Find box (found 16 Nov, confirming patch 28)
Routed to the Foundation by the coordinator, 16 Nov 14:33. The diff is regenerated against patch 29 (HOOKS).

**What happens.** Patch 28 draws "2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)" above the sheet (D-188, U-19 a). The Find box floats over the top centre of the viewer, on the same strip. Measured share of the sentence covered: 10% at 1280 px (the end is cut), about 20% on a tablet, 43–48% on a phone, where it can't be read; 0% only on a very wide screen (1920 px). The same in three browsers. Screenshot: `screenshots/webkit-u19-line-under-find-box.png`.

**Options** (the file is the Foundation's `XlsxView`):
- **(a) Move the line under the sheet, just above the sheet tabs.** Diff ready and measured: `proposal/web-ui-xlsx-hidden-matches-under-sheet.patch` (HOOKS).
  - Pros: 0% covered at every size; it sits next to the tabs' match counts, which report the same thing; 8 lines; nothing else moves.
  - Cons: it is at the bottom, away from the Find box where the person has just typed.
- **(b) Keep it on top, and push it below the Find box while Find is open** (top padding as tall as the box, about 60 px).
  - Pros: it stays near the Find box.
  - Cons: the sheet jumps down about 60 px whenever such a match exists; the viewer has to know the Find box's height, which belongs to the Reader.
- **(c) Put the sentence inside the Find box, as a second line under the count** (what I first proposed for U-19 a).
  - Pros: it is exactly where the person is looking; never covered.
  - Cons: the most plumbing: the Find box belongs to the Reader and the sentence is worked out in the Excel viewer, so it needs a callback between them; the box grows on a phone.

**Recommendation: (a).** It is the smallest change that makes the line readable everywhere, and it is ready. (c) is the nicest place and fits with (b) of U-19 (next / previous) later.

## Observations from the patch 29 check (16 Nov): the ask-before-closing card and the Excel resize
**The card against D-190** (three browsers × portal desktop, tablet, phone and the Windows profile; all the same unless said):
- Button order: Save · Save as… · Discard · (gap) · Cancel, on one row. Save is the primary button and Discard is in the danger colour. A file that can't be written offers Save as… · Discard · Cancel, with Save as… primary. ✔
- Focus: on Save when the card opens (on Save as… for a read-only file). ✔
- Enter (focus on Save): the marks are written into the file and the tab closes. Esc: the card goes, the tab and its mark stay, the file is untouched. Discard: the tab closes, the file is untouched. Cancel: as Esc. ✔
- The page behind doesn't answer a click or a tap (scrim). ✔
- **Tab is not held in the card** → diff in HOOKS (`web-ui-close-card-keeps-focus.patch`).
- **Wording differs from the words quoted in D-190.** D-190 says: a card "This file has unsaved marks". The card says: title "Save the marks on **<file name>**?", text "It has 1 mark that is not saved. It is lost if you close without saving." (plural: "It has 3 marks that are not saved. They are lost if you close without saving."), and with several files " File 2 of 3." The meaning is the same and it names the file, which helps when several are closing. For the coordinator to accept or change.
- Phone (390 px): the card sits at the bottom, inside the screen, with 44 px buttons; **"Save as…" wraps onto two lines inside its button**. Small; a shorter gap or a second row would cure it.

**Excel resize against D-190** (same 12 cases; `layout.xlsx`):
- Drag a column's edge: B 64 → 124 px for a 60 px drag, and the columns after it move by 60. Drag a row's edge: row 9 20 → 44 px, rows below move by 24. A guide line shows while dragging; the mouse cursor is `col-resize`. With touch-type pointer events on the tablet and phone profiles the same. ✔
- Press twice on an edge: the column fits its content (A 140 → 327 px; 328 in Firefox). Smallest size 8 px. ✔
- For viewing only: the file's bytes are unchanged after all of it. Kept with the tab: after another sheet and back, the sizes are still there. ✔
- The way back: "File's own sizes" appears beside the sheet tabs once something is resized; it restores every size and goes away. ✔
- A cell still shows its value in the value bar after a resize; no sideways scroll; no page errors. ✔
- What I could not do here: a real finger. The touch cases use pointer events of type "touch" sent by script, which exercise the 14 px reach but not the browser's own gesture handling.

## View asked for by the coordinator (16 Nov 21:35): what the ask-before-closing card should offer on the portal
The question (coming to Arun from Web): on the portal the card's Save writes the marks into the session copy on the server, and nothing downloads.
1. **Save should download, as Ctrl S does on the portal, and the tab closes once the download has been handed to the browser.** D-03 already says that on the Web "Save = browser download", and the Web host delivers Save and Save as as downloads. One word should do one thing (the WT-10 rule).
2. **Not "as is".** A Save that only updates the server's copy and then closes the tab looks finished but leaves nothing on the person's computer, and 12a promises that copy is wiped at sign-out. It is the one path where the card loses the work it exists to protect.
3. **Keep D-190's order: Save · Save as… · Discard · Cancel, if Save as… asks for a name on the portal; show Save alone if both would hand over the same download.** Two buttons that do the same thing make the person stop and wonder. "Only Save as…" is safe, but it drops the one-press answer the card is built around.

## Recorded: D-194 (coordinator 16 Nov 22:50)
On the portal the ask-before-closing card offers only Save as…, also on Sign out; it arrives with patch 32. I will check it in the portal then.

## Observations from the patch 31 check (16 Nov): the encoding picker (D-185, D-191)
Checked in Chromium, Firefox and WebKit on portal desktop, tablet, phone and the Windows profile, with five small files made for it (UTF-8, Windows-1252 and UTF-16 LE text, UTF-8 Markdown, HTML that declares windows-1252).

**As designed** (the same in all 12 cases unless said):
- Detection: all five files are read right at once, and the HTML file's own declared charset is honoured.
- Status bar (desktop and Windows; the tablet and phone have no status bar): a small button with the encoding's name and a chevron, tooltip "Read this file as…", read out as "Read this file as… Now Windows-1252".
- Other ways in: Document ▾ › "Text encoding…" (desktop, tablet, Windows), ⋮ › "Text encoding…" (phone).
- The card: title "Read this file as" with the file type; rows Automatic (with what was detected), UTF-8, Windows-1252, UTF-16 LE, UTF-16 BE; exactly one chosen; footer "The file itself is never changed. Your choice is remembered while the file is in Recents." LiPi Sans 12.5 px, the same card as the other tools; a bottom sheet on the phone; always inside the screen.
- Choosing: UTF-8 on the Windows-1252 file re-reads it at once ("Caf� …"), shows "9 bytes don't fit UTF-8" in the card, and the status button says UTF-8. Windows-1252 puts it right and the note goes. Automatic returns to detection. The file's bytes never change.
- Keyboard: Enter on the status button opens the card; Enter or Space on a row chooses it; Tab goes down the rows in order; Esc closes the card from anywhere.
- Kept without a reload: after going to Home and back to the tab, the choice and the text are still there.

**For the coordinator to decide or pass on:**
1. **Rows are 34 px on tablet and phone** → small diff in HOOKS (`web-ui-encoding-rows-finger-size.patch`).
2. **Two names for one thing.** The status button and the card say "Read this file as…"; the Document and ⋮ menus say "Text encoding…". By the WT-10 rule (one word for one action) the menu entry could read "Read this file as…" too. Pros: one name everywhere. Cons: "Text encoding…" is the word a person who knows the term looks for in a menu, and Ctrl K still finds it by "encoding" either way (the command keeps those keywords).
3. **The keyboard doesn't land in the card.** Opened from the status button, the focus stays on that button, and the first row is 20 Tabs away (22 on the Windows profile), because the status bar is last on the page. Arrow keys don't move between the rows. Both are how every card and radio group in the app behaves today (FloatCard has no focus handling; Print's page range and the Settings segments are the same), so the picker is consistent with the design language; the gap is the app's, not the picker's. A fix belongs in FloatCard, for all cards at once.
4. **Not provable in my preview: the choice after a page reload.** Here a reload forgets it, because the preview has no session storage. On the real portal Recents live in the session's storage on the server (`SessionAppStorage`), so the choice should survive F5. For Web Test: choose an encoding, press F5, expect it kept.

## Observations from the patch 32 check (18 Nov): the close questions and Find (D-194, D-195)
Checked in Chromium, Firefox and WebKit on portal desktop, tablet, phone and the Windows profile: 12 runs, 6 cases each, every case passing.

**As designed:**
- **Marks** (portal): Save as…, Discard, Cancel. On Windows: Save, Save as…, Discard, Cancel. The keyboard starts on the first button, Tab and Shift Tab stay inside the card, Esc cancels. Save as… writes a new file and leaves the original untouched.
- **Bookmarks:** "Save the bookmarks of <file>?" Save bookmarks, Discard, Cancel. Save bookmarks writes them into the file.
- **Redaction areas:** "Discard the redaction areas on <file>?" Discard and Cancel only, and the keyboard starts on Cancel, not on Discard. Discard leaves the file untouched.
- **Arrange:** "Save what you arranged?" Save session…, Discard, Cancel. The question shows Arrange behind it. Save session… writes a session file.
- **Both at once:** Arrange is asked first, then the file. Cancel on the second question stops the whole close.
- **On Sign out** (portal: account menu on desktop and tablet; ⋮ on the phone; Account › Sign out on the phone's Home): the same cards. Cancel keeps the person signed in; an answer signs them out.
- **Find:** the current match is never under the Find bar or off screen: 16 steps of 16 in all 12 runs. The bar moves aside for 12 of the 16, as it should for matches on the top line.
- **Look:** all four cards use the house card style (LiPi Sans, the binding colour for the main action, danger red for Discard), one row of buttons, always inside the screen. Buttons are 44 px tall on tablet and phone.

**Your wording rule ("keep as built, unless it reads wrongly in a new card"):** the file name in the title reads well in all four cards. Two small points; neither is wrong enough to need changing on its own:
1. **"Save the marks *on* <file>?" but "Save the bookmarks *of* <file>?"** Both read naturally; "on" for marks and redaction areas, "of" for bookmarks is how people would say it. My view: leave it.
2. **"…nor saved in a session" in the Arrange card, shown at Sign out.** On the portal "session" already means the sign-in ("Files live only for your session", "kept for this session"), so at Sign out "saved in a session" can be read as "kept in this sign-in", the opposite of what it means. Options:
   - (a) Leave it. Pros: no work; Arrange calls these files "sessions" on every platform. Cons: the clash above, on the portal only.
   - (b) Say "saved in a session file" everywhere (one word added; the button "Save session…" stays). Pros: clearer on every platform, no portal-only wording. Cons: one wording change through the Foundation.
   - (c) A portal-only wording through PlatformText. Pros: desktop untouched. Cons: two wordings for one card.
   - **My recommendation: (b).** I'll write the exact diff if you choose it.

**For the coordinator to decide or pass on:**
3. **Phone: two long labels break onto two lines** ("Save bookmarks", "Save session…") → diff in HOOKS (`web-ui-close-card-phone-labels.patch`), measured in three browsers, including the four-button Android card.
4. **Bookmarks on the portal.** "Save bookmarks" writes the session's working copy and downloads it under the file's own name. So the person does get their file, unlike a plain Save, which D-194 removed for marks. I think this is right as built; I'm only flagging that the bookmarks card doesn't follow the marks card's "Save as only" rule.
5. **For Web (when it takes patch 32):** the Ui asks on Sign out only if the host's `IAccount.SignOutAsync` first calls `IUnsavedWork.ConfirmCloseAsync` (Services.cs: "The portal calls the same before Sign out"). Today `WebPlatform.SignOutAsync` (95c44b0) goes straight to `/signout`. Also, a Save as… or Save session… chosen at Sign out is delivered as a download, so the move to `/signout`, which wipes the session's files, must wait until that download has been handed to the browser. In my preview I did the first part to test the cards; the second can only be proved on the real portal.

**Closed:** the encoding choice after a reload (point 4 of the patch 31 check). Web Test proved it on the real portal (`encoding_picker.py` 12/12 × 3: survives a reload, not seen by a second person, gone after sign-out).

## Observations from the patch 33 check (18 Nov): what is held until the next library update (D-198, D-199, D-200)
Checked in Chromium, Firefox and WebKit on portal desktop, tablet, phone and the Windows profile. My test files:
- a plain PDF;
- the Foundation's `rich.pdf` (bookmarks, page labels, language) and `layered.pdf`;
- a PDF signed with the app's own signing service (self-signed certificate);
- an Excel file with one conditional-colour rule.

**As designed:**
- **Page operations ask first** (Arrange › Bind and Bind all). Title "The new file will not have everything", buttons Continue and Cancel, and the keyboard starts on Cancel. Tab stays in the card; Esc cancels, and the next Bind asks again. After Continue, the same file isn't asked about again in that run.
  - A plain file is still asked about ("…has none of what is left out (bookmarks, form fields, links to places in the file, page labels, language, tags)").
  - `rich.pdf` names its bookmarks, page labels and language.
  - `layered.pdf` adds "It has layers: a layer that is hidden in the file may show in the new one. Check the result before you rely on it."
  - Two files: one line per file, then "Files with layers: …". The phone shows them as a list.
  - The card is the close card's style, one row of buttons (44 px on touch), always inside the screen.
- **Redaction held:**
  - Desktop: Protect's rail shows Redaction greyed, with "soon" and the reason on hover.
  - The R key, Ctrl K and the redact page don't open it. The redact page says "Redaction comes back with the next update.", gives its one-line reason, and offers only "Back to the document", which works.
  - Arrange no longer offers "Send to Redact".
- **Signature check:**
  - The banner and status bar say "Signed by A. Shiva · 17 Nov 2026 · not checked in this version" and "1 signature · not checked in this version".
  - The card says "Not checked" and ends "Shown here is what the signature states. Whether it is valid, and whether the file changed after it, is not checked in this version: checking comes back with the next update." No "Valid" or "Trusted" anywhere.
- **Excel:** "Conditional colours return with the next update", one line under the sheet that has the rule (phone included). Its tooltip: "This sheet colours some cells by rule. Those colours are not drawn in this version; the values are." The rule's cell has no colour, and the sheet without rules has no line.
- **Tone:** plain and calm throughout. Each message says what is missing, that it comes back, and what to do. Nothing alarming, nothing hidden.

**For the coordinator to decide or pass on:**
1. **On tablet and phone a tap on held Redaction says nothing** (the phone's tools read only "Box" and "Find"); the certificate next to them does say why. → diff in HOOKS (`web-ui-held-redaction-reason-on-tap.patch`), measured in three browsers. **The one thing in patch 33 I'd fix before Phase 1.**
2. **"…the bookmarks, page labels and the document's language of rich.pdf."** "The document's language of" reads awkwardly; in the two-file list it's "its bookmarks, page labels and the document's language".
   - (a) Leave it.
   - (b) Say "language": "…the bookmarks, page labels and language of rich.pdf" / "its bookmarks, page labels and language". One word list in `PageOperationCheck`.
   - **I recommend (b)**, mildly; I'll write the diff if wanted.
3. **Ctrl K cuts the reason** to "Redaction comes back with the nex…", so the important word is lost. The command list's reason column is narrow for every greyed command; this is the first long reason a person will meet there often. Options:
   - (a) Leave it: the full sentence is in the tooltip and on the redact page.
   - (b) Let the reason wrap to a second line in the command list (one CSS rule; changes every command with a long reason).
   - **I recommend (a) for Phase 1.** It goes away with Pdf 3.35.1.
4. **Small, no change suggested:**
   - The rail tooltip stutters ("Redaction — Redaction comes back with the next update."), from the "Label — reason" pattern.
   - The note shown on a tap has the app's green tick, a "done" sign, for a "not available" message.
   - The signature card's details line "valid to 17 Nov 2027" is the certificate's own end date, not a verdict.
