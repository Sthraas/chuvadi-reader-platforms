# Web — decisions waiting for Arun

Raised 6 Nov 2026 by the Web chat. Nothing below is built until Arun decides. Each item has the options, pros and cons, and a recommendation.

## W-01 Do files stay on the server? (kickoff and design disagree)

- **Kickoff:** "no file stays on the server after the session".
- **Design `Portal & Android` 12a/12b:** per-user storage with a quota ("Storage 1.8 / 10 GB"), "autosaved to your storage", account menu "My files" and "Shared with me", promises "Encrypted at rest, per-user storage" and "Delete a file and it is gone from the server".

| Option | Pros | Cons |
|---|---|---|
| (a) Session-only: everything wiped when the user signs out or the session ends | Smallest attack surface; no storage, quota, backup or encryption-key work; simpler privacy story | Contradicts 12b (storage meter, autosave, My files, Shared with me); the Ui's Library, Recents, Pinned and watched folder are empty every visit; users must re-upload each time |
| (b) Persistent per-user storage, encrypted at rest, as 12b shows | Matches the design; the existing Ui (Library, Recents, save folder, sessions) works as on desktop, because each user simply has their own folder | Needs encryption at rest, per-user keys, quota, backups, a delete-really-deletes guarantee, and a data-protection/retention policy (medical documents are likely) |

Recommendation: (b), because it is what the locked design shows and the Ui is built around a persistent folder. "Shared with me" then needs its own decision (W-07).

## W-02 How users are isolated on the server

The Core is a desktop core: it writes to `Path.GetTempPath()` (Bench, Press, Reader), `%AppData%/ChuvadiReader` (desk templates, `SessionService`), `Documents/Chuvadi Documents` (`SaveFolderService`), and greets the user by the OS account name (`UserProfileService`, `Environment.UserName`). The spike showed the dashboard saying "Good evening, Root." — the server's account. In one shared process these paths are shared by every user.

| Option | Pros | Cons |
|---|---|---|
| (a) One server process, services per session (scoped) | Lowest memory: ~10–20 MB per extra user; one process to run | The paths above are shared between users, so many existing Core and Ui files must change to take a per-user root (rule 4 list, Reader chat's code); Pdf A (name table never shrinks) grows the one process until restart; Pdf B (font renderer race) can drop Indic text for every user |
| (b) One worker process per signed-in user, behind our own Kestrel gateway | Unchanged Core and Ui: each worker gets its own HOME, TMPDIR and data folder, so temp files, app data, Documents and sessions are per user with no code change; Pdf A memory is returned when the worker exits; Pdf B can only hit within one user's own session; one user's crash or runaway file can't affect others; per-worker memory cap with the built-in `DOTNET_GCHeapHardLimit` | ~95 MB idle and ~120–135 MB after a few pages per active user (measured on the spike, before tuning), so roughly 50 active users per 8 GB; we write and test our own HTTP + WebSocket relay in the gateway (no YARP — it is a separate NuGet, so an external); 1–2 s start on sign-in; more to monitor |

Recommendation: (b). It keeps the Reader chat's code untouched, turns two production blockers into contained risks, and gives real isolation for medical documents. Pdf A and B still need Arun's library decision; (b) only reduces their blast radius.

## W-03 TLS certificate on Kestrel (no nginx)

Kestrel can serve 443 itself; systemd's `AmbientCapabilities=CAP_NET_BIND_SERVICE` lets it bind 443 without root.

| Option | Pros | Cons |
|---|---|---|
| (a) Our own small ACME (Let's Encrypt) client in C#, BCL crypto only | Free, automatic 90-day renewal, no external | ~400 lines to write and test; must handle renewal failures |
| (b) `certbot` from the Ubuntu archive, Kestrel reloads the files | Proven, little code | An external tool on the production server (rule 3) — needs your approval |
| (c) Buy a yearly certificate, install by hand | No code, no externals | Manual yearly renewal; expiry risk |

Recommendation: (a), with Kestrel reloading the certificate without a restart.

## W-04 Sangam sign-in — I need the integration method from you

Please tell me (I will not guess):
1. Protocol: OpenID Connect authorisation code + PKCE, plain OAuth 2, SAML, or Sangam's own?
2. The issuer / discovery URL, and a test (sandbox) tenant I can use.
3. How the portal is registered as a client (client id, secret or not, redirect URL, allowed sign-out URL).
4. What comes back about the user: name, Sangam ID (e.g. `arun.s@smh.sangam`), organisation/department ("Records" in 12b), roles, quota?
5. Token lifetime and refresh; single sign-out.
6. Is the 12a "or with your Sangam ID" field a login hint passed to Sangam, or does the portal take the ID itself?

Related rule question: the OpenID Connect handler (`Microsoft.AspNetCore.Authentication.OpenIdConnect`) is a Microsoft NuGet, not part of the .NET shared framework, and pulls in `Microsoft.IdentityModel.*`. Cookie sign-in is in the framework. Options: (a) write our own code-flow client with HttpClient and BCL RSA/ECDsa token checks (~300 lines, no externals); (b) allow the Microsoft package. Recommendation: (a), unless Sangam ships its own .NET client library.

## W-05 Existing-file hooks the web portal needs (for approval; not edited)

The portal chrome is built as new components in the Web project. These existing Ui/Core spots are web-wrong today and need a hook (a platform switch) to show the portal versions. Exact diffs come once W-01/W-02 are decided.

| # | File | Today | Web needs (per 12b) |
|---|---|---|---|
| H1 | `Ui/Layout/MainLayout.razor` lines 124–126 | Minimise/maximise/close buttons always shown | Account button + menu (My files, Shared with me, Get the desktop app, Account settings, Sign out) with storage meter |
| H2 | `Ui/Layout/MainLayout.razor` line 163 | Status bar "offline · on this device" | "processed on the server · encrypted at rest · only you can see it", user · Sangam, autosave time |
| H3 | Left rail globals (MainLayout) | Open, Find, Library, Home | Upload, Find, Library, Home |
| H4 | `Ui/Pages/Dashboard.razor` line 31 | "nothing leaves this device" | Must not say this on the web |
| H5 | `Ui/Pages/Settings.razor` line 37; `Settings/AboutSection.razor` line 14; `Settings/LibrarySection.razor` line 50 | "Stored on this device only", "Network: Offline", "Stays on this device" | Server wording |
| H6 | `Core/Documents/UserProfileService.cs` line 39 | Greets with the OS account name | Sangam display name |
| H7 | Folder pickers: Library folder, watched folder, save folder, Split/Bench output folder | Native folder dialogs | Depends on W-01: folders inside the user's own storage, or hidden |

Smallest shape I'd propose: one new Core interface (e.g. `IHostProfile` with `IsWeb`, status text, account info) that the Windows host registers as "desktop", plus a few `@if` switches. Each line above goes to you with pros and cons before any edit.

## W-06 Packages: the Web host builds on Core as it is

`ChuvadiReader.Core.csproj` at c7b9e44 still references the umbrella `Chuvadi.Pdf` 3.31.1, `Chuvadi.Docs` 1.1.0 and `Chuvadi.Sheets` 1.1.2. The package report recommends individual Pdf packages, Sheets 2.0.1, and waiting for Docs 2.0.0. Changing that file is the Reader chat's work and your decision; the Web host will not reference library packages of its own beyond what it needs for printing/downloads, and will follow Core.

## W-07 "Shared with me" and "Share a link"

12b's account menu has "Shared with me"; 12c lists "Share a link" as Sangam-gated. Is sharing in scope for the first web release, or shown as coming later? Sharing medical documents needs access rules, link expiry and an audit trail.
