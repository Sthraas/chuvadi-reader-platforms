// Mac Test driver — TESTING ONLY, never shipped. Arun's own code (Swift, Apple frameworks only).
// Drives and observes Chuvadi.app from outside: Accessibility (AX) tree and actions, CGEvent keyboard/mouse,
// window capture (CGWindowList), menu-bar walk, Launch Services queries, pasteboard, display modes, and a
// first-frame startup probe that never relies on the app's own timings.
//
//   swiftc -O tests/mac/macdrive.swift -o macdrive
//   macdrive trust                                   AX / screen-capture permission state
//   macdrive firstframe <app> [file] <out-dir> [--label L] [--timeout S]   launch via NSWorkspace, time frames
//   macdrive windows                                 on-screen windows (owner, pid, id, bounds)
//   macdrive capture <name|pid> <out.png>            capture the app's main window (best resolution)
//   macdrive axdump <name|pid> <out.txt>             whole AX tree of the app (menus excluded)
//   macdrive menudump <name|pid> <out.json> [--live] menu bar with shortcuts and enabled state
//   macdrive menu <name|pid> <Top> <Item> [<Sub>...] press a menu item by its titles
//   macdrive press <name|pid> <text> [--contains] [--role R] [--index N]   AXPress (or click) an element
//   macdrive find <name|pid> <text> [--contains] [--timeout S]  wait for an element; prints its frame
//   macdrive click <x> <y> [--double] | rclick <x> <y> | move <x> <y>   (screen points)
//   macdrive key <combo>        e.g. cmd+o, cmd+shift+g, ctrl+cmd+f, escape, return, tab, 1
//   macdrive type <text>        types Unicode text
//   macdrive winstate <name|pid>   AX window attributes (position, size, fullscreen, minimized, zoomed guess)
//   macdrive lsquery <file>        default app and every app that can open the file
//   macdrive pasteboard <out-dir>  pasteboard types; writes text.txt / image.png if present
//   macdrive displays [--hidpi]    display modes; --hidpi switches the main display to a HiDPI mode if one exists
//   macdrive activate <name|pid>
//   macdrive quit <name|pid> [--force]
import AppKit
import ApplicationServices
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

setvbuf(stdout, nil, _IOLBF, 0)

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(2)
}

func now() -> Double { Double(DispatchTime.now().uptimeNanoseconds) / 1_000_000.0 }

// MARK: - process lookup

func pidOf(_ nameOrPid: String) -> pid_t {
    if let p = Int32(nameOrPid) { return p }
    let apps = NSWorkspace.shared.runningApplications.filter {
        $0.localizedName == nameOrPid || $0.bundleIdentifier == nameOrPid
            || $0.executableURL?.lastPathComponent == nameOrPid
    }
    guard let a = apps.first else { fail("no running app '\(nameOrPid)'") }
    return a.processIdentifier
}

func processStartMs(_ pid: pid_t) -> Double? {
    var info = kinfo_proc()
    var size = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0 else { return nil }
    let tv = info.kp_proc.p_un.__p_starttime
    let startEpoch = Double(tv.tv_sec) * 1000 + Double(tv.tv_usec) / 1000
    // convert epoch → our uptime clock
    let nowEpoch = Date().timeIntervalSince1970 * 1000
    return now() - (nowEpoch - startEpoch)
}

// MARK: - windows and capture

struct Win { let id: CGWindowID; let pid: pid_t; let owner: String; let bounds: CGRect; let layer: Int; let name: String }

func windows(pid: pid_t? = nil) -> [Win] {
    guard let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else { return [] }
    return list.compactMap { d in
        guard let id = d[kCGWindowNumber as String] as? UInt32,
              let p = d[kCGWindowOwnerPID as String] as? Int32,
              let bd = d[kCGWindowBounds as String] as? NSDictionary,
              let r = CGRect(dictionaryRepresentation: bd as CFDictionary) else { return nil }
        if let pid, p != pid { return nil }
        return Win(id: id, pid: p, owner: d[kCGWindowOwnerName as String] as? String ?? "",
                   bounds: r, layer: d[kCGWindowLayer as String] as? Int ?? 0, name: d[kCGWindowName as String] as? String ?? "")
    }
}

