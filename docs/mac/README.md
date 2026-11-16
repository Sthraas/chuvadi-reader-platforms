# Chuvadi Reader for macOS

.NET MAUI Blazor Hybrid on Mac Catalyst. One universal app for Apple Silicon and Intel Macs,
macOS 14 Sonoma or later (D-195). Project: `src/ChuvadiReader.Mac`.

## Build (on a Mac)
Needs the .NET 10 SDK and Xcode (the version the .NET 10 Mac Catalyst workload requires; CI uses the
newest on the runner).
```bash
dotnet workload install maui-maccatalyst
dotnet restore src/ChuvadiReader.Mac/ChuvadiReader.Mac.csproj --configfile ci/nuget.config
dotnet build   src/ChuvadiReader.Mac/ChuvadiReader.Mac.csproj -c Release --no-restore
# → src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/Chuvadi.app (arm64 + x86_64)
codesign --force --deep --sign - src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/Chuvadi.app
```
Run: `open src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/Chuvadi.app` (always through `open` or Finder — a Mac Catalyst app started by running its binary directly aborts).

CI pins: the repo `global.json` as pushed (SDK 10.0.403, workload set 10.0.403 = Mac Catalyst 27.0) and Xcode 27.1,
on the `xcode-27` runner (arm64, macOS 27; a GitHub public-preview image). Building by hand needs the same: Xcode 27.1
or later, on an Apple Silicon or Intel Mac. One build makes both slices — the Intel (x86_64) slice is compiled on the
arm64 runner (`RuntimeIdentifiers` maccatalyst-arm64;maccatalyst-x64) and merged with the arm64 slice into one
universal bundle. That one zip is then tested on `macos-26`, `macos-15`, `macos-15-intel` and `xcode-27`.

**If the build runner changes** (it is a preview image): the workflow names `/Applications/Xcode_27.1.app` when the
image has it, so a new default Xcode does not change the build, and it stops with a plain message if Xcode is older
than 27.1. If the `xcode-27` label goes away, run the workflow with its `build_runner` input set to any label that
carries Xcode 27.1 or later (the regular macOS 27 image once GitHub ships it) — no file changes. If no hosted image
has it, the build needs a Mac with Xcode 27.1 (a self-hosted runner or by hand, steps above) until one does; the tests
and smoke on macOS 26 and 15 are not affected. Building on an older workload set is not a fallback: the 10.0.401
runner swap was retired with D-195.

Without a Mac: run the **Mac** workflow by hand (Actions → Mac → Run workflow, branch `platform/mac`) — it
builds, tests, verifies the bundle layout, smoke-launches and uploads `Chuvadi-mac-universal-unsigned.zip`.
The smoke step (`.github/scripts/mac-smoke.sh`) runs the app with `CHUVADI_SMOKE=1` and checks the Mac Test fixes on
the runner: files handed over at launch and while running, single instance, the Reader rendering with no Ui error, the
real menu bar, window size and position, the page reaching the top edge, .NET message text, a clean quit, and the
startup breakdown. `CHUVADI_SMOKE` is never set for a person; without it the app prints nothing extra.
Both Mac workflows are manual only (D-90: macOS minutes cost 10× Linux).

## Installing the unsigned test build on a Mac
The app is ad-hoc signed, not signed by an Apple Developer ID, so macOS blocks it on first open.
1. Download `Chuvadi-mac-universal-unsigned.zip` from the workflow run's Artifacts and double-click it
   (GitHub wraps it in a second zip — unzip until you see `Chuvadi.app`).
2. Drag `Chuvadi.app` into **Applications**.
3. Double-click it. macOS says it "cannot be opened because Apple cannot check it for malicious
   software" (or "cannot verify the developer"). Click **Done** / **Cancel**.
4. Open **System Settings → Privacy & Security**, scroll to the message about Chuvadi, click
   **Open Anyway**, enter your password, then **Open**. (On macOS 14 and earlier, Control-click the app
   in Applications → **Open** → **Open** also works.)
