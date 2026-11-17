/* A stand-in for the desktop's side of signing out, for the UI tests only (never shipped; GLib only).
 *
 *   fake-session portal   owns org.freedesktop.portal.Desktop: Inhibit, CreateMonitor, QueryEndResponse,
 *                         and Request.Close on the handles it gave out
 *   fake-session gnome    owns org.gnome.SessionManager: Inhibit, Uninhibit
 *   fake-session portal gnome          both, as on a GNOME desktop
 *   fake-session portal refuse gnome   the portal takes Inhibit and then refuses it (the request ends with
 *                                      Response 2), as a desktop behind the portal that says no
 *
 * Every call is written to stdout as one line. A line on stdin makes it act: "query-end" sends the portal's
 * StateChanged (session-state 2) to every monitor, as a desktop does when the person signs out; "quit" ends it.
 *
 *   gcc -O1 -o fake-session tools/linux/fake-session.c $(pkg-config --cflags --libs gio-2.0 gio-unix-2.0)
 */
#include <gio/gio.h>
#include <gio/gunixinputstream.h>
#include <stdio.h>
#include <string.h>

static GDBusConnection *bus;
static GPtrArray *monitors; /* session object paths */
static guint next_id = 1;
static gboolean refuse;

static const char PORTAL_XML[] =
    "<node>"
    "<interface name='org.freedesktop.portal.Inhibit'>"
    "<method name='Inhibit'><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='a{sv}' direction='in'/><arg type='o' direction='out'/></method>"
    "<method name='CreateMonitor'><arg type='s' direction='in'/><arg type='a{sv}' direction='in'/><arg type='o' direction='out'/></method>"
    "<method name='QueryEndResponse'><arg type='o' direction='in'/></method>"
    "<signal name='StateChanged'><arg type='o'/><arg type='a{sv}'/></signal>"
    "<property name='version' type='u' access='read'/>"
    "</interface>"
    "<interface name='org.freedesktop.portal.Request'><method name='Close'/>"
    "<signal name='Response'><arg type='u'/><arg type='a{sv}'/></signal></interface>"
    "</node>";

static const char GNOME_XML[] =
    "<node><interface name='org.gnome.SessionManager'>"
    "<method name='Inhibit'><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='u' direction='out'/></method>"
    "<method name='Uninhibit'><arg type='u' direction='in'/></method>"
    "</interface></node>";

static void say(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
    putchar('\n');
    fflush(stdout);
}

static char *sender_element(const char *sender)
{
    char *s = g_strdup(sender + 1);
    for (char *c = s; *c; c++)
    {
        if (*c == '.')
        {
            *c = '_';
        }
    }

    return s;
}

static void request_call(GDBusConnection *c, const char *sender, const char *path, const char *iface, const char *method,
                         GVariant *params, GDBusMethodInvocation *inv, gpointer data)
{
    (void)c; (void)sender; (void)iface; (void)params; (void)data;
    if (g_strcmp0(method, "Close") == 0)
    {
        say("Close %s", strrchr(path, '/') + 1);
        g_dbus_method_invocation_return_value(inv, NULL);
    }
}

static const GDBusInterfaceVTable request_vtable = { request_call, NULL, NULL, { 0 } };
static GDBusNodeInfo *portal_info;

static void portal_call(GDBusConnection *c, const char *sender, const char *path, const char *iface, const char *method,
                        GVariant *params, GDBusMethodInvocation *inv, gpointer data)
{
    (void)path; (void)iface; (void)data;
    char *who = sender_element(sender);
    if (g_strcmp0(method, "Inhibit") == 0)
    {
        const char *window;
        guint32 flags;
        GVariant *options;
        const char *reason = "";
        g_variant_get(params, "(&su@a{sv})", &window, &flags, &options);
        g_variant_lookup(options, "reason", "&s", &reason);
        const char *asked = NULL;
        g_variant_lookup(options, "handle_token", "&s", &asked);
        char *token = asked ? g_strdup(asked) : g_strdup_printf("hold%u", next_id++);
        char *handle = g_strdup_printf("/org/freedesktop/portal/desktop/request/%s/%s", who, token);
        guint object = g_dbus_connection_register_object(c, handle, portal_info->interfaces[1], &request_vtable, NULL, NULL, NULL);
        say("Inhibit %s flags=%u reason=%s", token, flags, reason);
        g_dbus_method_invocation_return_value(inv, g_variant_new("(o)", handle));
        if (refuse)
        {
            GVariantBuilder results;
            g_variant_builder_init(&results, G_VARIANT_TYPE("a{sv}"));
            g_dbus_connection_emit_signal(c, sender, handle, "org.freedesktop.portal.Request", "Response",
                                          g_variant_new("(ua{sv})", (guint32)2, &results), NULL);
            g_dbus_connection_unregister_object(c, object);
            say("Refused %s", token);
        }

        g_variant_unref(options);
        g_free(token);
        g_free(handle);
    }
    else if (g_strcmp0(method, "CreateMonitor") == 0)
    {
        const char *window;
        GVariant *options;
        const char *token = "t", *session = "s";
        g_variant_get(params, "(&s@a{sv})", &window, &options);
        g_variant_lookup(options, "handle_token", "&s", &token);
        g_variant_lookup(options, "session_handle_token", "&s", &session);
        char *handle = g_strdup_printf("/org/freedesktop/portal/desktop/request/%s/%s", who, token);
        g_ptr_array_add(monitors, g_strdup_printf("/org/freedesktop/portal/desktop/session/%s/%s", who, session));
        say("CreateMonitor");
        g_dbus_method_invocation_return_value(inv, g_variant_new("(o)", handle));
        g_variant_unref(options);
        g_free(handle);
    }
    else if (g_strcmp0(method, "QueryEndResponse") == 0)
    {
        say("QueryEndResponse");
        g_dbus_method_invocation_return_value(inv, NULL);
    }

    g_free(who);
}

