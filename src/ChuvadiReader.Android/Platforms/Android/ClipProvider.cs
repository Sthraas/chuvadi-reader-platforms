using global::Android.Content;
using global::Android.Database;
using global::Android.OS;
using global::Android.Provider;
using global::Android.Runtime;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// A minimal read-only content provider that serves clipboard images from one private folder.
/// Own code instead of a library FileProvider (programme rule 3). Declared in AndroidManifest.xml
/// as <c>chuvadi.reader.ClipProvider</c>, not exported; other apps can read a clip only through
/// the per-URI grant the clipboard gives them.
/// </summary>
[Register("chuvadi/reader/ClipProvider")]
public sealed class ClipProvider : ContentProvider
{
    public static string ClipFolder => Path.Combine(FileSystem.CacheDirectory, "clip");

    public override bool OnCreate() => true;

    public override string? GetType(AUri uri) => "image/png";

    public override ParcelFileDescriptor? OpenFile(AUri uri, string mode)
    {
        if (mode != "r")
        {
            throw new Java.Lang.SecurityException("Clip images are read-only.");
        }

        var file = Resolve(uri) ?? throw new Java.IO.FileNotFoundException(uri.ToString());
        return ParcelFileDescriptor.Open(new Java.IO.File(file), ParcelFileMode.ReadOnly);
    }

    public override ICursor? Query(AUri uri, string[]? projection, string? selection, string[]? selectionArgs, string? sortOrder)
    {
        var file = Resolve(uri);
        if (file is null)
        {
            return null;
        }

        var cursor = new MatrixCursor(new[] { IOpenableColumns.DisplayName, IOpenableColumns.Size });
        cursor.AddRow(new Java.Lang.Object[] { new Java.Lang.String(Path.GetFileName(file)), Java.Lang.Long.ValueOf(new FileInfo(file).Length) });
        return cursor;
    }

    public override AUri? Insert(AUri uri, ContentValues? values) => throw new Java.Lang.UnsupportedOperationException();

    public override int Delete(AUri uri, string? selection, string[]? selectionArgs) => throw new Java.Lang.UnsupportedOperationException();

    public override int Update(AUri uri, ContentValues? values, string? selection, string[]? selectionArgs) => throw new Java.Lang.UnsupportedOperationException();

    /// <summary>Only a bare file name inside the clip folder is accepted — no paths, no traversal.</summary>
    private static string? Resolve(AUri uri)
    {
        var name = uri.LastPathSegment;
        if (string.IsNullOrEmpty(name) || name != Path.GetFileName(name) || name.StartsWith('.'))
        {
            return null;
        }

        var file = Path.Combine(ClipFolder, name);
        return File.Exists(file) ? file : null;
    }
}