func mainWindow(pid: pid_t) -> Win? {
    windows(pid: pid).filter { $0.layer == 0 && $0.bounds.width > 200 && $0.bounds.height > 150 }
        .max { $0.bounds.width * $0.bounds.height < $1.bounds.width * $1.bounds.height }
}

typealias CreateImageFn = @convention(c) (CGRect, UInt32, UInt32, UInt32) -> Unmanaged<CGImage>?
let createImage: CreateImageFn? = {
    guard let sym = dlsym(UnsafeMutableRawPointer(bitPattern: -2), "CGWindowListCreateImage") else { return nil }
    return unsafeBitCast(sym, to: CreateImageFn.self)
}()

func captureWindow(_ id: CGWindowID) -> CGImage? {
    guard let f = createImage else { return nil }
    // kCGWindowListOptionIncludingWindow = 1<<3; boundsIgnoreFraming = 1<<0, bestResolution = 1<<3
    return f(.null, 1 << 3, id, (1 << 0) | (1 << 3))?.takeRetainedValue()
}

func savePNG(_ img: CGImage, _ path: String) {
    let url = URL(fileURLWithPath: path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    guard let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else { return }
    CGImageDestinationAddImage(dest, img, nil)
    CGImageDestinationFinalize(dest)
}

struct FrameStats { var colors = 0; var whiteFrac = 0.0; var darkInWhite = 0; var w = 0; var h = 0 }

func analyse(_ img: CGImage) -> FrameStats {
    let w = img.width, h = img.height
    var s = FrameStats(); s.w = w; s.h = h
    guard w > 0, h > 0 else { return s }
    var buf = [UInt8](repeating: 0, count: w * h * 4)
    guard let ctx = CGContext(data: &buf, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return s }
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
    var seen = Set<Int>()
    var white = 0, total = 0
    var minX = w, minY = h, maxX = -1, maxY = -1
    let step = 2
    var y = 0
    while y < h {
        var x = 0
        let row = y * w * 4
        while x < w {
            let i = row + x * 4
            let r = Int(buf[i]), g = Int(buf[i + 1]), b = Int(buf[i + 2])
            seen.insert(((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3))
            if r >= 252 && g >= 252 && b >= 252 {
                white += 1
                if x < minX { minX = x }; if x > maxX { maxX = x }
                if y < minY { minY = y }; if y > maxY { maxY = y }
            }
            total += 1
            x += step
        }
        y += step
    }
    s.colors = seen.count
    s.whiteFrac = total > 0 ? Double(white) / Double(total) : 0
    if maxX > minX && maxY > minY && s.whiteFrac > 0.05 {
        var dark = 0
        var yy = minY
        while yy <= maxY {
            var xx = minX
            while xx <= maxX {
                let i = yy * w * 4 + xx * 4
                if Int(buf[i]) + Int(buf[i + 1]) + Int(buf[i + 2]) < 240 { dark += 1 }
                xx += step
            }
            yy += step
        }
        s.darkInWhite = dark
    }
    return s
}

// MARK: - firstframe probe

func firstFrame(app: String, file: String?, outDir: String, label: String, timeout: Double) {
    let appURL = URL(fileURLWithPath: app)
    guard let bundle = Bundle(url: appURL), let bid = bundle.bundleIdentifier else { fail("not an app: \(app)") }
    if !NSRunningApplication.runningApplications(withBundleIdentifier: bid).isEmpty { fail("app already running") }
    try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
    let cfg = NSWorkspace.OpenConfiguration()
    cfg.activates = true
    cfg.addsToRecentItems = false
    let t0 = now()
    if let file {
        NSWorkspace.shared.open([URL(fileURLWithPath: file)], withApplicationAt: appURL, configuration: cfg) { _, e in
            if let e { FileHandle.standardError.write("open error: \(e)\n".data(using: .utf8)!) }
        }
    } else {
        NSWorkspace.shared.openApplication(at: appURL, configuration: cfg) { _, e in
            if let e { FileHandle.standardError.write("open error: \(e)\n".data(using: .utf8)!) }
        }
    }
    var pid: pid_t = 0
    var marks: [String: Double] = [:]
    var lastColors = -1
    var trace: [[String: Any]] = []
    var frames = 0
    var pidStart: Double?
    while now() - t0 < timeout * 1000 {
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.001))
        if pid == 0 {
            if let a = NSRunningApplication.runningApplications(withBundleIdentifier: bid).first {
                pid = a.processIdentifier
                marks["process_seen"] = now() - t0
                if let ps = processStartMs(pid) { pidStart = ps - t0; marks["process_start"] = ps - t0 }
            }
            continue
        }
        guard let win = mainWindow(pid: pid) else { continue }
        if marks["window"] == nil { marks["window"] = now() - t0 }
        let tCap = now() - t0
        guard let img = captureWindow(win.id) else { marks["capture_failed"] = tCap; break }
        frames += 1
        let st = analyse(img)
        if st.colors != lastColors {
            trace.append(["t": round(tCap * 10) / 10, "colors": st.colors, "white": round(st.whiteFrac * 1000) / 1000, "dark": st.darkInWhite])
            lastColors = st.colors
        }
        if marks["first_paint"] == nil && st.colors >= 4 { marks["first_paint"] = tCap; savePNG(img, "\(outDir)/\(label)-first-paint.png") }
        if marks["first_render"] == nil && st.colors >= 40 { marks["first_render"] = tCap; savePNG(img, "\(outDir)/\(label)-first-render.png") }
        if file != nil && marks["first_page"] == nil && st.whiteFrac >= 0.08 && st.darkInWhite >= 150 {
            marks["first_page"] = tCap; savePNG(img, "\(outDir)/\(label)-first-page.png")
        }
        let done = file == nil ? marks["first_render"] != nil : marks["first_page"] != nil
        if done {
            // settle: one more frame 1.5 s later for the record
            Thread.sleep(forTimeInterval: 1.5)
            if let img2 = captureWindow(win.id) { savePNG(img2, "\(outDir)/\(label)-settled.png") }
            break
        }
    }
    marks["frames"] = Double(frames)
    var result: [String: Any] = ["label": label, "file": file ?? "", "pid": pid, "marks": marks, "trace": trace]
    if let pidStart { result["process_start_ms"] = pidStart }
    let data = try! JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
    FileManager.default.createFile(atPath: "\(outDir)/\(label).json", contents: data)
    print(String(data: data, encoding: .utf8)!)
}

