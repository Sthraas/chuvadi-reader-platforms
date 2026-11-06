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

    public DocumentImport(DocumentLinks links, OpenDocumentService open, BenchDropService bench)
    {
        _links = links;
        _open = open;
        _bench = bench;
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
        _ = Task.Run(() =>
        {
            var local = _links.Import(uri, mime, persistable, DocumentTypes.Extensions);
            if (local is null)
            {
                return;
            }

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
}
