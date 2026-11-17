/*
 * chvdhost — the native half of Chuvadi Reader's Linux host.
 *
 * One GTK 4 window holding one WebKitGTK 6.0 web view. Everything the app does
 * lives in .NET (ChuvadiReader.Linux, ChuvadiReader.Ui, ChuvadiReader.Core);
 * this file only owns what must be native:
 *
 *   - the window and its custom-chrome frame (no system title bar, resize edges kept)
 *   - the web view, its settings and its background colour (no white flash)
 *   - the "app" URI scheme: every asset request is handed to .NET, which answers it
 *   - the JS <-> .NET message pipe used by blazor.webview.js (window.external)
 *   - a thread-safe "wake" so .NET can run work on the GTK main thread
 *   - navigation policy: nothing but app://localhost loads inside the view
 *
 * Threading: every exported function except chvd_wake() and chvd_post_message()
 * must be called on the GTK main thread. Those two may be called from any thread.
 *
 * Only GTK, GLib and WebKitGTK are used (OS components). No third-party code.
 */

#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <gtk/gtkunixprint.h>
#include <string.h>
#include <math.h>

#define CHVD_EXPORT __attribute__((visibility("default")))

#define CHVD_SCHEME "app"
#define CHVD_ORIGIN "app://localhost/"
#define CHVD_HANDLER "chuvadi"

/* Window events sent to .NET (chvd_event_fn kind). */
enum
{
    CHVD_EVENT_MAXIMIZED_CHANGED = 1, /* payload "1" or "0" */
    CHVD_EVENT_CLOSE_REQUESTED = 2,   /* payload NULL */
    CHVD_EVENT_FILES_DROPPED = 3,     /* payload: absolute paths, one per line */
    CHVD_EVENT_EXTERNAL_LINK = 4,     /* payload: the URI the page tried to open */
    CHVD_EVENT_FIRST_PAINT = 5,       /* payload NULL: web view finished its first load */
    CHVD_EVENT_DIALOG_RESULT = 6,     /* payload "<token>" then one chosen path per line (none = cancelled) */
    CHVD_EVENT_PRINT_RESULT = 7,      /* payload "<token>" then key=value lines (none = cancelled) */
    CHVD_EVENT_JS_RESULT = 8,         /* payload "<token>" then the result as JSON, or "!<error>" (UI test builds) */
    CHVD_EVENT_BUTTON_LAYOUT = 9,     /* payload: the desktop's new window-button layout (D-101) */
    CHVD_EVENT_SESSION_END = 10,      /* payload "query": the desktop asks before signing out or shutting down (D-194) */
};

typedef void (*chvd_scheme_fn)(void *request, const char *uri);
typedef void (*chvd_message_fn)(const char *message);
typedef void (*chvd_wake_fn)(void);
typedef void (*chvd_event_fn)(int kind, const char *payload);

static struct
{
    chvd_scheme_fn scheme;
    chvd_message_fn message;
    chvd_wake_fn wake;
    chvd_event_fn event;

    GMainLoop *loop;
    GtkWindow *window;
    WebKitWebView *view;
    GtkCssProvider *css;

    /* The start-up mark: an opaque cover over the web view, from the window's first frame until the app's
     * first render (chvd_ready), or the fallback time. */
    GtkWidget *cover;
    guint cover_fallback;
    int close_held;     /* set by .NET from inside the close-requested event: that request is held */

    /* Sign-out and shutdown (D-194): see "the session" below. */
    GDBusConnection *bus;
    char *monitor_path;       /* the portal's session monitor, once asked for */
    guint monitor_signal;
    char *hold_reason;        /* non-NULL: .NET wants the sign-out held, with this reason */
    char *hold_request;       /* the portal's request object that is the hold */
    char *hold_request_named; /* the path we asked the portal to give that request, to hear its refusal */
    guint hold_refusal;       /* the subscription to that request's Response */
    guint hold_serial;        /* makes each request's name its own */
    guint hold_cookie;        /* or the GNOME session manager's cookie */
    int hold_pending;         /* a call asking for the hold is under way */
    int query_end_owed;       /* the desktop is waiting for our answer to "about to end" */
    double pinch_scale; /* the pinch's scale at the last change sent to the page; 0 when no pinch is on */

    /* The last pointer press inside the view, for begin-move from the HTML title bar. */
    GdkDevice *press_device;
    int press_button;
    double press_x, press_y; /* view coordinates */
    guint32 press_time;

    gint wake_pending;
    gboolean no_gpu; /* no DRM render node: GTK and WebKit render on the CPU */
} S;

/* ── main loop ──────────────────────────────────────────────────────────── */

static gboolean has_render_node(void)
{
    GDir *dir = g_dir_open("/dev/dri", 0, NULL);
    if (!dir)
    {
        return FALSE;
    }

    gboolean found = FALSE;
    const char *name;
    while (!found && (name = g_dir_read_name(dir)))
    {
        found = g_str_has_prefix(name, "renderD");
    }

    g_dir_close(dir);
    return found;
}

static void on_layout_changed(GObject *settings, GParamSpec *pspec, gpointer data)
{
    char *layout = NULL;
    g_object_get(settings, "gtk-decoration-layout", &layout, NULL);
    if (S.event)
    {
        S.event(CHVD_EVENT_BUTTON_LAYOUT, layout ? layout : "");
    }
    g_free(layout);
}

/* UI tests only call this: sets the layout the way the desktop's settings bridge does. */
CHVD_EXPORT void chvd_set_button_layout(const char *layout)
{
    g_object_set(gtk_settings_get_default(), "gtk-decoration-layout", layout, NULL);
}

CHVD_EXPORT int chvd_init(chvd_scheme_fn scheme, chvd_message_fn message, chvd_wake_fn wake, chvd_event_fn event)
{
    if (!scheme || !message || !wake || !event)
    {
        return 0;
    }

    S.scheme = scheme;
    S.message = message;
    S.wake = wake;
    S.event = event;


    /* Without a GPU (no DRM render node: VMs, remote sessions, CI), GTK's GL/Vulkan renderers run in
     * software (llvmpipe) and cost ~460 ms before the window shows and ~700 ms to first render
     * (measured, docs/linux/BUILD-LOG.md). Its CPU renderer is then the fast one. With a GPU, GTK's
     * default stays. The person's own GSK_RENDERER always wins. */
    S.no_gpu = !has_render_node();
    if (!g_getenv("GSK_RENDERER") && S.no_gpu)
    {
        g_setenv("GSK_RENDERER", "cairo", FALSE);
    }

    if (!gtk_init_check())
    {
        return 0; /* no display */
    }

    /* Printing goes to CUPS queues only (the PDF itself, through Chuvadi.Print.Ipp). GTK's "Print to
     * File" pseudo-printer can't take that job, so the print dialog lists CUPS printers only.
     * (GTK 4 reads this from its settings; the GTK 3 GTK_PRINT_BACKENDS variable is gone.) */
    g_object_set(gtk_settings_get_default(), "gtk-print-backends", "cups", NULL);
    /* D-101: the desktop's window-button layout can change while Chuvadi is open (GNOME/KDE settings reach
     * GTK as this property); the top bar follows at once. */
    g_signal_connect(gtk_settings_get_default(), "notify::gtk-decoration-layout", G_CALLBACK(on_layout_changed), NULL);

    S.loop = g_main_loop_new(NULL, FALSE);
    return 1;
}

CHVD_EXPORT void chvd_run(void)
{
    g_main_loop_run(S.loop);
}

CHVD_EXPORT void chvd_quit(void)
{
    if (S.loop)
    {
        g_main_loop_quit(S.loop);
    }
}

static gboolean on_wake(gpointer data)
{
    (void)data;
    g_atomic_int_set(&S.wake_pending, 0);
    S.wake();
    return G_SOURCE_REMOVE;
}

/* Any thread: ask the main thread to call the wake callback (coalesced). */
CHVD_EXPORT void chvd_wake(void)
{
    if (g_atomic_int_compare_and_exchange(&S.wake_pending, 0, 1))
    {
        g_main_context_invoke(NULL, on_wake, NULL);
    }
}

/* ── JS -> .NET ──────────────────────────────────────────────────────────── */

static void on_script_message(WebKitUserContentManager *ucm, JSCValue *value, gpointer data)
{
    (void)ucm;
    (void)data;
    if (!jsc_value_is_string(value))
    {
        return;
    }

    char *text = jsc_value_to_string(value);
    S.message(text);
    g_free(text);
}

/* Defines window.external the way blazor.webview.js expects it, before any page script runs.
 * Messages to .NET go through the "chuvadi" script message handler; messages from .NET
 * arrive through __chvdReceive (see chvd_post_message). */
