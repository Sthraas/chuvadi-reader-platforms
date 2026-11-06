using ChuvadiReader.Platform;
using global::Android.Provider;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Sends a file Chuvadi has written at a working path back to the document or folder the person
/// chose (Foundation's IFileWriteBack). Files: the URI is truncated and rewritten ("wt"). Folders
/// (from the tree picker): every file in the working folder is created in, or replaces its namesake
/// in, the chosen folder.
///
/// NOTE: the Ui calls <see cref="CommitAsync"/> only once Foundation's Ui hooks are approved
/// (EDITS-FOR-APPROVAL). Until then nothing calls it — see docs/android/DECISIONS.md, A-02.
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
        var link = _links.Find(localPath);
        if (link is null)
        {
            // Not a picked or opened document (e.g. an internal scratch file): nothing to send.
            return WriteBackResult.NotNeeded;
        }

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

            var parent = DocumentsContract.BuildDocumentUriUsingTree(uri, DocumentsContract.GetTreeDocumentId(uri))
                ?? throw new IOException("The chosen folder is no longer available.");
            foreach (var file in Directory.EnumerateFiles(localPath))
            {
                ct.ThrowIfCancellationRequested();
                var name = Path.GetFileName(file);
                var target = DocumentsContract.CreateDocument(resolver, parent, MimeFor(name), name)
                    ?? throw new IOException($"Couldn't create {name} in the chosen folder.");
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

    private static string MimeFor(string name) => Path.GetExtension(name).ToLowerInvariant() switch
    {
        ".pdf" => DocumentTypes.Pdf,
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".json" => "application/json",
        ".txt" => "text/plain",
        _ => "application/octet-stream",
    };
}
