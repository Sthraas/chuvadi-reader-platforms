using ChuvadiReader.Core.Reader;
using global::Android.Content;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Documents arriving from other apps — "Open with" (ACTION_VIEW) and "Share" (ACTION_SEND).
/// Each is imported as a working copy (<see cref="DocumentLinks.Import"/>) and then routed exactly
/// like a desktop drop (PLATFORM-INTERFACE §4): onto the Bench when it is open, otherwise opened
/// in the Reader under the document's real name. The original is never modified here.
/// </summary>
public sealed class DocumentImport
{
    private readonly DocumentLinks _links;
    private readonly OpenDocumentService _open;
    private readonly BenchDropService _bench;
    private readonly ShellService _shell;

    public DocumentImport(DocumentLinks links, OpenDocumentService open, BenchDropService bench, ShellService shell)
    {
        _links = links;
        _open = open;
        _bench = bench;
        _shell = shell;
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

        // Copy off the UI thread; the grant stays valid while the activity holds the intent.
        // A file that can't be opened is said so on screen (and in the log): never a silent no-op.
        _ = Task.Run(() =>
        {
            string? local;
            try
            {
                local = _links.Import(uri, mime, persistable, DocumentTypes.Extensions);
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
                if (_bench.IsBenchActive)
                {
                    _bench.Drop(new[] { local });
                }
                else
                {
                    _open.Request(local, Path.GetFileName(local));
                }
            });
        });
    }

    private void Tell(string text) => MainThread.BeginInvokeOnMainThread(() => _shell.Notify(text, isError: true));
}