static const char *BRIDGE_JS =
    "(function(){"
    "var r=[];"
    "Object.defineProperty(window,'__chvdReceive',{value:function(m){for(var i=0;i<r.length;i++)r[i](m);}});"
    "window.external={"
    "sendMessage:function(m){window.webkit.messageHandlers." CHVD_HANDLER ".postMessage(m);},"
    "receiveMessage:function(cb){r.push(cb);}"
    "};"
    "})();";

/* ── .NET -> JS ──────────────────────────────────────────────────────────── */

/* Every message to the page goes through one FIFO, drained on the main thread. Blazor's
 * dispatcher can send from a worker thread or, running inline, from the main thread itself;
 * delivering main-thread messages immediately would overtake ones still queued from workers
 * and break the order Blazor's render protocol relies on (seen as an occasional startup hang). */
static GAsyncQueue *S_outbox; /* created on first use, thread-safely */
static gint S_outbox_pending;

static GAsyncQueue *outbox(void)
{
    static gsize once = 0;
    if (g_once_init_enter(&once))
    {
        S_outbox = g_async_queue_new();
        g_once_init_leave(&once, 1);
    }

    return S_outbox;
}

static gboolean drain_outbox(gpointer data)
{
    (void)data;
    g_atomic_int_set(&S_outbox_pending, 0);
    char *script;
    while ((script = g_async_queue_try_pop(outbox())))
    {
        if (S.view)
        {
            webkit_web_view_evaluate_javascript(S.view, script, -1, NULL, NULL, NULL, NULL, NULL);
        }

        g_free(script);
    }

    return G_SOURCE_REMOVE;
}

/* Any thread. json_literal must already be a JavaScript string literal (quoted and escaped). */
CHVD_EXPORT void chvd_post_message(const char *json_literal)
{
    g_async_queue_push(outbox(), g_strconcat("__chvdReceive(", json_literal, ");", NULL));
    if (g_atomic_int_compare_and_exchange(&S_outbox_pending, 0, 1))
    {
        g_idle_add_full(G_PRIORITY_DEFAULT, drain_outbox, NULL, NULL);
    }
}

/* ── the app:// scheme ───────────────────────────────────────────────────── */

static void on_scheme_request(WebKitURISchemeRequest *request, gpointer data)
{
    (void)data;
    S.scheme(request, webkit_uri_scheme_request_get_uri(request));
}

/* Main thread, from inside the scheme callback. Copies the bytes. */
CHVD_EXPORT void chvd_scheme_respond(void *request, int status, const char *content_type,
                                     const void *bytes, gsize length, const char *cache_control)
{
    WebKitURISchemeRequest *req = WEBKIT_URI_SCHEME_REQUEST(request);
    GBytes *body = g_bytes_new(bytes, length);
    GInputStream *stream = g_memory_input_stream_new_from_bytes(body);
    WebKitURISchemeResponse *response = webkit_uri_scheme_response_new(stream, (gint64)length);

    webkit_uri_scheme_response_set_status(response, (guint)status, NULL);
    if (content_type && *content_type)
    {
        webkit_uri_scheme_response_set_content_type(response, content_type);
    }

    if (cache_control && *cache_control)
    {
        SoupMessageHeaders *headers = soup_message_headers_new(SOUP_MESSAGE_HEADERS_RESPONSE);
        soup_message_headers_append(headers, "Cache-Control", cache_control);
        webkit_uri_scheme_response_set_http_headers(response, headers); /* takes ownership */
    }

    webkit_uri_scheme_request_finish_with_response(req, response);

    g_object_unref(response);
    g_object_unref(stream);
    g_bytes_unref(body);
}

/* ── navigation policy ───────────────────────────────────────────────────── */

static gboolean is_internal(const char *uri)
{
    return uri && (g_str_has_prefix(uri, CHVD_ORIGIN) || g_str_has_prefix(uri, "about:") ||
                   g_str_has_prefix(uri, "blob:") || g_str_has_prefix(uri, "data:"));
}

static gboolean on_decide_policy(WebKitWebView *view, WebKitPolicyDecision *decision,
                                 WebKitPolicyDecisionType type, gpointer data)
{
    (void)view;
    (void)data;
    if (type != WEBKIT_POLICY_DECISION_TYPE_NAVIGATION_ACTION &&
        type != WEBKIT_POLICY_DECISION_TYPE_NEW_WINDOW_ACTION)
    {
        return FALSE; /* responses: default handling */
    }

    WebKitNavigationAction *action =
        webkit_navigation_policy_decision_get_navigation_action(WEBKIT_NAVIGATION_POLICY_DECISION(decision));
    const char *uri = webkit_uri_request_get_uri(webkit_navigation_action_get_request(action));

    if (type == WEBKIT_POLICY_DECISION_TYPE_NAVIGATION_ACTION && is_internal(uri))
    {
        webkit_policy_decision_use(decision);
        return TRUE;
    }

    /* Anything else never loads inside Chuvadi. .NET decides whether to hand it to the
     * system browser (only http, https and mailto qualify, see IExternalLinks.IsAllowed). */
    webkit_policy_decision_ignore(decision);
    if (uri && !is_internal(uri) && webkit_navigation_action_is_user_gesture(action))
    {
        S.event(CHVD_EVENT_EXTERNAL_LINK, uri);
    }

    return TRUE;
}

static void on_load_changed(WebKitWebView *view, WebKitLoadEvent event, gpointer data)
{
    (void)view;
    (void)data;
    if (event == WEBKIT_LOAD_FINISHED)
    {
        S.event(CHVD_EVENT_FIRST_PAINT, NULL);
    }
}

/* ── pointer tracking (for chvd_begin_move) ──────────────────────────────── */

static void on_press(GtkGestureClick *gesture, int n_press, double x, double y, gpointer data)
{
    (void)n_press;
    (void)data;
    GtkGesture *g = GTK_GESTURE(gesture);
    S.press_device = gtk_gesture_get_device(g);
    S.press_button = (int)gtk_gesture_single_get_current_button(GTK_GESTURE_SINGLE(gesture));
    S.press_x = x;
    S.press_y = y;
    S.press_time = gtk_event_controller_get_current_event_time(GTK_EVENT_CONTROLLER(gesture));
    /* Observe only: never claim, so the page still gets the click. */
}

/* ── file drops ──────────────────────────────────────────────────────────── */

static gboolean on_drop(GtkDropTarget *target, const GValue *value, double x, double y, gpointer data)
{
    (void)target;
    (void)x;
    (void)y;
    (void)data;
    if (!G_VALUE_HOLDS(value, GDK_TYPE_FILE_LIST))
    {
        return FALSE;
    }

    GString *paths = g_string_new(NULL);
    for (GSList *l = g_value_get_boxed(value); l; l = l->next)
    {
        char *path = g_file_get_path(G_FILE(l->data));
        if (path)
        {
            if (paths->len)
            {
                g_string_append_c(paths, '\n');
            }

            g_string_append(paths, path);
            g_free(path);
        }
    }

    gboolean any = paths->len > 0;
    if (any)
    {
        S.event(CHVD_EVENT_FILES_DROPPED, paths->str);
    }

    g_string_free(paths, TRUE);
    return any;
}

/* ── window ──────────────────────────────────────────────────────────────── */

/* Every way the window is asked to close arrives here: the title bar's close button, Alt F4, the desktop's
 * own "Close", and the in-app close (chvd_close). .NET hears of it first and may hold this one request
 * (chvd_hold_close, from inside the event) while it asks about unsaved work (D-190); it closes the window
 * itself afterwards if the answer allows. */
static gboolean on_close_request(GtkWindow *window, gpointer data)
{
    (void)window;
    (void)data;
    S.close_held = 0;
    S.event(CHVD_EVENT_CLOSE_REQUESTED, NULL);
    if (S.close_held)
    {
        S.close_held = 0;
        return TRUE; /* stay open */
    }

    return FALSE; /* let it close; .NET quits the loop on the destroy below */
}

/* From inside the close-requested event only: this request does not close the window. Main thread. */
CHVD_EXPORT void chvd_hold_close(void)
{
    S.close_held = 1;
}

static void on_destroy(GtkWidget *widget, gpointer data)
{
    (void)widget;
    (void)data;
    S.view = NULL;
    S.window = NULL;
    chvd_quit();
}

static void on_maximized(GObject *obj, GParamSpec *pspec, gpointer data)
{
    (void)pspec;
    (void)data;
    S.event(CHVD_EVENT_MAXIMIZED_CHANGED, gtk_window_is_maximized(GTK_WINDOW(obj)) ? "1" : "0");
}

/* Window CSS: the pre-paint background and the Linux frame from the design handout — 12 px
 * corners, square when maximised, tiled or full screen, and square without a compositor
 * (solid-csd: GTK can't draw transparent corners there). The child (the web view) is clipped
 * to the rounded box by overflow: hidden on the window. */
