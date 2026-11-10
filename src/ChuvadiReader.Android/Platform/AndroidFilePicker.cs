using ChuvadiReader.Core.Reader;
using global::Android.App;
using global::Android.Content;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Pickers through Android's system document picker (Storage Access Framework), returning local
/// working paths as Foundation's file model requires (PLATFORM-INTERFACE §3):
/// <list type="bullet">
/// <item>Open: the chosen document is imported as a working copy and linked to its URI, with a
/// persisted grant so Recent files reopen and Save can write back.</item>
/// <item>Save as (PDF, image, session): the person chooses the destination first; Core writes into a
/// working path linked to that URI, and the Ui's <c>WriteBack.DeliverOrThrowAsync</c> sends it there
/// (<see cref="AndroidFileWriteBack"/>).</item>
/// <item>Folder: the chosen folder becomes a working folder linked to it. The documents already in it are
/// copied in first (subfolders too), so a folder picked for the Library or as the watched folder shows
/// what it holds; whatever Chuvadi writes into it is sent back the same way.</item>
/// </list>
/// AT-18: the save and folder pickers had been left switched off since before the Ui delivered its
/// saves; nothing that saves to a new file worked. They are on.
/// </summary>
public sealed class AndroidFilePicker : IFilePicker
{
    private readonly DocumentLinks _links;

    public AndroidFilePicker(DocumentLinks links) => _links = links;

    public async Task<string?> PickDocumentAsync(CancellationToken ct = default)
        => (await OpenAsync(DocumentTypes.AllSupported, multiple: false, DocumentTypes.Extensions).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default)
        => OpenAsync(DocumentTypes.PdfOnly, multiple: true, new[] { ".pdf" });

    public async Task<string?> PickOpenSessionAsync(CancellationToken ct = default)
        => (await OpenAsync(new[] { "application/json", "application/octet-stream" }, multiple: false, null).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default)
        => OpenAsync(DocumentTypes.Images, multiple: true, null);

    public async Task<string?> PickCertificateAsync(CancellationToken ct = default)
        => (await OpenAsync(DocumentTypes.Certificates, multiple: false, new[] { ".pfx", ".p12" }).ConfigureAwait(false)).FirstOrDefault();

    public Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default)
        => CreateAsync(suggestedName, DocumentTypes.Pdf, ".pdf");

    public Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default)
        => CreateAsync(suggestedName, "application/json", ".json");

    public Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default)
        => CreateAsync(suggestedName, "image/png", ".png");

    public async Task<string?> PickFolderAsync(CancellationToken ct = default)
    {
        var intent = new Intent(Intent.ActionOpenDocumentTree);
        intent.AddFlags(ActivityFlags.GrantReadUriPermission | ActivityFlags.GrantWriteUriPermission | ActivityFlags.GrantPersistableUriPermission);
        var (code, data) = await ActivityResults.StartAsync(intent).ConfigureAwait(false);
        if (code != Result.Ok || data?.Data is not { } tree || Resolver is not { } resolver)
        {
            return null;
        }

        var persisted = DocumentLinks.TryPersist(resolver, tree);
        var folder = _links.NewWorkingFolder("folder");
        _links.Add(folder, tree, isTree: true, persisted);
        await Task.Run(() => _links.MirrorTree(resolver, tree, folder, DocumentTypes.Extensions, ct), ct).ConfigureAwait(false);
        return folder;
    }

    private static ContentResolver? Resolver => global::Android.App.Application.Context.ContentResolver;

    private async Task<IReadOnlyList<string>> OpenAsync(string[] mimeTypes, bool multiple, IReadOnlyCollection<string>? extensions)
    {
        var intent = new Intent(Intent.ActionOpenDocument);
        intent.AddCategory(Intent.CategoryOpenable);
        intent.SetType(mimeTypes.Length == 1 ? mimeTypes[0] : "*/*");
        intent.PutExtra(Intent.ExtraMimeTypes, mimeTypes);
        intent.PutExtra(Intent.ExtraAllowMultiple, multiple);
        intent.AddFlags(ActivityFlags.GrantReadUriPermission | ActivityFlags.GrantWriteUriPermission | ActivityFlags.GrantPersistableUriPermission);

        var (code, data) = await ActivityResults.StartAsync(intent).ConfigureAwait(false);
        if (code != Result.Ok || data is null)
        {
            return Array.Empty<string>();
        }

        var uris = new List<AUri>();
        if (data.ClipData is { } clip)
        {
            for (var i = 0; i < clip.ItemCount; i++)
            {
                if (clip.GetItemAt(i)?.Uri is { } u)
                {
                    uris.Add(u);
                }
            }
        }
        else if (data.Data is { } single)
        {
            uris.Add(single);
        }

        // Stream the copies off the UI thread (a large PDF from a cloud provider can take a while).
        return await Task.Run(() => uris
            .Select(u => _links.Import(u, null, takePersistable: true, extensions))
            .Where(p => p is not null)
            .Select(p => p!)
            .ToList()).ConfigureAwait(false);
    }

    private async Task<string?> CreateAsync(string suggestedName, string mime, string extension)
    {
        var name = DocumentLinks.SafeFileName(string.IsNullOrWhiteSpace(suggestedName) ? "document" + extension : suggestedName);
        if (!name.EndsWith(extension, StringComparison.OrdinalIgnoreCase))
        {
            name += extension;
        }

        var intent = new Intent(Intent.ActionCreateDocument);
        intent.AddCategory(Intent.CategoryOpenable);
        intent.SetType(mime);
        intent.PutExtra(Intent.ExtraTitle, name);
        intent.AddFlags(ActivityFlags.GrantReadUriPermission | ActivityFlags.GrantWriteUriPermission | ActivityFlags.GrantPersistableUriPermission);

        var (code, data) = await ActivityResults.StartAsync(intent).ConfigureAwait(false);
        if (code != Result.Ok || data?.Data is not { } uri || Resolver is not { } resolver)
        {
            return null;
        }

        // The person may have renamed it in the picker; the working copy carries the final name.
        var finalName = DocumentLinks.SafeFileName(DocumentLinks.QueryDisplayName(resolver, uri));
        var persisted = DocumentLinks.TryPersist(resolver, uri);
        var path = Path.Combine(_links.NewWorkingFolder("save"), finalName);
        _links.Add(path, uri, isTree: false, persisted);
        return path;
    }
}
