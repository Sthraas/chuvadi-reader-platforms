# Seventh combined patch — on `platform/foundation` (8 Nov)

## Part 1 (applied)
| Item | From | Where |
|---|---|---|
| **H-13** bug fix: double-tap page jump (zoom keeps the visible page anchored) and API 35 fit sizing | Mobile UI (`mobile-ui-hooks-4.patch`) | `reader.js`; Mobile UI's `mobile.js` |
| **Web H7** status-bar text per D-98: "processed on the server · kept in memory only · only you can see it" | Web portal UI (`web-ui-hooks-7-status-text.patch`) | `MainLayout.razor` |
| Web portal UI files: `PortalLegalLinks` (Terms of use · Privacy footer in the account card and phone account block, U-15 a / D-97), D-98 wording in the phone block, sign-in page tidy | Web portal UI (5bec046) | `Components/Platform/Portal/*` |
| **Window buttons follow the desktop's layout exactly** (Linux bug, D-93): `ShellChrome.ButtonLayout` (ordered buttons per side; null = today's behaviour), `WindowButtons` draws exactly those | Linux (`PROPOSAL-window-button-layout.md`, shared diff unchanged) | `PlatformInfo.cs`, `WindowButtons.razor`, `MainLayout.razor` |

## Part 2 (waiting for the diffs)
- **D-101** live "chrome changed" event (the Linux proposal's option B: `IPlatformInfo.ChromeChanged`, MainLayout re-renders the buttons) — no diff yet.
- **D-104** Web portal UI drop-overlay diff — not on `platform/web-ui` yet.

## Proof (part 1)
- Windows pixel-identical: 9 screens × 3 scales, before `f6607a3` vs after — **27/27 identical**.
- Portal and phone: Home, Reader, Bench, Redact, Library, Settings — no page errors, no error bar; the portal status bar shows the D-98 text.
- Build 0 warnings; tests 273/273.