static char S_background[16] = "#F2EAD6";
static char S_mark[16] = "#8A3A1C";            /* the theme's accent */
static char S_mark_rule[40] = "rgba(26,19,16,0.45)";

static void apply_window_css(void)
{
    char *css = g_strdup_printf(
        "window.chvd { background-color: %s; border-radius: 12px; }"
        "window.chvd.maximized, window.chvd.fullscreen, window.chvd.tiled,"
        "window.chvd.tiled-top, window.chvd.tiled-bottom, window.chvd.tiled-left, window.chvd.tiled-right,"
        "window.chvd.solid-csd { border-radius: 0; }"
        /* The start-up mark: the splash's own 230 x 6 progress bar (Brand Assets), alone on the pre-paint
         * colour. GTK stops the animation itself when the desktop's animations are off. */
        ".chvd-cover { background-color: %s; transition: opacity 140ms ease-out; }"
        ".chvd-cover.done { opacity: 0; }"
        ".chvd-bar { min-width: 228px; min-height: 4px; border: 1px solid %s; }"
        ".chvd-bar-fill { min-width: 87px; min-height: 4px; background-color: %s;"
        "  animation: chvd-boot 1.2s ease-in-out infinite alternate; }"
        "@keyframes chvd-boot { from { transform: translateX(-9px); } to { transform: translateX(152px); } }",
        S_background, S_background, S_mark_rule, S_mark);
    gtk_css_provider_load_from_string(S.css, css);
    g_free(css);
}

/* Background as "#RRGGBB" — painted by both the window and the web view until the page paints. */
static void apply_background(const char *hex)
{
    GdkRGBA rgba;
    if (!hex || strlen(hex) != 7 || !gdk_rgba_parse(&rgba, hex))
    {
        return;
    }

    if (S.view)
    {
        webkit_web_view_set_background_color(S.view, &rgba);
    }

    g_strlcpy(S_background, hex, sizeof S_background);
    apply_window_css();
}

/* ── the start-up mark ───────────────────────────────────────────────────── */

CHVD_EXPORT void chvd_ready(void);

static gboolean remove_cover(gpointer data)
{
    (void)data;
    if (S.cover)
    {
        GtkWidget *overlay = gtk_widget_get_parent(S.cover);
        if (overlay && GTK_IS_OVERLAY(overlay))
        {
            gtk_overlay_remove_overlay(GTK_OVERLAY(overlay), S.cover);
        }

        S.cover = NULL;
    }

    return G_SOURCE_REMOVE;
}

static gboolean on_cover_fallback(gpointer data)
{
    (void)data;
    S.cover_fallback = 0;
    chvd_ready();
    return G_SOURCE_REMOVE;
}

