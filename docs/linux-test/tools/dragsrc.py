# Test tool: a GTK4 window that drags a file list (like a file manager)
import sys, gi
gi.require_version("Gtk","4.0"); gi.require_version("Gdk","4.0")
from gi.repository import Gtk, Gdk, Gio, GObject
files=[Gio.File.new_for_path(p) for p in sys.argv[1:]]
def on_prepare(src, x, y):
    fl=Gdk.FileList.new_from_list(files)
    return Gdk.ContentProvider.new_for_value(GObject.Value(Gdk.FileList, fl))
def act(app):
    w=Gtk.ApplicationWindow(application=app, title="DragSource"); w.set_default_size(260,200)
    l=Gtk.Label(label="DRAG ME ("+str(len(files))+" files)"); w.set_child(l)
    ds=Gtk.DragSource(); ds.set_actions(Gdk.DragAction.COPY); ds.connect("prepare", on_prepare); l.add_controller(ds)
    w.present()
a=Gtk.Application(application_id="test.dragsrc"); a.connect("activate", act); a.run([])