static GVariant *portal_get(GDBusConnection *c, const char *sender, const char *path, const char *iface, const char *prop,
                            GError **error, gpointer data)
{
    (void)c; (void)sender; (void)path; (void)iface; (void)prop; (void)error; (void)data;
    return g_variant_new_uint32(3);
}

static const GDBusInterfaceVTable portal_vtable = { portal_call, portal_get, NULL, { 0 } };

static void gnome_call(GDBusConnection *c, const char *sender, const char *path, const char *iface, const char *method,
                       GVariant *params, GDBusMethodInvocation *inv, gpointer data)
{
    (void)c; (void)sender; (void)path; (void)iface; (void)data;
    if (g_strcmp0(method, "Inhibit") == 0)
    {
        const char *app, *reason;
        guint32 xid, flags;
        g_variant_get(params, "(&su&su)", &app, &xid, &reason, &flags);
        guint cookie = 1000 + next_id++;
        say("Inhibit cookie%u app=%s flags=%u reason=%s", cookie, app, flags, reason);
        g_dbus_method_invocation_return_value(inv, g_variant_new("(u)", cookie));
    }
    else if (g_strcmp0(method, "Uninhibit") == 0)
    {
        guint32 cookie;
        g_variant_get(params, "(u)", &cookie);
        say("Uninhibit cookie%u", cookie);
        g_dbus_method_invocation_return_value(inv, NULL);
    }
}

static const GDBusInterfaceVTable gnome_vtable = { gnome_call, NULL, NULL, { 0 } };

static void on_line(GObject *source, GAsyncResult *result, gpointer loop)
{
    char *line = g_data_input_stream_read_line_finish(G_DATA_INPUT_STREAM(source), result, NULL, NULL);
    if (!line || g_strcmp0(line, "quit") == 0)
    {
        g_main_loop_quit(loop);
        g_free(line);
        return;
    }

    if (g_strcmp0(line, "query-end") == 0)
    {
        for (guint i = 0; i < monitors->len; i++)
        {
            GVariantBuilder state;
            g_variant_builder_init(&state, G_VARIANT_TYPE("a{sv}"));
            g_variant_builder_add(&state, "{sv}", "screensaver-active", g_variant_new_boolean(FALSE));
            g_variant_builder_add(&state, "{sv}", "session-state", g_variant_new_uint32(2));
            g_dbus_connection_emit_signal(bus, NULL, "/org/freedesktop/portal/desktop", "org.freedesktop.portal.Inhibit",
                                          "StateChanged", g_variant_new("(oa{sv})", (const char *)g_ptr_array_index(monitors, i), &state), NULL);
        }

        say("StateChanged query-end to %u", monitors->len);
    }

    g_free(line);
    g_data_input_stream_read_line_async(G_DATA_INPUT_STREAM(source), G_PRIORITY_DEFAULT, NULL, on_line, loop);
}

static gboolean take_name(const char *name)
{
    GError *error = NULL;
    GVariant *owned = g_dbus_connection_call_sync(bus, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
                                                  g_variant_new("(su)", name, 4u), G_VARIANT_TYPE("(u)"), G_DBUS_CALL_FLAGS_NONE, -1, NULL, &error);
    if (!owned)
    {
        fprintf(stderr, "could not take %s: %s\n", name, error->message);
        return FALSE;
    }

    guint32 got = 0;
    g_variant_get(owned, "(u)", &got);
    g_variant_unref(owned);
    if (got != 1)
    {
        fprintf(stderr, "%s is already taken on this bus (a real portal or session manager): use a bus of its own\n", name);
        return FALSE;
    }

    return TRUE;
}

int main(int argc, char **argv)
{
    gboolean portal = FALSE, gnome = FALSE;
    GString *kinds = g_string_new(NULL);
    for (int i = 1; i < argc; i++)
    {
        portal |= g_strcmp0(argv[i], "portal") == 0;
        gnome |= g_strcmp0(argv[i], "gnome") == 0;
        refuse |= g_strcmp0(argv[i], "refuse") == 0;
        g_string_append_printf(kinds, "%s%s", i > 1 ? " " : "", argv[i]);
    }

    GError *error = NULL;
    bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &error);
    if (!bus)
    {
        fprintf(stderr, "no session bus: %s\n", error->message);
        return 1;
    }

    monitors = g_ptr_array_new_with_free_func(g_free);
    if (gnome)
    {
        GDBusNodeInfo *info = g_dbus_node_info_new_for_xml(GNOME_XML, NULL);
        g_dbus_connection_register_object(bus, "/org/gnome/SessionManager", info->interfaces[0], &gnome_vtable, NULL, NULL, NULL);
        if (!take_name("org.gnome.SessionManager"))
        {
            return 1;
        }
    }

    if (portal)
    {
        portal_info = g_dbus_node_info_new_for_xml(PORTAL_XML, NULL);
        g_dbus_connection_register_object(bus, "/org/freedesktop/portal/desktop", portal_info->interfaces[0], &portal_vtable, NULL, NULL, NULL);
        if (!take_name("org.freedesktop.portal.Desktop"))
        {
            return 1;
        }
    }

    say("ready %s", kinds->str);
    GMainLoop *loop = g_main_loop_new(NULL, FALSE);
    GInputStream *in = g_unix_input_stream_new(0, FALSE);
    GDataInputStream *lines = g_data_input_stream_new(in);
    g_data_input_stream_read_line_async(lines, G_PRIORITY_DEFAULT, NULL, on_line, loop);
    g_main_loop_run(loop);
    return 0;
}