static GtkWidget *make_cover(void)
{
    GtkWidget *cover = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(cover, "chvd-cover");
    gtk_widget_set_hexpand(cover, TRUE);
    gtk_widget_set_vexpand(cover, TRUE);

    GtkWidget *bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_add_css_class(bar, "chvd-bar");
    gtk_widget_set_halign(bar, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(bar, GTK_ALIGN_CENTER);
    gtk_widget_set_hexpand(bar, TRUE);
    gtk_widget_set_vexpand(bar, TRUE);
    gtk_widget_set_overflow(bar, GTK_OVERFLOW_HIDDEN);

    GtkWidget *fill = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_add_css_class(fill, "chvd-bar-fill");
    gtk_widget_set_halign(fill, GTK_ALIGN_START);
    gtk_box_append(GTK_BOX(bar), fill);
    gtk_box_append(GTK_BOX(cover), bar);
    return cover;
}

/* The mark's colours for the saved theme: accent "#RRGGBB" and the bar's outline (any CSS colour). Before chvd_show. */
CHVD_EXPORT void chvd_start_mark(const char *accent, const char *rule)
{
    GdkRGBA rgba;
    if (accent && strlen(accent) == 7 && gdk_rgba_parse(&rgba, accent))
    {
        g_strlcpy(S_mark, accent, sizeof S_mark);
    }

    if (rule && strlen(rule) < sizeof S_mark_rule && gdk_rgba_parse(&rgba, rule))
    {
        g_strlcpy(S_mark_rule, rule, sizeof S_mark_rule);
    }

    if (S.css)
    {
        apply_window_css();
    }
}

/* The app has drawn itself: the start-up mark fades out and goes. Safe to call more than once. Main thread. */
CHVD_EXPORT void chvd_ready(void)
{
    if (S.cover_fallback)
    {
        g_source_remove(S.cover_fallback);
        S.cover_fallback = 0;
    }

    if (S.cover && !gtk_widget_has_css_class(S.cover, "done"))
    {
        gtk_widget_add_css_class(S.cover, "done");
        gtk_widget_set_can_target(S.cover, FALSE);
        g_timeout_add(170, remove_cover, NULL);
    }
}

/* 1 while the start-up mark is still over the page (UI tests). */
CHVD_EXPORT int chvd_start_mark_shown(void)
{
    return S.cover ? 1 : 0;
}

/* ── the session: signing out and shutting down (D-194) ────────────────────── */

/* A sign-out or shutdown doesn't ask the window to close: the desktop ends the session and the process with
 * it. It can only be held by a lock on the session, taken through D-Bus (GLib's own; nothing external):
 *
 *   - org.freedesktop.portal.Inhibit, the cross-desktop way (GNOME, KDE and others implement it):
 *     Inhibit(window, 1 = logout, {reason}) takes the lock, closing the request it returns gives it up;
 *     CreateMonitor tells us when the session is about to end ("query-end"), and the desktop then waits
 *     about a second for QueryEndResponse, so a lock taken at that moment still counts.
 *   - org.gnome.SessionManager Inhibit / Uninhibit, where there is no portal.
 *
 * While the lock is held the desktop itself tells the person that Chuvadi has unsaved work and offers to
 * cancel or go on regardless. .NET decides when to hold (chvd_session_hold) and, on "query-end", asks the
 * person in the window. No session bus, no portal, no GNOME session manager: nothing is held, as before. */

#define PORTAL_NAME "org.freedesktop.portal.Desktop"
#define PORTAL_PATH "/org/freedesktop/portal/desktop"
#define PORTAL_INHIBIT "org.freedesktop.portal.Inhibit"
#define GNOME_SM_NAME "org.gnome.SessionManager"
#define GNOME_SM_PATH "/org/gnome/SessionManager"

static void session_answer_query_end(void)
{
    if (S.query_end_owed && !S.hold_pending && S.bus && S.monitor_path)
    {
        S.query_end_owed = 0;
        g_dbus_connection_call(S.bus, PORTAL_NAME, PORTAL_PATH, PORTAL_INHIBIT, "QueryEndResponse",
                               g_variant_new("(o)", S.monitor_path), NULL, G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
    }
}

static void session_stop_listening_for_refusal(void)
{
    if (S.hold_refusal)
    {
        g_dbus_connection_signal_unsubscribe(S.bus, S.hold_refusal);
        S.hold_refusal = 0;
    }

    g_clear_pointer(&S.hold_request_named, g_free);
}

static void session_release(void)
{
    if (!S.bus)
    {
        return;
    }

    session_stop_listening_for_refusal();
    if (S.hold_request)
    {
        g_dbus_connection_call(S.bus, PORTAL_NAME, S.hold_request, "org.freedesktop.portal.Request", "Close",
                               NULL, NULL, G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
        g_clear_pointer(&S.hold_request, g_free);
    }

    if (S.hold_cookie)
    {
        g_dbus_connection_call(S.bus, GNOME_SM_NAME, GNOME_SM_PATH, GNOME_SM_NAME, "Uninhibit",
                               g_variant_new("(u)", S.hold_cookie), NULL, G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
        S.hold_cookie = 0;
    }
}

/* A call asking for the hold has ended, with or without one. */
static void session_hold_settled(void)
{
    S.hold_pending = 0;
    if (!S.hold_reason)
    {
        session_release(); /* no longer wanted: it was given up while the call was under way */
    }

    session_answer_query_end();
}

static void on_gnome_inhibit(GObject *source, GAsyncResult *result, gpointer data)
{
    (void)data;
    GVariant *reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, NULL);
    if (reply)
    {
        g_variant_get(reply, "(u)", &S.hold_cookie);
        g_variant_unref(reply);
    }

    session_hold_settled();
}

/* The GNOME session manager's own call: where there is no portal, or the portal's desktop said no. */
static void session_take_from_gnome(void)
{
    S.hold_pending = 1;
    g_dbus_connection_call(S.bus, GNOME_SM_NAME, GNOME_SM_PATH, GNOME_SM_NAME, "Inhibit",
                           g_variant_new("(susu)", g_get_prgname() ? g_get_prgname() : "chuvadi-reader", (guint32)0,
                                         S.hold_reason, (guint32)1 /* logout */),
                           G_VARIANT_TYPE("(u)"), G_DBUS_CALL_FLAGS_NONE, -1, NULL, on_gnome_inhibit, NULL);
}

static void on_portal_inhibit(GObject *source, GAsyncResult *result, gpointer data)
{
    (void)data;
    GVariant *reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, NULL);
    if (reply)
    {
        if (S.hold_request_named)
        {
            g_variant_get(reply, "(o)", &S.hold_request); /* still ours: not refused in the meantime */
        }

        g_variant_unref(reply);
        if (S.hold_request || !S.hold_reason)
        {
            session_hold_settled();
        }

        return; /* refused before the reply: on_portal_refusal has already gone on to the session manager */
    }

    session_stop_listening_for_refusal();
    if (!S.hold_reason)
    {
        session_hold_settled();
        return;
    }

    session_take_from_gnome(); /* no portal, or it has no Inhibit */
}

/* The portal took the call but its desktop refused the lock: the request ends with a Response other than 0
 * (a lock that is granted sends none and simply stays). A refused request is not a lock (Linux Test B-35). */
static void on_portal_refusal(GDBusConnection *bus, const char *sender, const char *path, const char *iface,
                              const char *signal, GVariant *params, gpointer data)
{
    (void)bus;
    (void)sender;
    (void)iface;
    (void)signal;
    (void)data;
    guint32 response = 0;
    g_variant_get_child(params, 0, "u", &response);
    if (response == 0 || !S.hold_request_named || g_strcmp0(path, S.hold_request_named) != 0)
    {
        return;
    }

    session_stop_listening_for_refusal();
    g_clear_pointer(&S.hold_request, g_free); /* the request is gone with its Response: nothing to close */
    if (S.hold_reason && !S.hold_cookie)
    {
        session_take_from_gnome();
    }
    else
    {
        session_hold_settled();
    }
}

static void session_take(void)
{
    if (!S.bus || !S.hold_reason || S.hold_pending || S.hold_request || S.hold_cookie)
    {
        return;
    }

    /* The request's path is ours to name, so its refusal can be listened for before the call is made. */
    char *token = g_strdup_printf("chvd_hold%u", ++S.hold_serial);
    char *sender = g_strdup(g_dbus_connection_get_unique_name(S.bus) + 1);
    g_strdelimit(sender, ".", '_');
    S.hold_request_named = g_strdup_printf(PORTAL_PATH "/request/%s/%s", sender, token);
    g_free(sender);
    S.hold_refusal = g_dbus_connection_signal_subscribe(S.bus, PORTAL_NAME, "org.freedesktop.portal.Request", "Response",
                                                        S.hold_request_named, NULL, G_DBUS_SIGNAL_FLAGS_NONE,
                                                        on_portal_refusal, NULL, NULL);
    GVariantBuilder options;
    g_variant_builder_init(&options, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&options, "{sv}", "handle_token", g_variant_new_string(token));
    g_variant_builder_add(&options, "{sv}", "reason", g_variant_new_string(S.hold_reason));
    g_free(token);
    S.hold_pending = 1;
    g_dbus_connection_call(S.bus, PORTAL_NAME, PORTAL_PATH, PORTAL_INHIBIT, "Inhibit",
                           g_variant_new("(sua{sv})", "", (guint32)1 /* logout */, &options),
                           G_VARIANT_TYPE("(o)"), G_DBUS_CALL_FLAGS_NONE, -1, NULL, on_portal_inhibit, NULL);
}

/* The portal's monitor: session-state 1 running, 2 query-end (about to end, the desktop waits for
 * QueryEndResponse), 3 ending (too late to ask). */
static void on_session_state(GDBusConnection *bus, const char *sender, const char *path, const char *iface,
                             const char *signal, GVariant *params, gpointer data)
{
    (void)bus;
    (void)sender;
    (void)path;
    (void)iface;
    (void)signal;
    (void)data;
    const char *session = NULL;
    GVariant *state = NULL;
    guint32 phase = 0;
    g_variant_get(params, "(&o@a{sv})", &session, &state);
    gboolean ours = S.monitor_path && g_strcmp0(session, S.monitor_path) == 0;
    gboolean known = g_variant_lookup(state, "session-state", "u", &phase);
    g_variant_unref(state);
    if (!ours || !known || phase != 2)
    {
        return;
    }

    S.query_end_owed = 1;
    if (S.event)
    {
        S.event(CHVD_EVENT_SESSION_END, "query"); /* .NET may call chvd_session_hold from inside this */
    }

    session_answer_query_end(); /* at once, or when the hold just asked for is in place */
}

static void on_session_bus(GObject *source, GAsyncResult *result, gpointer data)
{
    (void)source;
    (void)data;
    S.bus = g_bus_get_finish(result, NULL);
    if (!S.bus)
    {
        return;
    }

    g_dbus_connection_set_exit_on_close(S.bus, FALSE);

    /* The monitor's object path is ours to name: .../session/<our bus name, as a path element>/<token>. */
    char *sender = g_strdup(g_dbus_connection_get_unique_name(S.bus) + 1);
    for (char *c = sender; *c; c++)
    {
        if (*c == '.')
        {
            *c = '_';
        }
    }

    S.monitor_path = g_strdup_printf(PORTAL_PATH "/session/%s/chvd_session", sender);
    g_free(sender);
    S.monitor_signal = g_dbus_connection_signal_subscribe(S.bus, PORTAL_NAME, PORTAL_INHIBIT, "StateChanged", PORTAL_PATH,
                                                          NULL, G_DBUS_SIGNAL_FLAGS_NONE, on_session_state, NULL, NULL);
    GVariantBuilder options;
    g_variant_builder_init(&options, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&options, "{sv}", "handle_token", g_variant_new_string("chvd_monitor"));
    g_variant_builder_add(&options, "{sv}", "session_handle_token", g_variant_new_string("chvd_session"));
    g_dbus_connection_call(S.bus, PORTAL_NAME, PORTAL_PATH, PORTAL_INHIBIT, "CreateMonitor",
                           g_variant_new("(sa{sv})", "", &options), NULL, G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
    session_take(); /* wanted before the bus was there */
}

/* Starts listening for the session's end. Once, after chvd_init. Main thread. Does nothing where there is no
 * session bus (and never starts one). */
CHVD_EXPORT void chvd_session_watch(void)
{
    if (S.bus || S.monitor_path)
    {
        return;
    }

    const char *address = g_getenv("DBUS_SESSION_BUS_ADDRESS");
    char *socket = g_build_filename(g_get_user_runtime_dir(), "bus", NULL);
    gboolean there = (address && *address) || g_file_test(socket, G_FILE_TEST_EXISTS);
    g_free(socket);
    if (there)
    {
        g_bus_get(G_BUS_TYPE_SESSION, NULL, on_session_bus, NULL);
    }
}

/* reason: why a sign-out or shutdown should wait (shown by the desktop), or NULL to let it go. Safe to call
 * again with the same answer. Main thread. */
CHVD_EXPORT void chvd_session_hold(const char *reason)
{
    g_free(S.hold_reason);
    S.hold_reason = reason && *reason ? g_strdup(reason) : NULL;
    if (S.hold_reason)
    {
        session_take();
    }
    else if (!S.hold_pending)
    {
        session_release();
    }
}

/* 0 nothing held, 1 being asked for, 2 held through the portal, 3 held through the GNOME session manager (UI tests). */
CHVD_EXPORT int chvd_session_hold_state(void)
{
    return S.hold_request ? 2 : S.hold_cookie ? 3 : S.hold_pending ? 1 : 0;
}

/* ── pinch ───────────────────────────────────────────────────────────────── */

/* Passes the pinch to the Reader's shared entry (patch 27): window.chuvadiPinch(phase, scale, x, y), phase
 * 'begin' | 'change' | 'end', scale since 'begin', x, y in the page's CSS pixels. WebKitGTK gives the page no
 * trackpad pinch; it would zoom the whole web page instead, which the claim below stops. The entry exists once a
 * view that zooms is open: on Home and Settings there is none, and nothing moves. x, y: view coordinates. */
static void forward_pinch(const char *phase, double scale, double x, double y)
{
    if (!S.view || !(scale > 0) || !isfinite(scale))
    {
        return;
    }

    double level = webkit_web_view_get_zoom_level(S.view);
    if (level > 0)
    {
        x /= level;
        y /= level;
    }

    char bs[G_ASCII_DTOSTR_BUF_SIZE], bx[G_ASCII_DTOSTR_BUF_SIZE], by[G_ASCII_DTOSTR_BUF_SIZE];
    g_ascii_formatd(bs, sizeof bs, "%.5f", scale);
    g_ascii_formatd(bx, sizeof bx, "%.2f", x);
    g_ascii_formatd(by, sizeof by, "%.2f", y);
    char *script = g_strdup_printf("window.chuvadiPinch&&window.chuvadiPinch('%s',%s,%s,%s);", phase, bs, bx, by);
    webkit_web_view_evaluate_javascript(S.view, script, -1, NULL, NULL, NULL, NULL, NULL);
    g_free(script);
}

static void pinch_place(GtkGesture *gesture, double *x, double *y)
{
    if (!gtk_gesture_get_bounding_box_center(gesture, x, y))
    {
        *x = gtk_widget_get_width(GTK_WIDGET(S.view)) / 2.0;
        *y = gtk_widget_get_height(GTK_WIDGET(S.view)) / 2.0;
    }
}

/* Pinch-to-zoom (touchpad or touch screen) would zoom the whole page; the Reader zooms its own
 * canvas. Claim the gesture before WebKit sees it, as the Windows host turns off pinch zoom. */
static void on_zoom_begin(GtkGesture *gesture, GdkEventSequence *sequence, gpointer data)
{
    (void)data;
    (void)sequence;
    gtk_gesture_set_state(gesture, GTK_EVENT_SEQUENCE_CLAIMED);
    double x, y;
    pinch_place(gesture, &x, &y);
    S.pinch_scale = 1.0;
    forward_pinch("begin", 1.0, x, y);
}

/* scale: the pinch so far, 1.0 at its start. */
static void on_zoom_scale_changed(GtkGestureZoom *gesture, double scale, gpointer data)
{
    (void)data;
    if (!(scale > 0) || !(S.pinch_scale > 0) || fabs(scale / S.pinch_scale - 1.0) < 0.003)
    {
        return; /* not begun, or too small a change to see: it is in the next one */
    }

    double x, y;
    pinch_place(GTK_GESTURE(gesture), &x, &y);
    S.pinch_scale = scale;
    forward_pinch("change", scale, x, y);
}

/* The fingers lifted, or the gesture was taken away: the Reader settles on the zoom it has. */
static void on_zoom_end(GtkGesture *gesture, GdkEventSequence *sequence, gpointer data)
{
    (void)gesture;
    (void)sequence;
    (void)data;
    if (S.pinch_scale > 0)
    {
        S.pinch_scale = 0;
        forward_pinch("end", 1.0, 0, 0);
    }
}

/* One step of a pinch at a place in the view, as the gesture sends it (UI tests: a pinch can't be made under
 * Xvfb). phase: 0 begin, 1 change, 2 end; scale: since the begin. */
CHVD_EXPORT void chvd_pinch(int phase, double scale, double x, double y)
{
    forward_pinch(phase == 0 ? "begin" : phase == 1 ? "change" : "end", scale, x, y);
}

/*
 * Creates the window and its web view (not yet shown).
 *   app_id     — also the WM_CLASS / Wayland app id, so the desktop entry's icon matches
 *   background — "#RRGGBB" pre-paint colour for the saved theme
 *   dev_tools  — non-zero only in Debug builds (Inspect element)
 */
CHVD_EXPORT int chvd_create_window(const char *title, const char *app_id, int width, int height,
                                   const char *background, int dev_tools)
{
    if (app_id && *app_id)
    {
        g_set_prgname(app_id);
    }

    S.css = gtk_css_provider_new();
    gtk_style_context_add_provider_for_display(gdk_display_get_default(), GTK_STYLE_PROVIDER(S.css),
                                               GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);

    GtkWidget *window = gtk_window_new();
    S.window = GTK_WINDOW(window);
    gtk_widget_add_css_class(window, "chvd");
    gtk_window_set_title(S.window, title ? title : "Chuvadi");
    gtk_window_set_default_size(S.window, width, height);

    /* Custom chrome: the HTML title bar replaces the system one. An empty, zero-height
     * titlebar widget keeps client-side decorations (shadow, rounded corners, resize edges)
     * while removing the header bar itself. */
    GtkWidget *no_titlebar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_visible(no_titlebar, FALSE);
    gtk_window_set_titlebar(S.window, no_titlebar);

    /* The web view, with the bridge script and the app:// scheme. */
    WebKitWebContext *context = webkit_web_context_new();
    webkit_web_context_set_cache_model(context, WEBKIT_CACHE_MODEL_DOCUMENT_VIEWER);
    webkit_web_context_register_uri_scheme(context, CHVD_SCHEME, on_scheme_request, NULL, NULL);

    WebKitSecurityManager *security = webkit_web_context_get_security_manager(context);
    webkit_security_manager_register_uri_scheme_as_secure(security, CHVD_SCHEME);
    webkit_security_manager_register_uri_scheme_as_cors_enabled(security, CHVD_SCHEME);

    WebKitUserContentManager *ucm = webkit_user_content_manager_new();
    WebKitUserScript *bridge = webkit_user_script_new(BRIDGE_JS, WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
                                                      WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, bridge);
    webkit_user_script_unref(bridge);
    g_signal_connect(ucm, "script-message-received::" CHVD_HANDLER, G_CALLBACK(on_script_message), NULL);
    webkit_user_content_manager_register_script_message_handler(ucm, CHVD_HANDLER, NULL);

    WebKitSettings *settings = webkit_settings_new();
    webkit_settings_set_enable_developer_extras(settings, dev_tools ? TRUE : FALSE);
    webkit_settings_set_javascript_can_access_clipboard(settings, TRUE);
    webkit_settings_set_enable_back_forward_navigation_gestures(settings, FALSE);
    webkit_settings_set_enable_page_cache(settings, FALSE);
    /* B-12: without a GPU, WebKit's GL compositing runs in software, and on a person's first launch Mesa
     * compiles its shaders on the CPU first (again after every Mesa update): measured 4.7 s before the
     * page shows on a fresh profile, 1.5 s with compositing off (BUILD-LOG §37). With a GPU, WebKit's
     * default stays; WEBKIT_DISABLE_COMPOSITING_MODE set by the person still applies either way. */
    if (S.no_gpu)
    {
        webkit_settings_set_hardware_acceleration_policy(settings, WEBKIT_HARDWARE_ACCELERATION_POLICY_NEVER);
    }

    /* Ephemeral session: nothing is written to disk (no profile, cache or web storage), so an
     * updated app can never be served a previous version's assets. App state lives in .NET
     * (IAppStorage), not in web storage, exactly as on Windows. */
    WebKitNetworkSession *session = webkit_network_session_new_ephemeral();

    S.view = WEBKIT_WEB_VIEW(g_object_new(WEBKIT_TYPE_WEB_VIEW, "web-context", context, "network-session", session,
                                          "user-content-manager", ucm, "settings", settings, NULL));
    g_object_unref(session);
    g_object_unref(settings);
    g_object_unref(ucm);
    g_object_unref(context);

    g_signal_connect(S.view, "decide-policy", G_CALLBACK(on_decide_policy), NULL);
    g_signal_connect(S.view, "load-changed", G_CALLBACK(on_load_changed), NULL);

    GtkGesture *click = gtk_gesture_click_new();
    gtk_gesture_single_set_button(GTK_GESTURE_SINGLE(click), 0);
    gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(click), GTK_PHASE_CAPTURE);
    g_signal_connect(click, "pressed", G_CALLBACK(on_press), NULL);
    gtk_widget_add_controller(GTK_WIDGET(S.view), GTK_EVENT_CONTROLLER(click));

    /* Window-level file drop, captured before the web view, as the Windows host does. */
    GtkDropTarget *drop = gtk_drop_target_new(GDK_TYPE_FILE_LIST, GDK_ACTION_COPY);
    gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(drop), GTK_PHASE_CAPTURE);
    g_signal_connect(drop, "drop", G_CALLBACK(on_drop), NULL);
    gtk_widget_add_controller(window, GTK_EVENT_CONTROLLER(drop));

    GtkGesture *zoom = gtk_gesture_zoom_new();
    gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(zoom), GTK_PHASE_CAPTURE);
    g_signal_connect(zoom, "begin", G_CALLBACK(on_zoom_begin), NULL);
    g_signal_connect(zoom, "scale-changed", G_CALLBACK(on_zoom_scale_changed), NULL);
    g_signal_connect(zoom, "end", G_CALLBACK(on_zoom_end), NULL);
    g_signal_connect(zoom, "cancel", G_CALLBACK(on_zoom_end), NULL);
    gtk_widget_add_controller(GTK_WIDGET(S.view), GTK_EVENT_CONTROLLER(zoom));

    /* The web view under the start-up mark (make_cover), which goes at the app's first render. */
    GtkWidget *overlay = gtk_overlay_new();
    gtk_overlay_set_child(GTK_OVERLAY(overlay), GTK_WIDGET(S.view));
    S.cover = make_cover();
    gtk_overlay_add_overlay(GTK_OVERLAY(overlay), S.cover);
    gtk_window_set_child(S.window, overlay);
    gtk_widget_set_overflow(window, GTK_OVERFLOW_HIDDEN);
    apply_background(background);

    g_signal_connect(window, "close-request", G_CALLBACK(on_close_request), NULL);
    g_signal_connect(window, "destroy", G_CALLBACK(on_destroy), NULL);
    g_signal_connect(window, "notify::maximized", G_CALLBACK(on_maximized), NULL);
    return 1;
}

