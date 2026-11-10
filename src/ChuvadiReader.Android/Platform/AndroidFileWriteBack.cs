using ChuvadiReader.Platform;
using global::Android.Provider;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Sends a file Chuvadi has written at a working path back to the document or folder the person
/// chose (Foundation's IFileWriteBack; the Ui calls it through <c>WriteBack.DeliverOrThrowAsync</c> after
/// every save). Three cases:
/// <list type="bullet">
/// <item>a file linked to a document (opened, or chosen with Save as): the URI is truncated and rewritten ("wt");</item>
/// <item>a folder from the folder picker (Export pages, Scatter, Split to a folder, Press): every file under it,
/// subfolders included, is created in the chosen folder or replaces its namesake there;</item>
/// <item>a file inside such a folder (a save into the default save folder): that file alone, at its place in it.</item>
/// </list>
/// </summary>
public sealed class AndroidFileWriteBack : IFileWriteBack
{
    private const int CopyBufferBytes = 81920;

    private readonly DocumentLinks _links;

    public AndroidFileWriteBack(DocumentLinks links) => _links = links;

    public bool IsNeeded => true;

    public Task<WriteBackResult> CommitAsync(string localPath, CancellationToken ct = default)
        => Task.Run(() => Commit(localPath, ct), ct);

    private WriteBackResult Commit(string localPath, CancellationToken ct)
    {
        var owner = _links.FindOwner(localPath);
        if (owner is null)
        {
            // Not a picked or opened document, nor inside a picked folder (an internal scratch file): nothing to send.
            return WriteBackResult.NotNeeded;
        }

        var (linkedPath, link) = owner.Value;

        var resolver = global::Android.App.Application.Context.ContentResolver;
        var uri = AUri.Parse(link.Uri);
        if (resolver is null || uri is null)
        {
            return new WriteBackResult(WriteBackOutcome.Failed, "Couldn't reach Android's storage.");
        }

        try
        {
            if (!link.IsTree)
            {
                WriteFile(resolver, uri, localPath, ct);
                return new WriteBackResult(WriteBackOutcome.Done);
            }

            var root = DocumentsContract.BuildDocumentUriUsingTree(uri, DocumentsContract.GetTreeDocumentId(uri))
                ?? throw new IOException("The chosen folder is no longer available.");
            var full = Path.GetFullPath(localPath);
            var files = Directory.Exists(full)
                ? Directory.EnumerateFiles(full, "*", SearchOption.AllDirectories)
                : File.Exists(full) ? new[] { full } : Array.Empty<string>();
            foreach (var file in files.Where(f => !_links.IsUnchangedMirror(f)))
            {
                ct.ThrowIfCancellationRequested();
                var parts = Path.GetRelativePath(linkedPath, file).Split(Path.DirectorySeparatorChar);
                var parent = root;
                foreach (var folder in parts[..^1])
                {
                    parent = Child(resolver, uri, parent, folder, DocumentsContract.Document.MimeTypeDir)
                        ?? throw new IOException($"Couldn't make the folder {folder} in the chosen folder.");
                }

                var target = Child(resolver, uri, parent, parts[^1], MimeFor(parts[^1]))
                    ?? throw new IOException($"Couldn't create {parts[^1]} in the chosen folder.");
                WriteFile(resolver, target, file, ct);
            }

            return new WriteBackResult(WriteBackOutcome.Done);
        }
        catch (OperationCanceledException)
        {
            return new WriteBackResult(WriteBackOutcome.Cancelled);
        }
        catch (Java.Lang.SecurityException)
        {
            return new WriteBackResult(WriteBackOutcome.Failed,
                "The app that shared this file allowed reading only. Use Save as to keep your changes.");
        }
        catch (Exception ex) when (ex is IOException or Java.IO.IOException or Java.Lang.IllegalArgumentException)
        {
            return new WriteBackResult(WriteBackOutcome.Failed, "Couldn't save to the original location: " + ex.Message);
        }
    }

    private static void WriteFile(global::Android.Content.ContentResolver resolver, AUri uri, string localPath, CancellationToken ct)
    {
        using var output = resolver.OpenOutputStream(uri, "wt") ?? throw new IOException("The destination refused the write.");
        using var input = File.OpenRead(localPath);
        var buffer = new byte[CopyBufferBytes];
        int read;
        while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
        {
            ct.ThrowIfCancellationRequested();
            output.Write(buffer, 0, read);
        }

        output.Flush();
    }

    /// <summary>The named child of a folder in a picked tree: the existing one (so a save replaces its namesake
    /// rather than making "name (1)"), or a new one.</summary>
    private static AUri? Child(global::Android.Content.ContentResolver resolver, AUri tree, AUri parent, string name, string mime)
    {
        var children = DocumentsContract.BuildChildDocumentsUriUsingTree(tree, DocumentsContract.GetDocumentId(parent));
        if (children is not null)
        {
            using var cursor = resolver.Query(children,
                [DocumentsContract.Document.ColumnDocumentId, DocumentsContract.Document.ColumnDisplayName, DocumentsContract.Document.ColumnMimeType],
                null, null, null);
            while (cursor?.MoveToNext() == true)
            {
                var isDir = cursor.GetString(2) == DocumentsContract.Document.MimeTypeDir;
                if (cursor.GetString(1) == name && isDir == (mime == DocumentsContract.Document.MimeTypeDir))
                {
                    return DocumentsContract.BuildDocumentUriUsingTree(tree, cursor.GetString(0));
                }
            }
        }

        return DocumentsContract.CreateDocument(resolver, parent, mime, name);
    }

    private static string MimeFor(string name) => Path.GetExtension(name).ToLowerInvariant() switch
    {
        ".pdf" => DocumentTypes.Pdf,
        ".docx" => "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx" => "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".json" => "application/json",
        ".txt" => "text/plain",
        _ => "application/octet-stream",
    };
}
