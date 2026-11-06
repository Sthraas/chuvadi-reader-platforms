# Chuvadi Reader for macOS

.NET MAUI Blazor Hybrid on Mac Catalyst. One universal app for Apple Silicon and Intel Macs,
macOS 12 Monterey or later. Project: `src/ChuvadiReader.Mac`.

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

CI pins: workload set `10.0.401` (Mac Catalyst 26.5.10318) and `/Applications/Xcode_26.6.app`. Move both forward together when the runner image carries the Xcode a newer workload needs.

Without a Mac: run the **Mac** workflow by hand (Actions → Mac → Run workflow, branch `platform/mac`) — it
builds, tests, verifies the bundle layout, smoke-launches and uploads `Chuvadi-mac-universal-unsigned.zip`.
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