CHVD_EXPORT void chvd_show(int maximized)
{
    if (!S.window)
    {
        return;
    }

    if (maximized)
    {
        gtk_window_maximize(S.window);
    }

    /* If the app never reports its first render, the page (and whatever it says) still shows: as the Windows splash. */
    if (S.cover && !S.cover_fallback)
    {
        S.cover_fallback = g_timeout_add_seconds(20, on_cover_fallback, NULL);
    }

    gtk_window_present(S.window);
}

CHVD_EXPORT void chvd_navigate(const char *uri)
{
    if (S.view)
    {
        webkit_web_view_load_uri(S.view, uri);
    }
}

CHVD_EXPORT void chvd_set_zoom(double factor)
{
    if (S.view && factor > 0)
    {
        webkit_web_view_set_zoom_level(S.view, factor);
    }
}

CHVD_EXPORT void chvd_set_background(const char *hex)
{
    apply_background(hex);
}

CHVD_EXPORT void chvd_minimize(void)
{
    if (S.window)
    {
        gtk_window_minimize(S.window);
    }
}

CHVD_EXPORT void chvd_toggle_maximize(void)
{
    if (!S.window)
    {
        return;
    }

    if (gtk_window_is_maximized(S.window))
    {
        gtk_window_unmaximize(S.window);
    }
    else
    {
        gtk_window_maximize(S.window);
    }
}

