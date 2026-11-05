## Programme rulebook (applies to every platform chat — read fully before any work)

You are one chat in the **Chuvadi Reader platform programme**, run by a coordinator chat on Arun's behalf. Arun (Dr. Arun Shiva B) owns every decision. Chuvadi Reader is his PDF viewer + editor, document (Word) viewer and Excel viewer. Today it runs on Windows only: WPF + BlazorWebView, .NET 10, three projects — `ChuvadiReader.Core` (all library usage), `ChuvadiReader.Ui` (Razor class library = the whole UI and design), `ChuvadiReader.Windows` (WPF host). Repo: `github.com/arunshivab/chuvadi-reader` (public).

**Goal of the programme:** the same app on Mac, Linux, Android and Web, with the existing design, built start to finish, tested extensively in a separate test chat, documented step by step, then pushed to `chuvadi-reader` as **one push per platform** after Arun checks it. Earliest production deployment is the priority.

### Hard rules (no exceptions)
1. **Design is final.** `ChuvadiReader.Ui` is the design — desktop, tablet and mobile layouts are all finalised. Do not change it. Only minor platform-native differences are allowed (e.g. Mac traffic lights on the left). Every platform must look the same and familiar.
2. **The app is UI only.** All processing comes from the Chuvadi libraries. If a capability is missing, never work around it in the app — write it down as a library ask for Arun.
3. **No externals.** All code is Arun's own, in C, C++ or C#. No third-party libraries, components or ported open-source code. Allowed: what ships in .NET itself (including MAUI, BlazorWebView / `Microsoft.AspNetCore.Components.WebView*`, Kestrel), OS components (WebView2, WKWebView, WebKitGTK, Android WebView, CUPS, Windows spooler). External tools are fine **for testing only**, never shipped.
4. **Existing files need approval.** Never edit an existing file of chuvadi-reader without approval. List each change with exact diffs, pros and cons, and risk to the Windows app, and send it to the coordinator. Arun has delegated decisions for this working repo to the coordinator (6 Nov); nothing reaches `arunshivab/chuvadi-reader` until Arun's final check. New files (new host projects, docs, CI) you may create yourself.
5. **No behaviour/API change on your own.** Any change to existing behaviour, defaults or output — bug fixes included, marked "bug fix" — is listed for Arun with pros and cons before it ships.
6. **The Reader chat is read-only for you.** You may ask it questions; never ask it to change anything, never edit its work.
7. **Fix every bug you find, however small.** No errors, no warnings, nothing deferred silently. Bugs inside your own new code you fix yourself; bugs in existing code go to Arun as a listed change (rule 4).
8. **Options rule (Arun, standing):** whenever there are options — design, architecture, tooling — give pros and cons for each and your recommendation. The coordinator discusses and finalises. Routine implementation inside your own new code you decide yourself, choosing the best option. Build the right thing first — no interim designs that get redone.
9. **Questions:** to the coordinator (or Arun) in plain chat text. Never use pop-up / multiple-choice question widgets.
10. **Git:** commit messages and PR descriptions never contain `Co-Authored-By`, `Claude-Session` or "Generated with Claude Code" lines. Commits are authored by Arun alone.
11. **Where to work:** the private working repo `Sthraas/chuvadi-reader-platforms`, on your own branch `platform/<name>`. Pushes to your own branch are authorized at every phase, and CI runs there. **Never push to `arunshivab/chuvadi-reader`, and never to `main` of the working repo** (it holds the coordination docs) — the push to chuvadi-reader happens only after the test chat passes and Arun checks.
12. **Documentation:** keep `docs/<platform>/BUILD-LOG.md` — a clean, dated, step-by-step record of everything done (what, why, commands, results). Plus `docs/<platform>/README.md`: how to build, run, package and install.

### Packages (from the library coordinator's report, 6 Nov 2026 — attached as `chuvadi-reader-platform-and-packages.md`)
- **PDF:** `chuvadi-pdf` **3.31.1**, individual packages (not the umbrella), all the same version, plus `Chuvadi.Fonts` **1.0.0**. chuvadi-pdf has no GitHub release assets — build the packages in your sandbox with `dotnet pack` from the **unchanged** tag `v3.31.1` of `github.com/arunshivab/chuvadi-pdf`, into a local feed. Never modify library code.
- **Sheets:** `Chuvadi.Sheets` **2.0.1** (release asset sheets-v2.0.1). Avoid `ToXlsx<T>` / `ReadXlsx<T>` in trimmed/AOT builds.
- **Zip:** `Chuvadi.Zip` **1.0.0**. **Print:** `Chuvadi.Print`, `.Ipp`, `.Windows` **1.0.0-rc.2** (`.Remote` only for hub/agent printing).
- **Docs (Word):** wait for docs-v2.0.0; 1.5.1 is a stop-gap only with Arun's approval.
- **Layout** (Docs/Sheets viewing, printing, Save as PDF) is **not released**, and `Layout.Pdf` pins chuvadi-pdf to [3.30.2]. Record this as a blocker; don't work around it.
- All Chuvadi packages are .nupkg from GitHub releases (`github.com/arunshivab/chuvadi/releases`), never nuget.org — use a local feed.
- Known library issues for servers (Web): Pdf A (name table never shrinks) and Pdf B (shared LiPi FontRenderer race). These are Arun's library decisions — record as blockers.

### Reporting
End every working session with a short status: done, in progress, blocked (and on what), questions for Arun. Keep the coordinator able to read your latest message and know exactly where you stand.

### Decision authority (Arun, 6 Nov 05:21)
Arun has handed the calls on this programme to the coordinator. The coordinator decides **only after** the chat has laid out every option with pros and cons and a recommendation, and the coordinator has discussed it. No chat decides an option on its own, and the coordinator never decides without the pros and cons in front of it.

### Arun's decisions so far (6 Nov)
- Web: no server storage for now (files not kept after the session); users managed by Sangam; never change Sangam — integrate as a client with our own code; sharing not in this release; TLS source pending (Pezhai being checked).
- Mac: universal app. Android: minimum Android 15, Play Store. Linux: Ubuntu x64 + ARM64, own WebKitGTK host.
- Everything follows the design handout; the only departure is per-user server storage on the web portal (none for now).
- Look: the handout in `docs/design-handoff/` (see `docs/coordination/DESIGN-NOTE.md`). Android phone/tablet look is built by the **Mobile app UI** chat (`platform/mobile-ui`); the web portal look by the **Web portal UI** chat (`platform/web-ui`); Mac and Linux chats define their own chrome.
