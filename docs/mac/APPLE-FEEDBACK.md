# Apple Feedback drafts (Mac chat)

Reports to file with Apple through Feedback Assistant (by Arun, from a Mac with a developer account). Each one has
what Apple asks for: what happens, steps, expected, actual, the evidence and the system.

## FB-1 — macOS 26: AXPress on a WKWebView button crashes the WebContent process

**Area:** Accessibility / WebKit (Mac Catalyst app with a WKWebView).

**What happens.** An assistive app (VoiceOver, Voice Control, or any AX client) performs `AXPress` on a button inside
web content. macOS 26's accessibility layer turns the press into a synthetic mouse click and reads index 0 of an
empty Swift array, so the web content process stops on an assertion (`EXC_BREAKPOINT`). The page is lost. A real
mouse click on the same button works, and macOS 15 handles the same press without trouble.

**Steps.**
1. On macOS 26.7.2 (Apple silicon), open Chuvadi (a Mac Catalyst app; the Ui is a WKWebView).
2. Open Settings in the app, then use VoiceOver (VO-Space), or any AX client sending `AXPress`, on the
   "Appearance" button in the left-hand list.

**Expected.** The button is pressed, as with a mouse click.

**Actual.** `com.apple.WebKit.WebContent` crashes. The app's WKWebView gets
`webViewWebContentProcessDidTerminate:`.

**Backtrace (WebContent, crashing thread):**
```
_assertionFailure(_:_:file:line:flags:)                         libswiftCore
closure #1 in __SwiftNativeNSArrayWithContiguousStorage._objectAt(_:)
__EmptyArrayStorage._withVerbatimBridgedUnsafeBuffer<A>(_:)
@objc __SwiftNativeNSArrayWithContiguousStorage.objectAtSubscript(_:)
-[AXPMacPlatformElement _synthesizeMouseClick:]
-[AXPMacPlatformElement accessibilityPerformPress]
NSAccessibilityPerformEntryPointBOOL
NSAccessibilityEntryPointPerformAction
_AXXMIGPerformAction
… WebKit::XPCServiceMain
```
Full report: `docs/mac-test/evidence/M-18-83207af-WebContent-crash-AXPress-macos26.ips` (branch platform/mac-test).

**System.** macOS 26.7.2 (GitHub `macos-26-arm64` runner, Apple M1 virtual). Not seen on macOS 15.7.

**What the app does meanwhile.** It catches the termination callback, logs it, reopens the same screen in a fresh web
view and shows a plain message (D-154). See Mac Test M-18.
