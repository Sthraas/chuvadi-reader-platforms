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
# → src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/ChuvadiReader.Mac.app (arm64 + x86_64)
codesign --force --deep --sign - src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/ChuvadiReader.Mac.app
```
Run: `open src/ChuvadiReader.Mac/bin/Release/net10.0-maccatalyst/ChuvadiReader.Mac.app`

Without a Mac: push to `platform/mac`; the **Mac** workflow builds, tests, smoke-launches and uploads
`Chuvadi-mac-universal-unsigned.zip`.

## Installing the unsigned test build on a Mac
The app is ad-hoc signed, not signed by an Apple Developer ID, so macOS blocks it on first open.
1. Download `Chuvadi-mac-universal-unsigned.zip` from the workflow run's Artifacts and double-click it
   (GitHub wraps it in a second zip — unzip until you see `ChuvadiReader.Mac.app`).
2. Drag `ChuvadiReader.Mac.app` into **Applications**.
3. Double-click it. macOS says it "cannot be opened because Apple cannot check it for malicious
   software" (or "cannot verify the developer"). Click **Done** / **Cancel**.
4. Open **System Settings → Privacy & Security**, scroll to the message about Chuvadi, click
   **Open Anyway**, enter your password, then **Open**. (On macOS 14 and earlier, Control-click the app
   in Applications → **Open** → **Open** also works.)
5. Alternative in Terminal: `xattr -dr com.apple.quarantine /Applications/ChuvadiReader.Mac.app`,
   then open normally.

Only the first launch needs this. App state: `~/Library/Application Support/Chuvadi`; logs and
startup timings: `~/Library/Logs/Chuvadi`.

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
  (or an App Store Connect API key) `--wait`, then `xcrun stapler staple ChuvadiReader.Mac.app`.
- Usually shipped as a signed, notarised **.dmg** (`hdiutil create`), itself signed and notarised.
- **Mac App Store** instead: different certificate (Apple Distribution + installer), App Sandbox
  required, provisioning profile, App Store review. The sandbox would require security-scoped bookmarks
  for Recent files and watched folders, which Core's path-based model doesn't have today.

## Open decisions (for Arun)
See the latest status message from the Mac chat; summary:
1. Window chrome (HTML dots top-right vs native traffic lights top-left vs standard title bar).
2. Print path (native macOS print panel fed by Chuvadi.Pdf's rasteriser vs Chuvadi.Print.Ipp over CUPS).
3. One MAUI project shared with Android, or two.
4. Bundle identifier (provisional: `in.sthraas.chuvadi.reader`).
5. Distribution: direct download (not sandboxed) vs Mac App Store (sandbox).
6. Ui hooks: ⌘ shortcut labels; Mac menu bar commands.