CHVD_EXPORT int chvd_is_maximized(void)
{
    return S.window && gtk_window_is_maximized(S.window);
}

CHVD_EXPORT void chvd_close(void)
{
    if (S.window)
    {
        gtk_window_close(S.window);
    }
}

/* Starts a compositor-driven window move from the last press inside the view
 * (the HTML title bar's mousedown). Does nothing while maximised, as on Windows. */
CHVD_EXPORT void chvd_begin_move(void)
{
    if (!S.window || !S.press_device || gtk_window_is_maximized(S.window))
    {
        return;
    }

    GtkNative *native = gtk_widget_get_native(GTK_WIDGET(S.view));
    GdkSurface *surface = native ? gtk_native_get_surface(native) : NULL;
    if (!surface || !GDK_IS_TOPLEVEL(surface))
    {
        return;
    }

    /* The page's mouse-down reaches here one round trip later; if the button is already up, a
       move would start with nothing to end it (the window would follow the pointer). Skip it. */
    GdkModifierType held = 0;
    double px = 0, py = 0;
    if (gdk_surface_get_device_position(surface, S.press_device, &px, &py, &held))
    {
        int b = S.press_button ? S.press_button : 1;
        GdkModifierType need = b == 1 ? GDK_BUTTON1_MASK : b == 2 ? GDK_BUTTON2_MASK : GDK_BUTTON3_MASK;
        if (!(held & need))
        {
            return;
        }
    }

    graphene_point_t in = GRAPHENE_POINT_INIT((float)S.press_x, (float)S.press_y), out;
    if (!gtk_widget_compute_point(GTK_WIDGET(S.view), GTK_WIDGET(native), &in, &out))
    {
        return;
    }

    double sx = 0, sy = 0;
    gtk_native_get_surface_transform(native, &sx, &sy);
    gdk_toplevel_begin_move(GDK_TOPLEVEL(surface), S.press_device, S.press_button ? S.press_button : 1,
                            out.x + sx, out.y + sy, S.press_time);
}

/* Puts PNG bytes on the system clipboard as an image. Returns 0 if the bytes don't decode. */
CHVD_EXPORT int chvd_clipboard_set_png(const void *bytes, gsize length)
{
    GBytes *data = g_bytes_new(bytes, length);
    GError *error = NULL;
    GdkTexture *texture = gdk_texture_new_from_bytes(data, &error);
    g_bytes_unref(data);
    if (!texture)
    {
        g_clear_error(&error);
        return 0;
    }

    gdk_clipboard_set_texture(gdk_display_get_clipboard(gdk_display_get_default()), texture);
    g_object_unref(texture);
    return 1;
}

/* ── file dialogs (GtkFileDialog: the desktop portal's own dialog on GNOME and KDE) ── */

enum
{
    CHVD_DIALOG_OPEN = 0,
    CHVD_DIALOG_OPEN_MULTIPLE = 1,
    CHVD_DIALOG_SAVE = 2,
    CHVD_DIALOG_FOLDER = 3,
};

typedef struct
{
    int kind;
    int token;
} DialogCall;

static void append_path(GString *out, GFile *file)
{
    char *path = file ? g_file_get_path(file) : NULL;
    if (path)
    {
        g_string_append_c(out, '\n');
        g_string_append(out, path);
        g_free(path);
    }
}

static void on_dialog_done(GObject *source, GAsyncResult *result, gpointer data)
{
    DialogCall *call = data;
    GtkFileDialog *dialog = GTK_FILE_DIALOG(source);
    GError *error = NULL;
    GString *out = g_string_new(NULL);
    g_string_printf(out, "%d", call->token);

    if (call->kind == CHVD_DIALOG_OPEN_MULTIPLE)
    {
        GListModel *files = gtk_file_dialog_open_multiple_finish(dialog, result, &error);
        if (files)
        {
            guint n = g_list_model_get_n_items(files);
            for (guint i = 0; i < n; i++)
            {
                GFile *file = g_list_model_get_item(files, i);
                append_path(out, file);
                g_object_unref(file);
            }

            g_object_unref(files);
        }
    }
    else
    {
        GFile *file = NULL;
        switch (call->kind)
        {
        case CHVD_DIALOG_OPEN:
            file = gtk_file_dialog_open_finish(dialog, result, &error);
            break;
        case CHVD_DIALOG_SAVE:
            file = gtk_file_dialog_save_finish(dialog, result, &error);
            break;
        default:
            file = gtk_file_dialog_select_folder_finish(dialog, result, &error);
            break;
        }

        append_path(out, file);
        g_clear_object(&file);
    }

    g_clear_error(&error); /* cancelled or dismissed: report no paths */
    S.event(CHVD_EVENT_DIALOG_RESULT, out->str);
    g_string_free(out, TRUE);
    g_free(call);
}

/* filters: one per line, "Label|*.pdf;*.docx". The first filter is the default. */
static GListModel *make_filters(const char *spec, GtkFileFilter **first)
{
    GListStore *store = g_list_store_new(GTK_TYPE_FILE_FILTER);
    *first = NULL;
    if (!spec || !*spec)
    {
        return G_LIST_MODEL(store);
    }

    char **lines = g_strsplit(spec, "\n", -1);
    for (char **line = lines; *line; line++)
    {
        char **parts = g_strsplit(*line, "|", 2);
        if (parts[0] && parts[1])
        {
            GtkFileFilter *filter = gtk_file_filter_new();
            gtk_file_filter_set_name(filter, parts[0]);
            char **patterns = g_strsplit(parts[1], ";", -1);
            for (char **pat = patterns; *pat; pat++)
            {
                if (**pat)
                {
                    /* suffixes match case-insensitively (*.PDF too) */
                    if (g_str_has_prefix(*pat, "*.") && (*pat)[2])
                    {
                        gtk_file_filter_add_suffix(filter, *pat + 2);
                    }
                    else
                    {
                        gtk_file_filter_add_pattern(filter, *pat);
                    }
                }
            }

            g_strfreev(patterns);
            g_list_store_append(store, filter);
            if (!*first)
            {
                *first = filter;
            }

            g_object_unref(filter);
        }

        g_strfreev(parts);
    }

    g_strfreev(lines);
    return G_LIST_MODEL(store);
}

