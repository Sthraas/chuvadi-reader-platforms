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

## U-15 Terms of use and Privacy from the account menu (coordinator 7 Nov 04:55: "propose one if the handout has no place")
**12a (sign-in): built.** "Terms of use · Privacy" on one line under the desktop-app line (`PortalLinks.TermsUrl`, new optional `PortalLinks.PrivacyUrl`; each hidden when null). The Web host passes `"/terms"` and `"/privacy"` (the Foundation's `Licence` page, served before sign-in).

**12b (account menu): the handout has no place for them.** The card holds the person, the storage meter (out of scope), My files / Shared with me (out of scope), Get the desktop app, Account settings, Sign out. Options:
- **(a) A small footer line at the bottom of the card, under Sign out: "Terms of use · Privacy"** (12 px, muted, same style as the 12a line). Same line at the foot of the phone account block (`PortalPhoneAccount`). Pros: one click from anywhere while signed in; matches 12a; adds no menu row, so the actions keep their weight; keeps the DPDP notice "readily accessible". Cons: a small departure from the 12b frame.
- **(b) Two menu rows ("Terms of use", "Privacy") between "Account settings" and "Sign out".** Pros: same look as the other items; bigger touch targets on phones. Cons: legal links compete with the real actions; the card grows by two rows (on a phone the ⋮ sheet is already long on document views).
- **(c) Nothing in the menu; rely on Settings › About › Licences**, which already shows the licence agreement and (on the portal) the terms and privacy texts. Pros: no change. Cons: three taps deep; a person looking for "privacy" will not think of "Licences".

Recommendation: **(a)**. Not built until decided (it touches `AccountMenu`, which the Foundation edited for Unit — I would send the change as a small diff on its current copy).

## D-89 Home drop overlay on the portal — what I will check when the Foundation's overlay lands
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