// MARK: - AX helpers

func ax(_ el: AXUIElement, _ attr: String) -> AnyObject? {
    var v: AnyObject?
    return AXUIElementCopyAttributeValue(el, attr as CFString, &v) == .success ? v : nil
}

func axStr(_ el: AXUIElement, _ attr: String) -> String {
    guard let v = ax(el, attr) else { return "" }
    if let s = v as? String { return s }
    if let n = v as? NSNumber { return n.stringValue }
    return ""
}

func axChildren(_ el: AXUIElement) -> [AXUIElement] { (ax(el, kAXChildrenAttribute) as? [AXUIElement]) ?? [] }

func axFrame(_ el: AXUIElement) -> CGRect? {
    guard let p = ax(el, kAXPositionAttribute), let s = ax(el, kAXSizeAttribute) else { return nil }
    var pt = CGPoint.zero, sz = CGSize.zero
    AXValueGetValue(p as! AXValue, .cgPoint, &pt)
    AXValueGetValue(s as! AXValue, .cgSize, &sz)
    return CGRect(origin: pt, size: sz)
}

func appElement(_ pid: pid_t) -> AXUIElement {
    let e = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(e, 5)
    return e
}

func describe(_ el: AXUIElement) -> String {
    let role = axStr(el, kAXRoleAttribute), sub = axStr(el, kAXSubroleAttribute)
    var s = role + (sub.isEmpty ? "" : "[\(sub)]")
    for (k, a) in [("title", kAXTitleAttribute), ("desc", kAXDescriptionAttribute), ("value", kAXValueAttribute),
                   ("help", kAXHelpAttribute), ("id", "AXDOMIdentifier"), ("class", "AXDOMClassList")] {
        var v = axStr(el, a)
        if k == "class", let arr = ax(el, a) as? [String] { v = arr.joined(separator: " ") }
        if !v.isEmpty { s += " \(k)=\"\(v.replacingOccurrences(of: "\n", with: "⏎").prefix(160))\"" }
    }
    if let f = axFrame(el) { s += String(format: " @%.0f,%.0f %.0fx%.0f", f.minX, f.minY, f.width, f.height) }
    if let en = ax(el, kAXEnabledAttribute) as? Bool, !en { s += " disabled" }
    return s
}

