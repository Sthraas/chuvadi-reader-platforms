using System.Text.Json;
using System.Text.Json.Serialization;
using ChuvadiReader.Platform;
using global::Android.Content;
using global::Android.Database;
using global::Android.Provider;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// The Android half of Foundation's file model (PLATFORM-INTERFACE §3, option C): Core always works
/// on a local working copy; this records which content URI (file) or tree URI (folder) each working
/// path belongs to, so a write can be sent back and Recent files survive a restart.
///
/// Stored as JSON in the app's private files. URIs from the system picker keep a persisted grant
/// (<see cref="ContentResolver.TakePersistableUriPermission"/>); one-off grants (some "Open with"
/// senders) last only for this run and are recorded as such.
/// </summary>
public sealed class DocumentLinks
{
    private const int CopyBufferBytes = 81920;
    private readonly Dictionary<string, DateTime> _mirrored = new(StringComparer.Ordinal);

    private readonly string _file;
    private readonly string _workingRoot;
    private readonly object _gate = new();
    private Dictionary<string, DocumentLink> _links;

    public DocumentLinks(IAppPaths paths)
    {
        _file = Path.Combine(paths.AppDataFolder, "document-links.json");
        _workingRoot = paths.WorkingFolder;
        _links = Load(_file);
    }

    public DocumentLink? Find(string localPath)
    {
        lock (_gate)
        {
            return _links.TryGetValue(Path.GetFullPath(localPath), out var link) ? link : null;
        }
    }

    /// <summary>The link of this path, or of the nearest folder above it that came from a folder picker.</summary>
    public (string LocalPath, DocumentLink Link)? FindOwner(string localPath)
    {
        lock (_gate)
        {
            for (var path = Path.GetFullPath(localPath); !string.IsNullOrEmpty(path); path = Path.GetDirectoryName(path))
            {
                if (_links.TryGetValue(path, out var link) && (link.IsTree || path == Path.GetFullPath(localPath)))
                {
                    return (path, link);
                }
            }

            return null;
        }
    }

    /// <summary>
    /// Copies the documents in a picked folder (and its subfolders) into its working folder, so what reads
    /// the folder — the Library, the watched folder — sees what it holds. Only the given extensions; a
    /// document that can't be read is skipped.
    /// </summary>
    public void MirrorTree(ContentResolver resolver, AUri tree, string folder, IReadOnlyCollection<string> extensions, CancellationToken ct)
    {
        var pending = new Stack<(string DocumentId, string Local)>();
        pending.Push((DocumentsContract.GetTreeDocumentId(tree)!, folder));
        string[] columns = [DocumentsContract.Document.ColumnDocumentId, DocumentsContract.Document.ColumnDisplayName, DocumentsContract.Document.ColumnMimeType];
        while (pending.Count > 0)
        {
            ct.ThrowIfCancellationRequested();
            var (id, local) = pending.Pop();
            var children = DocumentsContract.BuildChildDocumentsUriUsingTree(tree, id);
            if (children is null)
            {
                continue;
            }

            try
            {
                using var cursor = resolver.Query(children, columns, null, null, null);
                while (cursor?.MoveToNext() == true)
                {
                    var childId = cursor.GetString(0);
                    var name = SafeFileName(cursor.GetString(1) ?? string.Empty);
                    if (string.IsNullOrEmpty(childId) || string.IsNullOrEmpty(name))
                    {
                        continue;
                    }

                    var target = Path.Combine(local, name);
                    if (cursor.GetString(2) == DocumentsContract.Document.MimeTypeDir)
                    {
                        Directory.CreateDirectory(target);
                        pending.Push((childId, target));
                    }
                    else if (extensions.Contains(Path.GetExtension(name), StringComparer.OrdinalIgnoreCase)
                             && DocumentsContract.BuildDocumentUriUsingTree(tree, childId) is { } uri)
                    {
                        try
                        {
                            using var input = resolver.OpenInputStream(uri);
                            if (input is null)
                            {
                                continue;
                            }

                            using (var output = File.Create(target))
                            {
                                input.CopyTo(output, CopyBufferBytes);
                            }

                            lock (_gate)
                            {
                                _mirrored[Path.GetFullPath(target)] = File.GetLastWriteTimeUtc(target);
                            }
                        }
                        catch (Exception ex) when (ex is IOException or Java.Lang.SecurityException or Java.IO.FileNotFoundException)
                        {
                            TryDelete(target);
                        }
                    }
                }
            }
            catch (Exception ex) when (ex is Java.Lang.SecurityException or Java.Lang.IllegalArgumentException or Java.Lang.UnsupportedOperationException)
            {
                // A provider that won't list this folder: leave it out.
            }
        }
    }

    /// <summary>True for a copy brought in from a picked folder and not changed since: sending the folder back
    /// leaves it alone instead of rewriting the person's file with the same bytes.</summary>
    public bool IsUnchangedMirror(string localPath)
    {
        var full = Path.GetFullPath(localPath);
        lock (_gate)
        {
            return _mirrored.TryGetValue(full, out var stamp) && File.GetLastWriteTimeUtc(full) == stamp;
        }
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (IOException)
        {
            // A partial copy left behind is never linked or listed as a document.
        }
    }

    /// <summary>True for a path inside the app's private working folder (working copies, never shown).</summary>
    public bool IsWorkingCopy(string localPath)
        => Path.GetFullPath(localPath).StartsWith(Path.GetFullPath(_workingRoot) + Path.DirectorySeparatorChar, StringComparison.Ordinal);

    public void Add(string localPath, AUri uri, bool isTree, bool persisted)
    {
        lock (_gate)
        {
            _links[Path.GetFullPath(localPath)] = new DocumentLink(uri.ToString()!, isTree, persisted);
            Save();
        }
    }

