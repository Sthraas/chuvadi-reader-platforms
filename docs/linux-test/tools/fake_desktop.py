# Test only, never in the product: a stand-in for the desktop's side of a sign-out, written by Linux Test
# independently of tools/linux/fake-session.c. It sits on a private session bus and plays one of:
#   portal    org.freedesktop.portal.Desktop with the Inhibit interface (Inhibit, CreateMonitor, QueryEndResponse)
#   refused   the same, but every Inhibit request ends with Response 2 (the desktop refused the lock)
#   gnome     only org.gnome.SessionManager (Inhibit / Uninhibit), no portal
#   fallback  a portal whose Inhibit call fails, plus org.gnome.SessionManager
#   empty     nothing on the bus at all
# Every call it receives is written, with a millisecond clock, to the log file as one JSON line.
# The test tells it to send the "session state" notice with:  gdbus call ... lt.Ctl.State <1|2|3>
# Usage: fake_desktop.py <mode> <log file>      (DBUS_SESSION_BUS_ADDRESS = the private bus)
import sys, json, time
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

MODE, LOG = sys.argv[1], sys.argv[2]
PORTAL, PATH, IFACE = "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop", "org.freedesktop.portal.Inhibit"
GSM, GSM_PATH = "org.gnome.SessionManager", "/org/gnome/SessionManager"


def log(ev, **k):
    with open(LOG, "a") as f:
        f.write(json.dumps(dict(t=round(time.monotonic() * 1000), ev=ev, **k)) + "\n")


PORTAL_XML = """<node><interface name='org.freedesktop.portal.Inhibit'>
<method name='Inhibit'><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='a{sv}' direction='in'/><arg type='o' direction='out'/></method>
<method name='CreateMonitor'><arg type='s' direction='in'/><arg type='a{sv}' direction='in'/><arg type='o' direction='out'/></method>
<method name='QueryEndResponse'><arg type='o' direction='in'/></method>
<signal name='StateChanged'><arg type='o'/><arg type='a{sv}'/></signal>
</interface>
<interface name='lt.Ctl'><method name='State'><arg type='u' direction='in'/></method></interface></node>"""
REQ_XML = """<node><interface name='org.freedesktop.portal.Request'><method name='Close'/>
<signal name='Response'><arg type='u'/><arg type='a{sv}'/></signal></interface></node>"""
GSM_XML = """<node><interface name='org.gnome.SessionManager'>
<method name='Inhibit'><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='u' direction='out'/></method>
<method name='Uninhibit'><arg type='u' direction='in'/></method></interface></node>"""

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
state = dict(session=None, owner=None, n=0, cookie=1000, requests={})
req_info = Gio.DBusNodeInfo.new_for_xml(REQ_XML).interfaces[0]


def sender_part(sender):
    return sender[1:].replace(".", "_")


def on_request(conn, sender, path, iface, method, params, inv):
    log("request-close", path=path)
    reg = state["requests"].pop(path, None)
    if reg:
        conn.unregister_object(reg)
    inv.return_value(None)


def new_request(conn, sender, token, response, results=None):
    state["n"] += 1
    path = f"{PATH}/request/{sender_part(sender)}/{token or 'lt' + str(state['n'])}"
    state["requests"][path] = conn.register_object(path, req_info, on_request, None, None)

    def respond():
        conn.emit_signal(sender, path, "org.freedesktop.portal.Request", "Response",
                         GLib.Variant("(ua{sv})", (response, results or {})))
        return False
    GLib.idle_add(respond)
    return path


def send_state(conn, phase):
    if not state["session"]:
        log("notice-not-sent", why="no monitor")
        return
    conn.emit_signal(state["owner"], PATH, IFACE, "StateChanged",
                     GLib.Variant("(oa{sv})", (state["session"], {"screensaver-active": GLib.Variant("b", False),
                                                                    "session-state": GLib.Variant("u", phase)})))
    log("notice", phase=phase)


def on_portal(conn, sender, path, iface, method, params, inv):
    if iface == "lt.Ctl":
        send_state(conn, params.unpack()[0])
        inv.return_value(None)
        return
    if method == "Inhibit":
        window, flags, options = params.unpack()
        log("inhibit", window=window, flags=flags, options=options, sender=sender)
        if MODE == "fallback":
            inv.return_dbus_error("org.freedesktop.DBus.Error.UnknownMethod", "no Inhibit here")
            return
        handle = new_request(conn, sender, options.get("handle_token"), 2 if MODE == "refused" else 0)
        inv.return_value(GLib.Variant("(o)", (handle,)))
    elif method == "CreateMonitor":
        window, options = params.unpack()
        state["session"] = f"{PATH}/session/{sender_part(sender)}/{options.get('session_handle_token', 'lt')}"
        state["owner"] = sender
        log("monitor", window=window, options=options, session=state["session"])
        handle = new_request(conn, sender, options.get("handle_token"), 0, {"session_handle": GLib.Variant("s", state["session"])})
        inv.return_value(GLib.Variant("(o)", (handle,)))
        GLib.timeout_add(150, lambda: (send_state(conn, 1), False)[1])   # as the real portal does: the state now
    elif method == "QueryEndResponse":
        log("query-end-response", session=params.unpack()[0])
        inv.return_value(None)


def on_gsm(conn, sender, path, iface, method, params, inv):
    if method == "Inhibit":
        app, xid, reason, flags = params.unpack()
        state["cookie"] += 1
        state["owner"] = sender
        log("gsm-inhibit", app=app, xid=xid, reason=reason, flags=flags, cookie=state["cookie"])
        inv.return_value(GLib.Variant("(u)", (state["cookie"],)))
    else:
        log("gsm-uninhibit", cookie=params.unpack()[0])
        inv.return_value(None)


def on_owner(conn, sender, path, iface, signal, params):
    name, old, new = params.unpack()
    if name.startswith(":") and not new and name == state["owner"]:
        log("app-left-the-bus", name=name)


if MODE in ("portal", "refused", "fallback"):
    for i in Gio.DBusNodeInfo.new_for_xml(PORTAL_XML).interfaces:
        bus.register_object(PATH, i, on_portal, None, None)
    Gio.bus_own_name_on_connection(bus, PORTAL, Gio.BusNameOwnerFlags.NONE, None, None)
if MODE in ("gnome", "fallback"):
    bus.register_object(GSM_PATH, Gio.DBusNodeInfo.new_for_xml(GSM_XML).interfaces[0], on_gsm, None, None)
    Gio.bus_own_name_on_connection(bus, GSM, Gio.BusNameOwnerFlags.NONE, None, None)
bus.signal_subscribe("org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged", "/org/freedesktop/DBus",
                     None, Gio.DBusSignalFlags.NONE, on_owner)
log("ready", mode=MODE)
GLib.MainLoop().run()