func walk(_ el: AXUIElement, depth: Int = 0, maxDepth: Int = 80, skipMenus: Bool = true, visit: (AXUIElement, Int) -> Bool) {
    if !visit(el, depth) || depth >= maxDepth { return }
    for c in axChildren(el) {
        if skipMenus && axStr(c, kAXRoleAttribute) == "AXMenuBar" { continue }
        walk(c, depth: depth + 1, maxDepth: maxDepth, skipMenus: skipMenus, visit: visit)
    }
}

func axDump(_ pid: pid_t, _ out: String) {
    var lines: [String] = []
    walk(appElement(pid)) { el, d in
        lines.append(String(repeating: "  ", count: d) + describe(el))
        return lines.count < 40000
    }
    try? lines.joined(separator: "\n").write(toFile: out, atomically: true, encoding: .utf8)
    print("\(lines.count) elements → \(out)")
}

func matches(_ el: AXUIElement, _ text: String, contains: Bool, role: String?) -> Bool {
    if let role, axStr(el, kAXRoleAttribute) != role { return false }
    let t = text.lowercased()
    for a in [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute, kAXValueAttribute, "AXDOMIdentifier"] {
        let v = axStr(el, a).lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if v.isEmpty { continue }
        if contains ? v.contains(t) : v == t { return true }
    }
    return false
}

func findAll(_ pid: pid_t, _ text: String, contains: Bool, role: String?) -> [AXUIElement] {
    var found: [AXUIElement] = []
    walk(appElement(pid)) { el, _ in
        if matches(el, text, contains: contains, role: role) { found.append(el) }
        return found.count < 200
    }
    return found
}

func clickAt(_ p: CGPoint, double: Bool = false, right: Bool = false) {
    let src = CGEventSource(stateID: .hidSystemState)
    let down: CGEventType = right ? .rightMouseDown : .leftMouseDown
    let up: CGEventType = right ? .rightMouseUp : .leftMouseUp
    let btn: CGMouseButton = right ? .right : .left
    CGEvent(mouseEventSource: src, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: btn)?.post(tap: .cghidEventTap)
    usleep(30_000)
    for n in 1...(double ? 2 : 1) {
        let d = CGEvent(mouseEventSource: src, mouseType: down, mouseCursorPosition: p, mouseButton: btn)!
        d.setIntegerValueField(.mouseEventClickState, value: Int64(n))
        d.post(tap: .cghidEventTap)
        usleep(20_000)
        let u = CGEvent(mouseEventSource: src, mouseType: up, mouseCursorPosition: p, mouseButton: btn)!
        u.setIntegerValueField(.mouseEventClickState, value: Int64(n))
        u.post(tap: .cghidEventTap)
        usleep(60_000)
    }
}

func press(_ el: AXUIElement) -> String {
    if AXUIElementPerformAction(el, kAXPressAction as CFString) == .success { return "AXPress" }
    if let f = axFrame(el) { clickAt(CGPoint(x: f.midX, y: f.midY)); return "click" }
    return "failed"
}

// MARK: - menus

func menuItems(_ menu: AXUIElement) -> [AXUIElement] {
    axChildren(menu).filter { axStr($0, kAXRoleAttribute) == "AXMenuItem" }
}

func modString(_ m: Int, _ hasChar: Bool) -> String {
    guard hasChar else { return "" }
    var s = ""
    if m & 4 != 0 { s += "⌃" }
    if m & 2 != 0 { s += "⌥" }
    if m & 1 != 0 { s += "⇧" }
    if m & 8 == 0 { s += "⌘" }
    return s
}

