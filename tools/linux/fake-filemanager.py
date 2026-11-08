#!/usr/bin/python3
"""A stand-in desktop file manager on the session bus (test-only, never shipped): owns
org.freedesktop.FileManager1, answers ShowItems after <delay> seconds and logs each call.

  tools/linux/fake-filemanager.py <log file> <delay seconds>

Needs python3-gi (Ubuntu's binding for the system Python, /usr/bin/python3).
"""
import sys, time

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

LOG, DELAY = sys.argv[1], float(sys.argv[2])
XML = """<node><interface name='org.freedesktop.FileManager1'>
<method name='ShowItems'><arg type='as' name='uris' direction='in'/><arg type='s' name='startup_id' direction='in'/></method>
</interface></node>"""


def on_call(conn, sender, path, iface, method, params, invocation):
    with open(LOG, "a") as f:
        f.write(f"{time.time():.3f} {method} {params.unpack()[0]}\n")
    GLib.timeout_add(int(DELAY * 1000), lambda: (invocation.return_value(None), False)[1])


def on_bus(conn, name):
    node = Gio.DBusNodeInfo.new_for_xml(XML)
    conn.register_object("/org/freedesktop/FileManager1", node.interfaces[0], on_call, None, None)


Gio.bus_own_name(Gio.BusType.SESSION, "org.freedesktop.FileManager1", Gio.BusNameOwnerFlags.NONE, on_bus, None, None)
GLib.MainLoop().run()