5. Alternative in Terminal: `xattr -dr com.apple.quarantine /Applications/Chuvadi.app`,
   then open normally.

Only the first launch needs this. App state: `~/Library/Application Support/Chuvadi`; logs and
startup timings: `~/Library/Logs/Chuvadi`.

## What is in the bundle (legal)
`Chuvadi.app/Contents/Info.plist` → `NSHumanReadableCopyright` = `Copyright © 2026 Sthraas Intelligence Pvt Ltd. All rights reserved.`
`Chuvadi.app/Contents/Resources/legal/`:

| File | From | Notes |
|---|---|---|
| `LICENSE.txt` | repo `LICENSE` | DRAFT |
| `EULA.txt` | `legal/EULA.txt` | DRAFT; shown on the DMG licence page once there is a DMG |
| `THIRD-PARTY-NOTICES.txt` | `legal/THIRD-PARTY-NOTICES.txt` | DRAFT |
| `DOTNET-RUNTIME-THIRD-PARTY-NOTICES.txt` | `THIRD-PARTY-NOTICES.TXT` of the Mono runtime pack the build resolved | taken at build time |
| `DOTNET-MACCATALYST-LICENSE.txt` | `LICENSE` of the .NET for Mac Catalyst runtime pack the build resolved | taken at build time |

The last two form the **.NET runtime** tab on Settings › About › Licences (`MacHostNotices`, D-84). The build
fails if either can't be found in the resolved packs.

## Error log (D-132)
Warnings and errors go to `~/Library/Logs/Chuvadi/chuvadi.log` (Console.app › Log Reports), rolled at 512 KB to
`chuvadi.1.log` — about 1 MB in all, never sent anywhere. File names appear only as extension + short hash, quoted values
as a hash, links as scheme and host (`Platform/LogScrubber.cs`). To diagnose a failure, ask for these two files.

## Signing and notarisation (later — not done)
Needed for a normal double-click install with no warning:
- **Apple Developer Program** membership (organisation account for Sthraas / imagiQa: D-U-N-S number,
  US$99 per year).
- A **Developer ID Application** certificate (for distribution outside the App Store), kept in the CI
  secrets as a .p12 + password, imported into a temporary keychain on the runner.
- Build with `EnableCodeSigning=true`, `CodesignKey="Developer ID Application: …"`,
  `CodesignEntitlements=Platforms/MacCatalyst/Entitlements.plist`, and the **hardened runtime**
  (`UseHardenedRuntime=true`). .NET needs the `com.apple.security.cs.allow-jit` entitlement under the
  hardened runtime.
- **Notarise**: `xcrun notarytool submit Chuvadi.zip --apple-id … --team-id … --password <app-specific>`
  (or an App Store Connect API key) `--wait`, then `xcrun stapler staple Chuvadi.app`.
- Usually shipped as a signed, notarised **.dmg** (`hdiutil create`), itself signed and notarised.
- **Mac App Store** instead: different certificate (Apple Distribution + installer), App Sandbox
  required, provisioning profile, App Store review. The sandbox would require security-scoped bookmarks
  for Recent files and watched folders, which Core's path-based model doesn't have today.

## Decisions (coordinator, 6 Nov 2026)
- Separate `ChuvadiReader.Mac` project on the Foundation kit; window chrome and menu bar per the handout.
- Printing: native macOS print panel fed a vector PDF prepared by chuvadi-pdf (never rasterised).
- ⌘ labels: Foundation `Keys.Format`. Immersive: ⌃⌘F in the Mac menu.
- Distribution: direct download, signed and notarised, not sandboxed; App Store later.
- Publisher: Sthraas Intelligence Pvt Ltd. Apple Developer account after company registration — unsigned test
  builds until then. Bundle ID `in.sthraas.chuvadi.reader` is provisional until the final domain (likely
  chuvadi.in) is chosen; nothing is signed with it.
- CI keeps the workload pin until the runner image has the Xcode the next workload needs.
