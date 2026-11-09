// TESTING ONLY (Mac smoke run, never shipped): posts a real key press to the app named by bundle ID, through the
// HID event tap — the path a person's keyboard takes. Needs Post Event access (granted by grant-post-event.py).
//   keys <bundle-id> escape | ctrl-cmd-f | return
import AppKit

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: keys <bundle-id> <key>"); exit(2) }
for app in NSRunningApplication.runningApplications(withBundleIdentifier: args[1]) {
    app.activate(options: [.activateAllWindows])
}
usleep(600_000)
let keys: [String: (CGKeyCode, CGEventFlags)] = [
    "escape": (53, []),
    "return": (36, []),
    "ctrl-cmd-f": (3, [.maskControl, .maskCommand]),
]
guard let (code, flags) = keys[args[2]] else { print("unknown key \(args[2])"); exit(2) }
let src = CGEventSource(stateID: .hidSystemState)
let down = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: true)!
down.flags = flags
let up = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: false)!
up.flags = flags
down.post(tap: .cghidEventTap)
usleep(60_000)
up.post(tap: .cghidEventTap)
print("posted \(args[2]) to \(args[1]), trusted=\(AXIsProcessTrusted())")
