# Seventh combined patch — on `platform/foundation` (8 Nov)

## Part 1 (applied)
| Item | From | Where |
|---|---|---|
| **H-13** bug fix: double-tap page jump (zoom keeps the visible page anchored) and API 35 fit sizing | Mobile UI (`mobile-ui-hooks-4.patch`) | `reader.js`; Mobile UI's `mobile.js` |
| **Web H7** status-bar text per D-98: "processed on the server · kept in memory only · only you can see it" | Web portal UI (`web-ui-hooks-7-status-text.patch`) | `MainLayout.razor` |
| Web portal UI files: `PortalLegalLinks` (Terms of use · Privacy footer in the account card and phone account block, U-15 a / D-97), D-98 wording in the phone block, sign-in page tidy | Web portal UI (5bec046) | `Components/Platform/Portal/*` |
| **Window buttons follow the desktop's layout exactly** (Linux bug, D-93): `ShellChrome.ButtonLayout` (ordered buttons per side; null = today's behaviour), `WindowButtons` draws exactly those | Linux (`PROPOSAL-window-button-layout.md`, shared diff unchanged) | `PlatformInfo.cs`, `WindowButtons.razor`, `MainLayout.razor` |

## Part 2a (applied)
| Item | From | Where |
|---|---|---|
| Portal privacy line: "Processed on the Chuvadi server · kept in memory only · only you can see it. Your files are removed when you sign out." (D-106: D-98 supersedes D-20) | Coordinator | `PlatformText.ServerPrivacy` (Settings footer, Library index hint, About › Network on the portal) |
| **P-07** bug fix: MainLayout navigates to the Reader only when it isn't already showing, so Back no longer steps through duplicate history entries | Android (a42d9f0) | `MainLayout.razor` |
| **D-104** "Drop to open" overlay for the portal drop catcher | Web portal UI (`web-ui-drop-overlay.patch`, cd03fac) | `PortalDropCatcher.razor(+.css)` |
| 12a sign-in pitch: "kept in memory only" (D-103) + test | Web portal UI (cd03fac) | `PortalSignIn.razor`, `PortalTextTests.cs` |

Proof: Windows 27/27 identical (before `cd9b72d`); portal drag-and-drop checks 1–7 pass with the overlay; build 0 warnings; tests 274/274.

## Part 2b (applied; written by the Foundation, D-101, coordinator 20:22)
| Item | From | Where |
|---|---|---|
| `IPlatformInfo.ChromeChanged`: raised after `Chrome` changes. It has a default body that does nothing, so every existing `IPlatformInfo` compiles unchanged | Foundation (the Linux proposal's option B) | `PlatformInfo.cs` |
| The top bar redraws on it: MainLayout listens on non-Windows platforms only, like `FormFactorChanged` | Foundation | `MainLayout.razor` (+5 lines) |
| Tests: contract test; live redraw of the real Ui under 6 layouts | Foundation | `ChromeChangedTests.cs`; `tools/PixelProof/chrome-changed.js` with the preview's Linux mode (`CHVD_FF=linux`) |

The Linux chat wires its GTK settings watcher to it (`PLATFORM-INTERFACE.md`, "Live chrome changes").

Proof:
- Windows 27/27 identical vs `9fbed93`. On the first run Home and Library at 1× showed 28 px and 14 px of difference; both were identical on two re-runs (the known first-screenshot artefacts).
- Live redraw passes 6/6 with no page errors.
- Build 0 warnings (`-warnaserror`); tests 276/276.

## Proof (part 1)
- Windows pixel-identical: 9 screens × 3 scales, before `f6607a3` vs after — **27/27 identical**.
- Portal and phone: Home, Reader, Bench, Redact, Library, Settings — no page errors, no error bar; the portal status bar shows the D-98 text.
- Build 0 warnings; tests 273/273.