/* Shows a dialog modal to the main window. The answer arrives later as CHVD_EVENT_DIALOG_RESULT. */
CHVD_EXPORT void chvd_file_dialog(int kind, int token, const char *title, const char *initial_folder,
                                  const char *initial_name, const char *filters)
{
    GtkFileDialog *dialog = gtk_file_dialog_new();
    gtk_file_dialog_set_modal(dialog, TRUE);
    if (title && *title)
    {
        gtk_file_dialog_set_title(dialog, title);
    }

    if (initial_folder && *initial_folder)
    {
        GFile *folder = g_file_new_for_path(initial_folder);
        gtk_file_dialog_set_initial_folder(dialog, folder);
        g_object_unref(folder);
    }

    if (kind == CHVD_DIALOG_SAVE && initial_name && *initial_name)
    {
        gtk_file_dialog_set_initial_name(dialog, initial_name);
    }

    if (kind != CHVD_DIALOG_FOLDER)
    {
        GtkFileFilter *first = NULL;
        GListModel *list = make_filters(filters, &first);
        gtk_file_dialog_set_filters(dialog, list);
        if (first)
        {
            gtk_file_dialog_set_default_filter(dialog, first);
        }

        g_object_unref(list);
    }

    DialogCall *call = g_new0(DialogCall, 1);
    call->kind = kind;
    call->token = token;

    switch (kind)
    {
    case CHVD_DIALOG_OPEN:
        gtk_file_dialog_open(dialog, S.window, NULL, on_dialog_done, call);
        break;
    case CHVD_DIALOG_OPEN_MULTIPLE:
        gtk_file_dialog_open_multiple(dialog, S.window, NULL, on_dialog_done, call);
        break;
    case CHVD_DIALOG_SAVE:
        gtk_file_dialog_save(dialog, S.window, NULL, on_dialog_done, call);
        break;
    default:
        gtk_file_dialog_select_folder(dialog, S.window, NULL, on_dialog_done, call);
        break;
    }

    g_object_unref(dialog); /* the async call keeps its own reference */
}

/* Puts text on the system clipboard. Main thread. */
CHVD_EXPORT void chvd_clipboard_set_text(const char *text)
{
    gdk_clipboard_set_text(gdk_display_get_clipboard(gdk_display_get_default()), text ? text : "");
}

/* The desktop's window-button layout as GTK sees it (gtk-decoration-layout: GNOME's button-layout,
 * KDE's GTK settings), e.g. "appmenu:minimize,maximize,close" or "close:" — copied into buf
 * (NUL-terminated, cut at size - 1). The .NET side parses it the way GTK's header bar does. Returns
 * the full length, or -1 when the setting is unset. Main thread, after chvd_init. */
CHVD_EXPORT int chvd_button_layout(char *buf, int size)
{
    char *layout = NULL;
    g_object_get(gtk_settings_get_default(), "gtk-decoration-layout", &layout, NULL);
    if (!layout)
    {
        if (buf && size > 0)
        {
            buf[0] = 0;
        }
        return -1;
    }

    int len = (int)strlen(layout);
    if (buf && size > 0)
    {
        g_strlcpy(buf, layout, (gsize)size);
    }
    g_free(layout);
    return len;
}

/* B-15: WebKit renders pages inside a sandbox (bubblewrap) that needs unprivileged user namespaces. Where
 * they're unavailable (a hardened kernel, Docker's default seccomp, Ubuntu 24.04+ without the AppArmor
 * profile) WebKit aborts with a GLib error and no window. This runs bubblewrap once the way WebKit does
 * (same namespace switches), before any web view exists. Returns 1 when it starts (or when there's nothing
 * to check: no bwrap, or the person turned WebKit's sandbox off), 0 otherwise with bwrap's message in buf. */
CHVD_EXPORT int chvd_sandbox_check(char *buf, int size)
{
    if (buf && size > 0)
    {
        buf[0] = 0;
    }

    if (g_getenv("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"))
    {
        return 1;
    }

    gchar *bwrap = g_find_program_in_path("bwrap");
    if (!bwrap)
    {
        return 1;
    }

    gchar *argv[] = {bwrap, "--ro-bind", "/", "/", "--unshare-user", "--unshare-pid", "--unshare-ipc",
                     "--unshare-uts", "--unshare-cgroup-try", "--die-with-parent", "/bin/true", NULL};
    gchar *err = NULL;
    gint status = 0;
    GError *error = NULL;
    gboolean ran = g_spawn_sync(NULL, argv, NULL, G_SPAWN_STDOUT_TO_DEV_NULL, NULL, NULL, NULL, &err, &status, &error);
    gboolean ok = ran && g_spawn_check_wait_status(status, NULL);
    if (!ok && buf && size > 0)
    {
        g_strlcpy(buf, error ? error->message : (err && *err ? g_strstrip(err) : "bubblewrap could not start"), (gsize)size);
    }

    g_clear_error(&error);
    g_free(err);
    g_free(bwrap);
    return ok ? 1 : 0;
}

static void on_alert_done(GObject *source, GAsyncResult *result, gpointer loop)
{
    gtk_alert_dialog_choose_finish(GTK_ALERT_DIALOG(source), result, NULL);
    g_main_loop_quit(loop);
}

/* A plain message window for a problem that stops Chuvadi before its own window exists (B-15). Blocks until
 * the person closes it. Main thread, after chvd_init. */
CHVD_EXPORT void chvd_show_error(const char *title, const char *detail)
{
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", title);
    gtk_alert_dialog_set_detail(dialog, detail);
    const char *buttons[] = {"Close", NULL};
    gtk_alert_dialog_set_buttons(dialog, buttons);
    gtk_alert_dialog_set_cancel_button(dialog, 0);
    gtk_alert_dialog_set_default_button(dialog, 0);
    GMainLoop *loop = g_main_loop_new(NULL, FALSE);
    gtk_alert_dialog_choose(dialog, NULL, NULL, on_alert_done, loop);
    g_main_loop_run(loop);
    g_main_loop_unref(loop);
    g_object_unref(dialog);
}

/* Brings the window to the front for a file handed over by another launch (single instance, the kit's
 * DesktopSingleInstance). token: the launcher's activation token (Wayland's XDG_ACTIVATION_TOKEN, X11's
 * startup id) so the desktop lets the window come forward; NULL when the launcher gave none. Main thread. */
CHVD_EXPORT void chvd_present(const char *token)
{
    if (!S.window)
    {
        return;
    }

    if (token && *token)
    {
        gtk_window_set_startup_id(S.window, token);
    }
    gtk_window_present(S.window);
}

/* What the host decided at start-up (UI tests read it): bit 0 = no GPU (no DRM render node), bit 1 = WebKit's
 * hardware acceleration policy is "never" (compositing off). Main thread, after chvd_create_window. */
CHVD_EXPORT int chvd_render_info(void)
{
    int info = S.no_gpu ? 1 : 0;
    if (S.view)
    {
        WebKitSettings *settings = webkit_web_view_get_settings(S.view);
        if (webkit_settings_get_hardware_acceleration_policy(settings) == WEBKIT_HARDWARE_ACCELERATION_POLICY_NEVER)
        {
            info |= 2;
        }
    }
    return info;
}

/* "Show in folder": asks the desktop's file manager to open the folder with the file selected
 * (freedesktop org.freedesktop.FileManager1.ShowItems — Nautilus, Dolphin, Nemo, Thunar…).
 * Returns 1 when a file manager took the request (or is still opening its window: a slow first window
 * is not a failure), 0 only when there is no file manager service, so the caller falls back to opening
 * the folder. B-21: with a short timeout, a slow Nautilus first got the fallback (one window) and then
 * answered (a second window). Any thread (GDBus sync calls are thread-safe); blocks up to 30 s. */
CHVD_EXPORT int chvd_reveal(const char *path)
{
    if (!path || !*path)
    {
        return 0;
    }

    GError *error = NULL;
    GDBusConnection *bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &error);
    if (!bus)
    {
        g_clear_error(&error);
        return 0;
    }

    char *uri = g_filename_to_uri(path, NULL, NULL);
    if (!uri)
    {
        g_object_unref(bus);
        return 0;
    }

    const char *uris[] = {uri, NULL};
    GVariant *reply = g_dbus_connection_call_sync(
        bus, "org.freedesktop.FileManager1", "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1",
        "ShowItems", g_variant_new("(^ass)", uris, ""), NULL, G_DBUS_CALL_FLAGS_NONE, 30000, NULL, &error);

    int ok = 1;
    if (reply)
    {
        g_variant_unref(reply);
    }
    else if (error && error->domain == G_DBUS_ERROR &&
             (error->code == G_DBUS_ERROR_SERVICE_UNKNOWN || error->code == G_DBUS_ERROR_NAME_HAS_NO_OWNER ||
              error->code == G_DBUS_ERROR_UNKNOWN_METHOD || error->code == G_DBUS_ERROR_UNKNOWN_OBJECT ||
              error->code == G_DBUS_ERROR_UNKNOWN_INTERFACE || error->code == G_DBUS_ERROR_SPAWN_SERVICE_NOT_FOUND))
    {
        ok = 0; /* no file manager on the bus: open the folder instead */
    }
    /* Anything else (a timeout, the file manager's own error): it's there and has the request; opening the
     * folder as well would show a second window. */

    g_clear_error(&error);
    g_free(uri);
    g_object_unref(bus);
    return ok;
}

/* ── print dialog (GtkPrintUnixDialog: the desktop's printer list and printer options) ── */

typedef struct
{
    int token;
} PrintCall;