func menuJSON(_ item: AXUIElement) -> [String: Any] {
    let title = axStr(item, kAXTitleAttribute)
    let ch = axStr(item, "AXMenuItemCmdChar")
    let virt = ax(item, "AXMenuItemCmdVirtualKey") as? Int
    let mods = (ax(item, "AXMenuItemCmdModifiers") as? Int) ?? 0
    let glyph = ax(item, "AXMenuItemCmdGlyph") as? Int
    var d: [String: Any] = ["title": title, "enabled": (ax(item, kAXEnabledAttribute) as? Bool) ?? true]
    if !ch.isEmpty || virt != nil || glyph != nil {
        d["shortcut"] = modString(mods, true) + (ch.isEmpty ? "#\(virt ?? glyph ?? -1)" : ch)
    }
    if let mark = ax(item, "AXMenuItemMarkChar") as? String, !mark.isEmpty { d["mark"] = mark }
    if title.isEmpty && ch.isEmpty { d["separator"] = true }
    let subs = axChildren(item).filter { axStr($0, kAXRoleAttribute) == "AXMenu" }
    if let sub = subs.first { d["items"] = menuItems(sub).map(menuJSON) }
    return d
}

func menuBar(_ pid: pid_t) -> [AXUIElement] {
    guard let mb = ax(appElement(pid), kAXMenuBarAttribute) else { return [] }
    return axChildren(mb as! AXUIElement).filter { axStr($0, kAXRoleAttribute) == "AXMenuBarItem" }
}

