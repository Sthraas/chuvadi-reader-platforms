using ChuvadiReader.Platform;
using global::Android.Provider;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// AT-07: tabs, Home's cards and rows, the Library and watched folder are labelled with the
/// document's own name and where it came from — never the working copy's path in the app's
/// private cache, which TalkBack would read aloud and means nothing to the person.
///
/// A file from the device's own storage shows its folder there (<c>Download/report.pdf</c>, from the
/// document ID the storage provider gives); a file from any other app or cloud provider shows its
/// name (the provider's display name, which the working copy already carries); a file inside a
/// picked folder shows that folder's path and the file's place in it.
/// </summary>
public sealed class AndroidPathLabels : IPathLabels
{
    private const string DeviceStorage = "com.android.externalstorage.documents";

    private readonly DocumentLinks _links;

    public AndroidPathLabels(DocumentLinks links) => _links = links;

    public string Describe(string? path)
    {
        if (string.IsNullOrEmpty(path))
        {
            return string.Empty;
        }

        try
        {
            var owner = _links.FindOwner(path);
            if (owner is null)
            {
                return _links.IsWorkingCopy(path) ? Name(path) : path;
            }

            var (linked, link) = owner.Value;
            var uri = AUri.Parse(link.Uri);
            var origin = uri is null ? null : Origin(uri, link.IsTree);
            if (link.IsTree)
            {
                var inside = Path.GetRelativePath(linked, Path.GetFullPath(path)).Replace(Path.DirectorySeparatorChar, '/');
                var folder = origin ?? Name(linked);
                return inside == "." ? folder : $"{folder}/{inside}";
            }

            return origin ?? Name(path);
        }
        catch (Exception ex) when (ex is ArgumentException or Java.Lang.IllegalArgumentException or Java.Lang.UnsupportedOperationException)
        {
            return Name(path);
        }
    }

    // Device storage document IDs are "<volume>:<path>" (primary:Download/report.pdf); other providers'
    // IDs are opaque, so they get no location, only the name.
    private static string? Origin(AUri uri, bool isTree)
    {
        if (uri.Authority != DeviceStorage)
        {
            return null;
        }

        var id = isTree ? DocumentsContract.GetTreeDocumentId(uri) : DocumentsContract.GetDocumentId(uri);
        var colon = id?.IndexOf(':') ?? -1;
        var where = colon >= 0 ? id![(colon + 1)..].Trim('/') : null;
        return string.IsNullOrEmpty(where) ? null : where;
    }

    private static string Name(string path)
    {
        var name = Path.GetFileName(Path.TrimEndingDirectorySeparator(path));
        return string.IsNullOrEmpty(name) ? path : name;
    }
}
