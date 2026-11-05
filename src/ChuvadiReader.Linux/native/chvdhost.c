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

static gboolean deliver_message(gpointer data)
{
    char *script = data;
    if (S.view)
    {
        webkit_web_view_evaluate_javascript(S.view, script, -1, NULL, NULL, NULL, NULL, NULL);
    }

    g_free(script);
    return G_SOURCE_REMOVE;
}

/* Any thread. json_literal must already be a JavaScript string literal (quoted and escaped). */
CHVD_EXPORT void chvd_post_message(const char *json_literal)
{
    char *script = g_strconcat("__chvdReceive(", json_literal, ");", NULL);
    g_main_context_invoke(NULL, deliver_message, script);
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

/* Background as "#RRGGBB" — painted by both the window and the web view until the page paints. */
static void apply_background(const char *hex)
{
    GdkRGBA rgba;
    if (!hex || !gdk_rgba_parse(&rgba, hex))
    {
        return;
    }

    if (S.view)
    {
        webkit_web_view_set_background_color(S.view, &rgba);
    }

    char *css = g_strdup_printf("window.chvd { background-color: %s; }", hex);
    gtk_css_provider_load_from_string(S.css, css);
    g_free(css);
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

    gtk_window_set_child(S.window, GTK_WIDGET(S.view));
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