func sendKey(_ combo: String) {
    let parts = combo.lowercased().split(separator: "+").map(String.init)
    var flags: CGEventFlags = []
    for p in parts.dropLast() {
        switch p {
        case "cmd": flags.insert(.maskCommand)
        case "shift": flags.insert(.maskShift)
        case "alt", "opt", "option": flags.insert(.maskAlternate)
        case "ctrl", "control": flags.insert(.maskControl)
        default: fail("bad modifier \(p)")
        }
    }
    let k = parts.last ?? ""
    let codes: [String: CGKeyCode] = [
        "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14,
        "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27,
        "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "return": 36, "enter": 36, "l": 37, "j": 38,
        "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "tab": 48, "space": 49, "`": 50,
        "delete": 51, "backspace": 51, "escape": 53, "esc": 53, "f11": 103, "left": 123, "right": 124, "down": 125, "up": 126,
        "home": 115, "end": 119, "pageup": 116, "pagedown": 121, "fwddelete": 117,
    ]
    guard let code = codes[k] else { fail("unknown key \(k)") }
    let src = CGEventSource(stateID: .hidSystemState)
    let d = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: true)!
    d.flags = flags
    d.post(tap: .cghidEventTap)
    usleep(60_000)  // same hold as the Mac smoke's keys.swift
    let u = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: false)!
    u.flags = flags
    u.post(tap: .cghidEventTap)
    usleep(40_000)
}

func typeText(_ s: String) {
    let src = CGEventSource(stateID: .hidSystemState)
    for ch in s {
        let u = Array(String(ch).utf16)
        let d = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: true)!
        d.keyboardSetUnicodeString(stringLength: u.count, unicodeString: u)
        d.post(tap: .cghidEventTap)
        let up = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: false)!
        up.keyboardSetUnicodeString(stringLength: u.count, unicodeString: u)
        up.post(tap: .cghidEventTap)
        usleep(12_000)
    }
}

// MARK: - commands

var args = Array(CommandLine.arguments.dropFirst())
func flag(_ name: String) -> Bool {
    if let i = args.firstIndex(of: name) { args.remove(at: i); return true }
    return false
}
func option(_ name: String) -> String? {
    if let i = args.firstIndex(of: name), i + 1 < args.count {
        let v = args[i + 1]; args.removeSubrange(i...(i + 1)); return v
    }
    return nil
}
func arg(_ i: Int) -> String {
    if i < args.count { return args[i] }
    fail("missing argument \(i)")
}

guard let cmd = args.first else { fail("usage: see header of macdrive.swift") }
args.removeFirst()

switch cmd {
case "trust":
    print("ax_trusted=\(AXIsProcessTrusted())")
    print("screen_capture_preflight=\(CGPreflightScreenCaptureAccess())")
    print("create_image_symbol=\(createImage != nil)")
    if let w = windows().first, let img = captureWindow(w.id) {
        print("capture_test=\(img.width)x\(img.height) of \(w.owner)")
    } else { print("capture_test=none") }

case "firstframe":
    let label = option("--label") ?? "run"
    let timeout = Double(option("--timeout") ?? "40") ?? 40
    if args.count == 2 { firstFrame(app: arg(0), file: nil, outDir: arg(1), label: label, timeout: timeout) }
    else { firstFrame(app: arg(0), file: arg(1), outDir: arg(2), label: label, timeout: timeout) }

case "waitpage":
    // waitpage <name|pid> <out-dir> <label> [--key combo] [--timeout S]: optionally send a key, then capture the
    // window until a white page with dark glyphs is on screen; prints the elapsed ms (from the key).
    let pid = pidOf(arg(0))
    let outDir = arg(1), label = arg(2)
    let key = option("--key")
    let timeout = Double(option("--timeout") ?? "30") ?? 30
    guard let w = mainWindow(pid: pid) else { fail("no window") }
    if let key { sendKey(key) }
    let t0 = now()
    var result: [String: Any] = ["label": label]
    while now() - t0 < timeout * 1000 {
        guard let img = captureWindow(w.id) else { break }
        let st = analyse(img)
        if st.whiteFrac >= 0.08 && st.darkInWhite >= 150 {
            let ms = now() - t0
            result["first_page"] = ms
            savePNG(img, "\(outDir)/\(label)-first-page.png")
            break
        }
    }
    if result["first_page"] == nil, let img = captureWindow(w.id) { savePNG(img, "\(outDir)/\(label)-timeout.png") }
    let data = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    FileManager.default.createFile(atPath: "\(outDir)/\(label).json", contents: data)
    print(String(data: data, encoding: .utf8)!)

case "windows":
    for w in windows() { print("\(w.owner)\tpid=\(w.pid)\tid=\(w.id)\tlayer=\(w.layer)\t\(Int(w.bounds.minX)),\(Int(w.bounds.minY)) \(Int(w.bounds.width))x\(Int(w.bounds.height))\t\(w.name)") }

case "capture":
    let pid = pidOf(arg(0))
    guard let w = mainWindow(pid: pid) else { fail("no window") }
    guard let img = captureWindow(w.id) else { fail("capture failed") }
    savePNG(img, arg(1))
    print("\(img.width)x\(img.height) window \(Int(w.bounds.width))x\(Int(w.bounds.height)) pt → \(arg(1))")

case "axdump":
    axDump(pidOf(arg(0)), arg(1))

case "menudump":
    let pid = pidOf(arg(0))
    let live = flag("--live")
    var menus: [[String: Any]] = []
    for top in menuBar(pid) {
        let title = axStr(top, kAXTitleAttribute)
        if live { _ = AXUIElementPerformAction(top, kAXPressAction as CFString); usleep(400_000) }
        let sub = axChildren(top).first { axStr($0, kAXRoleAttribute) == "AXMenu" }
        menus.append(["title": title, "items": sub.map { menuItems($0).map(menuJSON) } ?? []])
        if live { sendKey("escape"); usleep(200_000) }
    }
    let data = try! JSONSerialization.data(withJSONObject: menus, options: [.prettyPrinted])
    FileManager.default.createFile(atPath: arg(1), contents: data)
    print("menus: " + menus.map { $0["title"] as! String }.joined(separator: " | "))

case "menu":
    let pid = pidOf(arg(0))
    let path = Array(args.dropFirst())
    guard let top = menuBar(pid).first(where: { axStr($0, kAXTitleAttribute) == path.first }) else { fail("no menu \(path.first ?? "")") }
    var current = top
    for title in path.dropFirst() {
        guard let menu = axChildren(current).first(where: { axStr($0, kAXRoleAttribute) == "AXMenu" }) else { fail("no submenu under \(axStr(current, kAXTitleAttribute))") }
        guard let item = menuItems(menu).first(where: { axStr($0, kAXTitleAttribute) == title }) else {
            fail("no item '\(title)'; have: " + menuItems(menu).map { axStr($0, kAXTitleAttribute) }.joined(separator: " | "))
        }
        current = item
    }
    let en = (ax(current, kAXEnabledAttribute) as? Bool) ?? true
    if !en { print("disabled: \(path.joined(separator: " › "))"); exit(3) }
    print("\(press(current)): \(path.joined(separator: " › "))")

case "press":
    let pid = pidOf(arg(0))
    let text = arg(1)
    let contains = flag("--contains")
    let role = option("--role")
    let index = Int(option("--index") ?? "0") ?? 0
    let found = findAll(pid, text, contains: contains, role: role)
    let idx = index < 0 ? found.count + index : index
    guard idx >= 0, idx < found.count else { fail("not found: \(text) (\(found.count) matches)") }
    if flag("--click"), let f = axFrame(found[idx]) {
        // a real mouse click at the element's centre instead of AXPress (AXPress goes through the
        // accessibility translation layer, which a mouse user never touches)
        clickAt(CGPoint(x: f.midX, y: f.midY))
        print("click: \(describe(found[idx])) [match \(idx + 1) of \(found.count)]")
    } else {
        print("\(press(found[idx])): \(describe(found[idx])) [match \(idx + 1) of \(found.count)]")
    }

case "find":
    let pid = pidOf(arg(0))
    let text = arg(1)
    let contains = flag("--contains")
    let timeout = Double(option("--timeout") ?? "10") ?? 10
    let t0 = now()
    while now() - t0 < timeout * 1000 {
        if let el = findAll(pid, text, contains: contains, role: nil).first {
            print(String(format: "found after %.0f ms: ", now() - t0) + describe(el)); exit(0)
        }
        usleep(150_000)
    }
    print("not found: \(text)"); exit(1)

case "scroll":
    // scroll x y lines — wheel event at a screen point (positive = down)
    let at = CGPoint(x: Double(arg(0))!, y: Double(arg(1))!)
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: at, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(80_000)
    let lines = Int32(arg(2)) ?? 10
    for _ in 0..<abs(lines) {
        CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 1, wheel1: lines > 0 ? -3 : 3, wheel2: 0, wheel3: 0)?.post(tap: .cghidEventTap)
        usleep(20_000)
    }
    print("scrolled \(lines) at \(at)")
case "click":
    clickAt(CGPoint(x: Double(arg(0))!, y: Double(arg(1))!), double: flag("--double"))
case "drag":
    // drag x1 y1 x2 y2 (screen points), left button
    let a = CGPoint(x: Double(arg(0))!, y: Double(arg(1))!), b = CGPoint(x: Double(arg(2))!, y: Double(arg(3))!)
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: a, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(80_000)
    CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: a, mouseButton: .left)?.post(tap: .cghidEventTap)
    for i in 1...20 {
        let t = Double(i) / 20
        let p = CGPoint(x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t)
        CGEvent(mouseEventSource: nil, mouseType: .leftMouseDragged, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
        usleep(20_000)
    }
    CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: b, mouseButton: .left)?.post(tap: .cghidEventTap)
case "rclick":
    clickAt(CGPoint(x: Double(arg(0))!, y: Double(arg(1))!), right: true)
case "move":
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: CGPoint(x: Double(arg(0))!, y: Double(arg(1))!), mouseButton: .left)?.post(tap: .cghidEventTap)

case "key":
    sendKey(arg(0))
case "type":
    typeText(arg(0))

case "winstate":
    let pid = pidOf(arg(0))
    let wins = (ax(appElement(pid), kAXWindowsAttribute) as? [AXUIElement]) ?? []
    let screen = NSScreen.main?.visibleFrame ?? .zero
    print("screen visible: \(screen)")
    for w in wins {
        print(describe(w) + " fullscreen=\(ax(w, "AXFullScreen") as? Bool ?? false) minimized=\(ax(w, kAXMinimizedAttribute) as? Bool ?? false)")
    }
    print("cg windows: " + windows(pid: pid).map { "\($0.id) layer\($0.layer) \(Int($0.bounds.width))x\(Int($0.bounds.height))@\(Int($0.bounds.minX)),\(Int($0.bounds.minY))" }.joined(separator: "; "))

case "setwin":
    // setwin <name|pid> minimized|fullscreen true|false
    let pid = pidOf(arg(0))
    let attr = arg(1) == "fullscreen" ? "AXFullScreen" : kAXMinimizedAttribute
    let value = arg(2) == "true"
    guard let w = ((ax(appElement(pid), kAXWindowsAttribute) as? [AXUIElement]) ?? []).first else { fail("no AX window") }
    let r = AXUIElementSetAttributeValue(w, attr as CFString, (value ? kCFBooleanTrue : kCFBooleanFalse)!)
    print("set \(attr)=\(value): \(r == .success ? "ok" : "error \(r.rawValue)")")

case "focusset":
    // focusset <name|pid> <text>: sets AXValue of the app's focused text field (e.g. the Open panel's Go-to field)
    let pid = pidOf(arg(0))
    guard let f = ax(appElement(pid), kAXFocusedUIElementAttribute) else { fail("no focused element") }
    let el = f as! AXUIElement
    let r = AXUIElementSetAttributeValue(el, kAXValueAttribute as CFString, arg(1) as CFString)
    print("\(describe(el)) set: \(r == .success ? "ok" : "error \(r.rawValue)") now=\(axStr(el, kAXValueAttribute))")

case "lsquery":
    let url = URL(fileURLWithPath: arg(0))
    print("default: \(NSWorkspace.shared.urlForApplication(toOpen: url)?.path ?? "none")")
    for u in NSWorkspace.shared.urlsForApplications(toOpen: url) { print("can open: \(u.path)") }

case "pasteboard":
    let pb = NSPasteboard.general
    let out = arg(0)
    try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
    print("types: " + (pb.types ?? []).map(\.rawValue).joined(separator: ", "))
    if let s = pb.string(forType: .string) { try? s.write(toFile: "\(out)/text.txt", atomically: true, encoding: .utf8); print("text: \(s.prefix(200))") }
    if let d = pb.data(forType: .png) { FileManager.default.createFile(atPath: "\(out)/image.png", contents: d); print("png bytes: \(d.count)") }

case "displays":
    let id = CGMainDisplayID()
    let opts = [kCGDisplayShowDuplicateLowResolutionModes: kCFBooleanTrue] as CFDictionary
    let modes = (CGDisplayCopyAllDisplayModes(id, opts) as? [CGDisplayMode]) ?? []
    if let cur = CGDisplayCopyDisplayMode(id) { print("current: \(cur.width)x\(cur.height) pt, \(cur.pixelWidth)x\(cur.pixelHeight) px") }
    for m in modes { print("mode: \(m.width)x\(m.height) pt \(m.pixelWidth)x\(m.pixelHeight) px\(m.pixelWidth > m.width ? " HiDPI" : "")") }
    if flag("--max") {
        let lo = modes.filter { $0.pixelWidth == $0.width }.max { $0.width * $0.height < $1.width * $1.height }
        guard let lo else { print("no modes"); exit(4) }
        var cfg: CGDisplayConfigRef?
        CGBeginDisplayConfiguration(&cfg)
        CGConfigureDisplayWithDisplayMode(cfg, id, lo, nil)
        let r = CGCompleteDisplayConfiguration(cfg, .permanently)
        print("switch to \(lo.width)x\(lo.height): \(r == .success ? "ok" : "error \(r.rawValue)")")
    }
    if flag("--hidpi") {
        let hi = modes.filter { $0.pixelWidth > $0.width && $0.width >= 1280 }.max { $0.width < $1.width }
        guard let hi else { print("no HiDPI mode ≥ 1280 pt"); exit(4) }
        var cfg: CGDisplayConfigRef?
        CGBeginDisplayConfiguration(&cfg)
        CGConfigureDisplayWithDisplayMode(cfg, id, hi, nil)
        let r = CGCompleteDisplayConfiguration(cfg, .permanently)
        print("switch to \(hi.width)x\(hi.height) HiDPI: \(r == .success ? "ok" : "error \(r.rawValue)")")
    }

case "focused":
    // the app's focused accessibility element (where keys go)
    let app = appElement(pidOf(arg(0)))
    if let f = ax(app, kAXFocusedUIElementAttribute) { print(describe(f as! AXUIElement)) } else { print("no focused element") }
case "activate":
    NSRunningApplication(processIdentifier: pidOf(arg(0)))?.activate()

case "quit":
    let pid = pidOf(arg(0))
    let force = flag("--force")
    guard let a = NSRunningApplication(processIdentifier: pid) else { exit(0) }
    _ = force ? a.forceTerminate() : a.terminate()
    let t0 = now()
    while !a.isTerminated && now() - t0 < 10_000 { RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.05)) }
    if !a.isTerminated { _ = a.forceTerminate(); print("forced") } else { print(String(format: "quit in %.0f ms", now() - t0)) }

default:
    fail("unknown command \(cmd)")
}
