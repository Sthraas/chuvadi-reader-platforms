using ChuvadiReader.Core.Reader;
using global::Android.Content;
using global::Android.Database;
using global::Android.Provider;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Brings documents from other apps into the Reader.
///
/// Android never gives a file path: "Open with", "Share" and the system picker all hand over a
/// <c>content://</c> URI with temporary read access. The Reader's Core opens documents by path,
/// so each incoming document is streamed (never loaded whole into memory) into a private
/// working copy under the app's cache folder, and that copy is opened under the document's own
/// display name. The original is never modified.
///
/// Writing changes back to the original is part of the platform-interface decision
/// (docs/android/DECISIONS.md, A-02) and is not done here.
/// </summary>
public sealed class DocumentImport
{
    private const int CopyBufferBytes = 81920;

    private readonly OpenDocumentService _open;
    private readonly BenchDropService _bench;

    public DocumentImport(OpenDocumentService open, BenchDropService bench)
    {
        _open = open;
        _bench = bench;
    }

    /// <summary>Root of the per-document working copies.</summary>
    public static string IncomingRoot => Path.Combine(FileSystem.CacheDirectory, "incoming");

    /// <summary>Handles an Open-with (ACTION_VIEW) or Share (ACTION_SEND) intent.</summary>
    public void HandleIntent(Intent intent)
    {
        AUri? uri = intent.Action switch
        {
            Intent.ActionView => intent.Data,
            Intent.ActionSend => GetStreamExtra(intent),
            _ => null,
        };

        if (uri is null)
        {
            return;
        }

        // Copy off the UI thread; the grant stays valid while the activity holds the intent.
        _ = Task.Run(() =>
        {
            var local = Materialize(uri, intent.Type);
            if (local is null)
            {
                return;
            }

            MainThread.BeginInvokeOnMainThread(() =>
            {
                // Same routing as a desktop drop: the Bench takes it as a source when it is open.
                if (_bench.IsBenchActive)
                {
                    _bench.Drop(new[] { local.Value.Path });
                }
                else
                {
                    _open.Request(local.Value.Path, local.Value.DisplayName);
                }
            });
        });
    }

    /// <summary>
    /// Streams a content URI into a private working copy and returns its path and the name to
    /// show. Null if the provider refused or the type is not one the Reader opens.
    /// </summary>
    public static (string Path, string DisplayName)? Materialize(AUri uri, string? mimeHint)
    {
        var resolver = global::Android.App.Application.Context.ContentResolver;
        if (resolver is null)
        {
            return null;
        }

        var name = SafeFileName(QueryDisplayName(resolver, uri));
        var mime = resolver.GetType(uri) ?? mimeHint;
        if (string.IsNullOrEmpty(Path.GetExtension(name)) && DocumentTypes.ExtensionFor(mime) is { } ext)
        {
            name += ext;
        }

        if (!DocumentTypes.Extensions.Contains(Path.GetExtension(name).ToLowerInvariant()))
        {
            return null;
        }

        // One folder per document keeps the original file name without clashes.
        var folder = Path.Combine(IncomingRoot, Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        var target = Path.Combine(folder, name);

        try
        {
            using var input = resolver.OpenInputStream(uri);
            if (input is null)
            {
                return null;
            }

            using var output = File.Create(target);
            input.CopyTo(output, CopyBufferBytes);
        }
        catch (Exception ex) when (ex is IOException or Java.Lang.SecurityException or Java.IO.FileNotFoundException)
        {
            TryDelete(folder);
            return null;
        }

        return (target, name);
    }

    /// <summary>Removes all working copies. Not called yet: Recent files point at them until A-02 decides
    /// how Android remembers documents (persisted URI grants vs working copies).</summary>
    public static void ClearPreviousRun()
    {
        TryDelete(IncomingRoot);
    }

    private static AUri? GetStreamExtra(Intent intent)
        => OperatingSystem.IsAndroidVersionAtLeast(33)
            ? intent.GetParcelableExtra(Intent.ExtraStream, Java.Lang.Class.FromType(typeof(AUri))) as AUri
            : null;

    private static string QueryDisplayName(ContentResolver resolver, AUri uri)
    {
        try
        {
            using ICursor? cursor = resolver.Query(uri, new[] { IOpenableColumns.DisplayName }, null, null, null);
            if (cursor is not null && cursor.MoveToFirst())
            {
                var index = cursor.GetColumnIndex(IOpenableColumns.DisplayName);
                if (index >= 0 && cursor.GetString(index) is { Length: > 0 } value)
                {
                    return value;
                }
            }
        }
        catch (Java.Lang.Exception)
        {
            // Some providers don't answer the query; fall back to the URI's last segment.
        }

        return uri.LastPathSegment ?? "document";
    }

    private static string SafeFileName(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new string(name.Select(c => invalid.Contains(c) || c == '/' ? '_' : c).ToArray()).Trim();
        return cleaned.Length == 0 ? "document" : cleaned;
    }

    private static void TryDelete(string folder)
    {
        try
        {
            if (Directory.Exists(folder))
            {
                Directory.Delete(folder, recursive: true);
            }
        }
        catch (IOException)
        {
            // Best effort; the cache folder is the system's to reclaim anyway.
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
