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

    /* The last pointer press inside the view, for begin-move from the HTML title bar. */
    GdkDevice *press_device;
    int press_button;
    double press_x, press_y; /* view coordinates */
    guint32 press_time;

    gint wake_pending;
} S;

/* ── main loop ──────────────────────────────────────────────────────────── */

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

    /* Printing goes to CUPS queues only (the PDF itself, through Chuvadi.Print.Ipp). GTK's
     * "Print to File" and LPR pseudo-printers can't take that job, so the dialog lists CUPS
     * printers only, unless the person has chosen backends themselves. */
    if (!g_getenv("GTK_PRINT_BACKENDS"))
    {
        g_setenv("GTK_PRINT_BACKENDS", "cups", FALSE);
    }

    if (!gtk_init_check())
    {
        return 0; /* no display */
    }

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

static gboolean on_close_request(GtkWindow *window, gpointer data)
{
    (void)window;
    (void)data;
    S.event(CHVD_EVENT_CLOSE_REQUESTED, NULL);
    return FALSE; /* let it close; .NET quits the loop on the destroy below */
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

static void apply_window_css(void)
{
    char *css = g_strdup_printf(
        "window.chvd { background-color: %s; border-radius: 12px; }"
        "window.chvd.maximized, window.chvd.fullscreen, window.chvd.tiled,"
        "window.chvd.tiled-top, window.chvd.tiled-bottom, window.chvd.tiled-left, window.chvd.tiled-right,"
        "window.chvd.solid-csd { border-radius: 0; }",
        S_background);
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

/* Pinch-to-zoom (touchpad or touch screen) would zoom the whole page; the Reader zooms its own
 * canvas. Claim the gesture before WebKit sees it, as the Windows host turns off pinch zoom. */
static void on_zoom_begin(GtkGesture *gesture, GdkEventSequence *sequence, gpointer data)
{
    (void)data;
    gtk_gesture_set_state(gesture, GTK_EVENT_SEQUENCE_CLAIMED);
    (void)sequence;
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
    gtk_widget_add_controller(GTK_WIDGET(S.view), GTK_EVENT_CONTROLLER(zoom));

    gtk_window_set_child(S.window, GTK_WIDGET(S.view));
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

/* The desktop's window-button layout (GtkSettings gtk-decoration-layout, which GTK reads from
 * GNOME's button-layout setting or KDE's GTK settings), e.g. "appmenu:minimize,maximize,close".
 * Returns 1 when the close button is on the left, 0 when on the right. Main thread, after init. */
CHVD_EXPORT int chvd_buttons_on_left(void)
{
    char *layout = NULL;
    g_object_get(gtk_settings_get_default(), "gtk-decoration-layout", &layout, NULL);
    int left = 0;
    if (layout)
    {
        const char *colon = strchr(layout, ':');
        const char *close = strstr(layout, "close");
        left = close && colon && close < colon;
        g_free(layout);
    }

    return left;
}

/* "Show in folder": asks the desktop's file manager to open the folder with the file selected
 * (freedesktop org.freedesktop.FileManager1.ShowItems — Nautilus, Dolphin, Nemo, Thunar…).
 * Any thread (GDBus sync calls are thread-safe). Returns 1 when a file manager accepted it. */
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
        "ShowItems", g_variant_new("(^ass)", uris, ""), NULL, G_DBUS_CALL_FLAGS_NONE, 5000, NULL, &error);

    int ok = reply != NULL;
    if (reply)
    {
        g_variant_unref(reply);
    }

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
    /* Printer-specific options GTK read from the queue are stored as "cups-<Option>". PPD option
     * names start with an upper-case letter (InputSlot, MediaType, Resolution…); those are passed on
     * as job attributes, which CUPS applies to the queue's options. */
    if (g_str_has_prefix(key, "cups-") && g_ascii_isupper(key[5]) && value && *value)
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