    /// <summary>A new, empty working folder for one document (keeps its real file name without clashes).</summary>
    public string NewWorkingFolder(string kind)
    {
        var folder = Path.Combine(_workingRoot, kind, Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        return folder;
    }

    /// <summary>
    /// Streams a content URI into a fresh working copy (never loaded whole into memory) and links it.
    /// Returns the local path, or null when the provider refused.
    /// </summary>
    /// <summary>
    /// Copies an incoming document into a working copy and links it to its source. A URI already linked
    /// to a working copy keeps that copy's path (AT-12, as Windows' shared router expects: the same
    /// document arrives under the same path, so an open tab is focused instead of duplicated, and
    /// Home's Recent keeps one entry). That copy is left exactly as it is while a tab holds it
    /// (<paramref name="isOpen"/>; it may carry unsaved edits); otherwise it is refreshed from the source.
    /// </summary>
    public string? Import(AUri uri, string? mimeHint, bool takePersistable, IReadOnlyCollection<string>? allowedExtensions,
                          Func<string, bool>? isOpen = null)
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

        if (allowedExtensions is not null && !allowedExtensions.Contains(Path.GetExtension(name).ToLowerInvariant()))
        {
            return null;
        }

        var persisted = takePersistable && TryPersist(resolver, uri);
        if (LinkedCopy(uri, name) is { } existing)
        {
            if (isOpen?.Invoke(existing) == true)
            {
                Add(existing, uri, isTree: false, persisted || Find(existing)?.Persisted == true);
                return existing;
            }

            // Not open: bring the copy up to date with the source, into a temporary file first so a
            // failed read leaves the previous copy whole.
            var fresh = existing + ".incoming";
            if (!CopyFrom(resolver, uri, fresh))
            {
                return null;
            }

            File.Move(fresh, existing, overwrite: true);
            Add(existing, uri, isTree: false, persisted || Find(existing)?.Persisted == true);
            return existing;
        }

        var target = Path.Combine(NewWorkingFolder("open"), name);
        if (!CopyFrom(resolver, uri, target))
        {
            TryDeleteFolder(Path.GetDirectoryName(target)!);
            return null;
        }

        Add(target, uri, isTree: false, persisted);
        return target;
    }

    /// <summary>The working copy already linked to this URI (a file, not a folder), if it still exists under the same name.</summary>
    private string? LinkedCopy(AUri uri, string name)
    {
        var key = uri.ToString();
        lock (_gate)
        {
            return _links.Where(l => !l.Value.IsTree && l.Value.Uri == key && Path.GetFileName(l.Key) == name && File.Exists(l.Key))
                         .Select(l => l.Key)
                         .FirstOrDefault();
        }
    }

    private static bool CopyFrom(ContentResolver resolver, AUri uri, string target)
    {
        try
        {
            using var input = resolver.OpenInputStream(uri);
            if (input is null)
            {
                return false;
            }

            using var output = File.Create(target);
            input.CopyTo(output, CopyBufferBytes);
            return true;
        }
        catch (Exception ex) when (ex is IOException or Java.Lang.SecurityException or Java.IO.FileNotFoundException)
        {
            try
            {
                File.Delete(target);
            }
            catch (IOException)
            {
                // Best effort: a stray partial copy is never linked, so nothing opens it.
            }

            return false;
        }
    }

    public static string QueryDisplayName(ContentResolver resolver, AUri uri)
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

    public static string SafeFileName(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new string(name.Select(c => invalid.Contains(c) || c == '/' ? '_' : c).ToArray()).Trim();
        return cleaned.Length == 0 || cleaned is "." or ".." ? "document" : cleaned;
    }

    public static bool TryPersist(ContentResolver resolver, AUri uri)
    {
        try
        {
            resolver.TakePersistableUriPermission(uri, ActivityFlags.GrantReadUriPermission | ActivityFlags.GrantWriteUriPermission);
            return true;
        }
        catch (Java.Lang.SecurityException)
        {
            try
            {
                resolver.TakePersistableUriPermission(uri, ActivityFlags.GrantReadUriPermission);
                return true;
            }
            catch (Java.Lang.SecurityException)
            {
                return false; // a one-off grant: valid for this run only
            }
        }
    }

    private static void TryDeleteFolder(string folder)
    {
        try
        {
            Directory.Delete(folder, recursive: true);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private void Save()
    {
        var temp = _file + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(_links, LinksJson.Default.DictionaryStringDocumentLink));
        File.Move(temp, _file, overwrite: true);
    }

    private static Dictionary<string, DocumentLink> Load(string file)
    {
        try
        {
            if (File.Exists(file))
            {
                var links = JsonSerializer.Deserialize(File.ReadAllText(file), LinksJson.Default.DictionaryStringDocumentLink) ?? new();

                // Working copies in the cache may have been reclaimed by the system; one-off grants
                // expired with the previous run.
                return links
                    .Where(kv => kv.Value.Persisted && (kv.Value.IsTree ? Directory.Exists(kv.Key) : File.Exists(kv.Key)))
                    .ToDictionary(kv => kv.Key, kv => kv.Value);
            }
        }
        catch (Exception ex) when (ex is JsonException or IOException)
        {
            // A damaged links file only costs write-back for older working copies.
        }

        return new();
    }
}

/// <summary>Where a working copy really belongs.</summary>
public sealed record DocumentLink(string Uri, bool IsTree, bool Persisted);

[JsonSerializable(typeof(Dictionary<string, DocumentLink>))]
internal sealed partial class LinksJson : JsonSerializerContext
{
}
