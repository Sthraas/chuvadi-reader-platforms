import sys, gi
from gi.repository import Gio, GLib
scale=float(sys.argv[1])
bus=Gio.bus_get_sync(Gio.BusType.SESSION)
p=Gio.DBusProxy.new_sync(bus,0,None,"org.gnome.Mutter.DisplayConfig","/org/gnome/Mutter/DisplayConfig","org.gnome.Mutter.DisplayConfig")
serial,monitors,logical,props=p.call_sync("GetCurrentState",None,0,-1,None).unpack()
mon=monitors[0]; connector=mon[0][0]; mode=[m for m in mon[1] if m[6].get("is-current")][0][0]
cfg=[(0,0,scale,0,True,[(connector,mode,{})])]
p.call_sync("ApplyMonitorsConfig",GLib.Variant("(uua(iiduba(ssa{sv}))a{sv})",(serial,1,cfg,{})),0,-1,None)
serial,monitors,logical,props=p.call_sync("GetCurrentState",None,0,-1,None).unpack()
print("logical monitors now:", [(l[0],l[1],l[2]) for l in logical])
