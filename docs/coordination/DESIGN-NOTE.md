# Design handout — what every platform chat must follow

Arun's finalised design is the Claude Design handout in `docs/design-handoff/` (from `PDF_Viewer_Design_Revamp_3.zip`, added 6 Nov 2026). It is the visual reference for **every** platform. Match it exactly; the existing `ChuvadiReader.Ui` code is how it is implemented on Windows so far.

## Order of authority (highest first)
1. Arun's own instructions in chat, and the programme rulebook (`docs/coordination/RULEBOOK.md`).
2. `docs/design-handoff/reference/CHUVADI-READER-DESIGN-AND-ROADMAP.md` (locked decisions D-07 to D-10).
3. `Reader Side Rails.dc.html` (D-10 chrome) and `Portal & Android.dc.html` (web portal, Android tablet, Android phone).
4. The rest of `README.md`, then the other `.dc.html` files. Where `README.md` says "mode bar", "leaf bar" or "margin", read top bar, View rail and settings cards.

Open any `.dc.html` in a browser with `support.js`, `lipicons.js` and `fonts/` beside it (headless Chromium or similar is fine for testing — external tools are allowed for testing only).

## Platform sections to build to
| Platform | Follow | Key points |
|---|---|---|
| Windows | `Reader Side Rails` | Reference build (Reader chat owns it). |
| Mac | `Reader Side Rails`, README "Platforms", `Chuvadi Revamp v3` frames | Traffic lights on the left; app menu in the macOS menu bar (File, Edit, View, Document, Window, Help); ⌘ shortcuts. |
| Linux | `Reader Side Rails`, README "Platforms", `Chuvadi Revamp v3` frames | Same as Windows; 12 px window corners; honour the GNOME/KDE button layout. |
| Web | `Portal & Android` 12a–12c | Blazor Server; Sangam sign-in page (12a) required; no window controls — account menu instead; status bar "processed on the server · encrypted at rest · only you can see it"; Sangam gating (12c). |
| Android tablet | `Portal & Android` | Same rails at 72 / 72 / 60 px with 48 px touch targets. Supersedes the tablet mockups in `Chuvadi Mobile`. |
| Android phone | `Portal & Android` | Left bar → bottom bar; Tools rail → tool strip (Mark/Protect only); View rail → pinch gestures + View sheet. |

## Superseded by later decisions — do NOT follow these parts of the handout
- **Roadmap §4 "Photino.Blazor for Linux"** and **"MAUI for Windows"**: superseded. Photino is an external (not allowed); Linux uses our own WebKitGTK host. Windows keeps its WPF host.
- **README "Web: files are processed in the browser", "Install app (PWA)", "local · files stay in this browser"**: superseded by D-10 / `Portal & Android` — Web is Blazor Server with Sangam sign-in.
- **`Chuvadi Mobile.dc.html` tablet frames and the README "Mobile" section**: superseded by `Portal & Android` for Android. iOS is not in scope.
- **Anjal Mail embedding**: out of scope.

## Gaps today (6 Nov)
- The current Ui implements the desktop D-10 rails partly (SideRail, left bar, View rail, 5 themes). Arrange/Protect still live on separate Bench/Redact pages, and the Reader chat continues the desktop revamp.
- **Not in the Ui yet:** Android phone/tablet layouts, web portal chrome, Mac system menu bar, Linux window chrome.
- **Ownership (decided 6 Nov):** the **Mobile app UI** chat builds the Android phone and tablet look (`platform/mobile-ui`); the **Web portal UI** chat builds the portal look (`platform/web-ui`); the Mac and Linux chats define their own chrome. All as new components behind the Foundation's platform + form-factor signal; existing-file hooks go to the coordinator as exact diffs with pros and cons.
- **Web scope (Arun, 6 Nov):** no server storage this release — leave out quota, 'My files', 'autosaved to your storage' and storage in the account menu; no sharing ('Shared with me', 'Share a link').
- Library-gated features stay locked as the handout says (regex redaction, Replace, shape primitives, image alpha, password API, Layout-based Office view).
