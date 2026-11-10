using ChuvadiReader.Core.Reader;
using ChuvadiReader.Hosting;
using global::Android.Content;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Documents arriving from other apps — "Open with" (ACTION_VIEW) and "Share" (ACTION_SEND).
/// Each is imported as a working copy (<see cref="DocumentLinks.Import"/>) and handed to the kit's
/// <see cref="IncomingFiles"/> router (HANDOFF §2), the one route every host uses: onto the Bench
/// shelf when it is open, otherwise a new Reader tab, after the first render. The original is never
/// modified here.
/// </summary>
public sealed class DocumentImport
{
    private readonly DocumentLinks _links;
    private readonly IncomingFiles _incoming;
    private readonly ShellService _shell;
    private readonly TabsService _tabs;

    public DocumentImport(DocumentLinks links, IncomingFiles incoming, ShellService shell, TabsService tabs)
    {
        _links = links;
        _incoming = incoming;
        _shell = shell;
        _tabs = tabs;
    }

    public void HandleIntent(Intent intent)
    {
        AUri? uri = intent.Action switch
        {
            Intent.ActionView => intent.Data,
            Intent.ActionSend => intent.GetParcelableExtra(Intent.ExtraStream, Java.Lang.Class.FromType(typeof(AUri))) as AUri,
            _ => null,
        };

        if (uri is null)
        {
            return;
        }

        // Write access is kept only when the sender granted it persistably; otherwise read-only for this run.
        var persistable = (intent.Flags & ActivityFlags.GrantPersistableUriPermission) != 0;
        var mime = intent.Type;

        // The paths open in tabs now (read here, on the main thread): a document already open keeps its
        // working copy untouched, so the router focuses its tab (AT-12).
        var open = _tabs.Tabs.Select(t => Path.GetFullPath(t.Path)).ToHashSet(StringComparer.OrdinalIgnoreCase);

        // Copy off the UI thread; the grant stays valid while the activity holds the intent.
        // A file that can't be opened is said so on screen (and in the log): never a silent no-op.
        _ = Task.Run(() =>
        {
            string? local;
            try
            {
                local = _links.Import(uri, mime, persistable, DocumentTypes.Extensions, open.Contains);
            }
            catch (Exception ex) when (ex is Java.Lang.SecurityException or Java.Lang.IllegalArgumentException
                                           or Java.Lang.UnsupportedOperationException or IOException or UnauthorizedAccessException)
            {
                global::Android.Util.Log.Warn("Chuvadi", $"Open from another app failed for {uri}: {ex}");
                Tell("Chuvadi couldn't read that file: the app that sent it didn't give access.");
                return;
            }

            if (local is null)
            {
                global::Android.Util.Log.Warn("Chuvadi", $"Open from another app: nothing imported from {uri} (type {mime})");
                Tell("Chuvadi couldn't open that file.");
                return;
            }

            global::Android.Util.Log.Info("Chuvadi", $"Opened from another app: {Path.GetFileName(local)}");
            MainThread.BeginInvokeOnMainThread(() =>
            {
                if (_incoming.Receive([local]) == 0)
                {
                    global::Android.Util.Log.Warn("Chuvadi", $"Open from another app: not an openable type: {Path.GetFileName(local)}");
                    Tell("Chuvadi couldn't open that file.");
                }
            });
        });
    }

    private void Tell(string text) => MainThread.BeginInvokeOnMainThread(() => _shell.Notify(text, isError: true));
}