static void add_line(GString *out, const char *key, const char *value)
{
    g_string_append_printf(out, "\n%s=%s", key, value ? value : "");
}

static void collect_cups_option(const char *key, const char *value, gpointer data)
{
    /* GTK keeps the queue's options as "cups-<CUPS option name>": the printer's own options
     * (InputSlot, MediaType, Resolution…) and the Job tab (job-priority, job-sheets,
     * job-hold-until, job-billing). All are passed on; .NET types them as IPP attributes. */
    if (g_str_has_prefix(key, "cups-") && key[5] && value && *value)
    {
        GString *out = data;
        g_string_append_printf(out, "\nopt:%s=%s", key + 5, value);
    }
}

static void on_print_response(GtkDialog *dialog, int response, gpointer data)
{
    PrintCall *call = data;
    GtkPrintUnixDialog *pd = GTK_PRINT_UNIX_DIALOG(dialog);
    GString *out = g_string_new(NULL);
    g_string_printf(out, "%d", call->token);

    GtkPrinter *printer = response == GTK_RESPONSE_OK ? gtk_print_unix_dialog_get_selected_printer(pd) : NULL;
    if (printer)
    {
        GtkPrintSettings *settings = gtk_print_unix_dialog_get_settings(pd); /* new reference */
        GtkPageSetup *setup = gtk_print_unix_dialog_get_page_setup(pd);

        add_line(out, "printer", gtk_printer_get_name(printer));
        g_string_append_printf(out, "\ncopies=%d", gtk_print_settings_get_n_copies(settings));
        g_string_append_printf(out, "\ncollate=%d", gtk_print_settings_get_collate(settings) ? 1 : 0);
        g_string_append_printf(out, "\nreverse=%d", gtk_print_settings_get_reverse(settings) ? 1 : 0);

        switch (gtk_print_settings_get_print_pages(settings))
        {
        case GTK_PRINT_PAGES_CURRENT:
            g_string_append_printf(out, "\npages=current:%d", gtk_print_unix_dialog_get_current_page(pd));
            break;
        case GTK_PRINT_PAGES_RANGES:
        {
            int n = 0;
            GtkPageRange *ranges = gtk_print_settings_get_page_ranges(settings, &n);
            g_string_append(out, "\npages=ranges:");
            for (int i = 0; i < n; i++)
            {
                g_string_append_printf(out, "%s%d-%d", i ? "," : "", ranges[i].start, ranges[i].end); /* 0-based */
            }

            g_free(ranges);
            break;
        }
        default:
            g_string_append(out, "\npages=all");
            break;
        }

        switch (gtk_print_settings_get_page_set(settings))
        {
        case GTK_PAGE_SET_EVEN:
            add_line(out, "page-set", "even");
            break;
        case GTK_PAGE_SET_ODD:
            add_line(out, "page-set", "odd");
            break;
        default:
            add_line(out, "page-set", "all");
            break;
        }

        switch (gtk_print_settings_get_duplex(settings))
        {
        case GTK_PRINT_DUPLEX_HORIZONTAL:
            add_line(out, "duplex", "horizontal");
            break;
        case GTK_PRINT_DUPLEX_VERTICAL:
            add_line(out, "duplex", "vertical");
            break;
        default:
            add_line(out, "duplex", "simplex");
            break;
        }

        g_string_append_printf(out, "\nnumber-up=%d", gtk_print_settings_get_number_up(settings));

        if (setup)
        {
            GtkPaperSize *paper = gtk_page_setup_get_paper_size(setup);
            if (paper)
            {
                g_string_append_printf(out, "\npaper=%s;%.3f;%.3f", gtk_paper_size_get_name(paper),
                                       gtk_paper_size_get_width(paper, GTK_UNIT_POINTS),
                                       gtk_paper_size_get_height(paper, GTK_UNIT_POINTS));
            }

            switch (gtk_page_setup_get_orientation(setup))
            {
            case GTK_PAGE_ORIENTATION_LANDSCAPE:
                add_line(out, "orientation", "landscape");
                break;
            case GTK_PAGE_ORIENTATION_REVERSE_LANDSCAPE:
                add_line(out, "orientation", "reverse-landscape");
                break;
            case GTK_PAGE_ORIENTATION_REVERSE_PORTRAIT:
                add_line(out, "orientation", "reverse-portrait");
                break;
            default:
                add_line(out, "orientation", "portrait");
                break;
            }
        }

        gtk_print_settings_foreach(settings, collect_cups_option, out);
        g_object_unref(settings);
    }

    gtk_window_destroy(GTK_WINDOW(dialog));
    S.event(CHVD_EVENT_PRINT_RESULT, out->str);
    g_string_free(out, TRUE);
    g_free(call);
}

/*
 * Shows the desktop's print dialog, modal to the main window, preset with what the person chose in
 * the app's Print card. pages: "" = all, "current", or 0-based "a-b,c-d". The answer arrives later
 * as CHVD_EVENT_PRINT_RESULT. Main thread.
 */
CHVD_EXPORT void chvd_print_dialog(int token, const char *title, int page_count, int current_page,
                                   const char *pages, int copies)
{
    GtkWidget *dialog = gtk_print_unix_dialog_new(title && *title ? title : "Print", S.window);
    GtkPrintUnixDialog *pd = GTK_PRINT_UNIX_DIALOG(dialog);
    gtk_window_set_modal(GTK_WINDOW(dialog), TRUE);
    gtk_window_set_destroy_with_parent(GTK_WINDOW(dialog), TRUE);
    gtk_print_unix_dialog_set_embed_page_setup(pd, TRUE);
    gtk_print_unix_dialog_set_manual_capabilities(
        pd, GTK_PRINT_CAPABILITY_PAGE_SET | GTK_PRINT_CAPABILITY_COPIES | GTK_PRINT_CAPABILITY_COLLATE |
                GTK_PRINT_CAPABILITY_REVERSE | GTK_PRINT_CAPABILITY_NUMBER_UP);
    if (page_count > 0 && current_page >= 0 && current_page < page_count)
    {
        gtk_print_unix_dialog_set_current_page(pd, current_page);
    }

    GtkPrintSettings *settings = gtk_print_settings_new();
    gtk_print_settings_set_n_copies(settings, copies > 0 ? copies : 1);
    gtk_print_settings_set_collate(settings, TRUE);
    if (pages && g_str_equal(pages, "current"))
    {
        gtk_print_settings_set_print_pages(settings, GTK_PRINT_PAGES_CURRENT);
    }
    else if (pages && *pages)
    {
        char **parts = g_strsplit(pages, ",", -1);
        guint n = g_strv_length(parts);
        GtkPageRange *ranges = g_new0(GtkPageRange, n);
        guint used = 0;
        for (guint i = 0; i < n; i++)
        {
            int a = 0, b = 0;
            if (sscanf(parts[i], "%d-%d", &a, &b) == 2 && a >= 0 && b >= a)
            {
                ranges[used].start = a;
                ranges[used].end = b;
                used++;
            }
        }

        if (used > 0)
        {
            gtk_print_settings_set_print_pages(settings, GTK_PRINT_PAGES_RANGES);
            gtk_print_settings_set_page_ranges(settings, ranges, (int)used);
        }

        g_free(ranges);
        g_strfreev(parts);
    }

    gtk_print_unix_dialog_set_settings(pd, settings);
    g_object_unref(settings);

    PrintCall *call = g_new0(PrintCall, 1);
    call->token = token;
    g_signal_connect(dialog, "response", G_CALLBACK(on_print_response), call);
    gtk_window_present(GTK_WINDOW(dialog));
}

/* ── script evaluation for the UI test driver (only the -p:UiTest=true build calls this) ── */

static void on_js_done(GObject *source, GAsyncResult *result, gpointer data)
{
    int token = GPOINTER_TO_INT(data);
    GError *error = NULL;
    JSCValue *value = webkit_web_view_call_async_javascript_function_finish(WEBKIT_WEB_VIEW(source), result, &error);
    char *text;
    if (value)
    {
        char *json = jsc_value_is_undefined(value) ? g_strdup("null") : jsc_value_to_json(value, 0);
        text = g_strdup_printf("%d\n%s", token, json ? json : "null");
        g_free(json);
        g_object_unref(value);
    }
    else
    {
        text = g_strdup_printf("%d\n!%s", token, error ? error->message : "error");
        g_clear_error(&error);
    }

    S.event(CHVD_EVENT_JS_RESULT, text);
    g_free(text);
}

/* Main thread. Runs script as a function body (use "return …" for a value; await is allowed). */
CHVD_EXPORT void chvd_eval_js(int token, const char *script)
{
    if (!S.view)
    {
        return;
    }

    webkit_web_view_call_async_javascript_function(S.view, script, -1, NULL, NULL, NULL, NULL, on_js_done,
                                                   GINT_TO_POINTER(token));
}
