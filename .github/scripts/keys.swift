// TESTING ONLY (Mac smoke run, never shipped): posts a real key press to the app named by bundle ID, through the
// HID event tap — the path a person's keyboard takes. Needs Post Event access (granted by grant-post-event.py).
//   keys <bundle-id> escape | ctrl-cmd-f | return
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: keys <bundle-id> <key|ax-walk|ax-press label>"); exit(2) }

// ax-press <label>: press an element by its accessible name, as VoiceOver / Voice Control / the Mac Test driver do
// (AXPress, not a mouse click). The app's full accessibility tree is switched on first, as assistive apps do.
if args[2] == "ax-press", args.count == 4 {
    guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: args[1]).first else { print("not running"); exit(1) }
    let root = AXUIElementCreateApplication(app.processIdentifier)
    AXUIElementSetMessagingTimeout(root, 5) // web content answers slowly; the default gives up before it does
    AXUIElementSetAttributeValue(root, "AXManualAccessibility" as CFString, kCFBooleanTrue)
    AXUIElementSetAttributeValue(root, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
    usleep(1_500_000)
    let label = args[3]
    var found: AXUIElement?
    var seen = 0
    func str(_ e: AXUIElement, _ a: String) -> String? {
        var v: CFTypeRef?
        return AXUIElementCopyAttributeValue(e, a as CFString, &v) == .success ? v as? String : nil
    }
    func walk(_ e: AXUIElement, _ depth: Int) {
        if found != nil || depth > 60 || seen > 30000 { return }
        seen += 1
        let role = str(e, kAXRoleAttribute) ?? ""
        let names = [str(e, kAXTitleAttribute), str(e, kAXDescriptionAttribute), str(e, kAXHelpAttribute), str(e, kAXValueAttribute)].compactMap { $0 }
        if role != "AXStaticText" && names.contains(where: { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == label.lowercased() }) {
            found = e; print("ax-press target role=\(role)"); return
        }
        var kids: CFTypeRef?
        if AXUIElementCopyAttributeValue(e, kAXChildrenAttribute as CFString, &kids) == .success, let list = kids as? [AXUIElement] {
            for k in list where str(k, kAXRoleAttribute) != "AXMenuBar" { walk(k, depth + 1) }
        }
    }
    walk(root, 0)
    guard let target = found else { print("ax-press: no button named \(label) (\(seen) elements)"); exit(1) }
    let r = AXUIElementPerformAction(target, kAXPressAction as CFString)
    print("ax-press \(label): \(r.rawValue) (\(seen) elements searched)")
    exit(0)
}

// ax-walk: read the app's accessibility tree, as VoiceOver or the Mac Test driver does (makes WebKit build its own).
if args[2] == "ax-walk" {
    guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: args[1]).first else { print("not running"); exit(1) }
    let root = AXUIElementCreateApplication(app.processIdentifier)
    var count = 0, webAreas = 0
    func walk(_ e: AXUIElement, _ depth: Int) {
        if depth > 40 || count > 20000 { return }
        count += 1
        var role: CFTypeRef?
        if AXUIElementCopyAttributeValue(e, kAXRoleAttribute as CFString, &role) == .success, (role as? String) == "AXWebArea" { webAreas += 1 }
        var title: CFTypeRef?
        _ = AXUIElementCopyAttributeValue(e, kAXTitleAttribute as CFString, &title)
        var kids: CFTypeRef?
        if AXUIElementCopyAttributeValue(e, kAXChildrenAttribute as CFString, &kids) == .success, let list = kids as? [AXUIElement] {
            for k in list { walk(k, depth + 1) }
        }
    }
    walk(root, 0)
    print("ax-walk nodes=\(count) webAreas=\(webAreas) trusted=\(AXIsProcessTrusted())")
    exit(0)
}
for app in NSRunningApplication.runningApplications(withBundleIdentifier: args[1]) {
    app.activate(options: [.activateAllWindows])
}
usleep(600_000)
let keys: [String: (CGKeyCode, CGEventFlags)] = [
    "escape": (53, []),
    "return": (36, []),
    "ctrl-cmd-f": (3, [.maskControl, .maskCommand]),
    "cmd-k": (40, [.maskCommand]),
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
