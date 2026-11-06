using global::Android.Content;
using global::Android.Database;
using global::Android.OS;
using global::Android.Provider;
using global::Android.Runtime;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// A minimal read-only content provider for files Chuvadi hands to other apps: the clipboard image
/// and the file being shared. Own code instead of a library FileProvider (programme rule 3).
/// Declared in AndroidManifest.xml as <c>chuvadi.reader.SharedFileProvider</c>, not exported; other
/// apps read a file only through the per-URI grant the clipboard or share intent gives them.
/// URIs look like content://&lt;app id&gt;.files/&lt;area&gt;/&lt;file name&gt;; nothing outside the
/// two areas can be named.
/// </summary>
[Register("chuvadi/reader/SharedFileProvider")]
public sealed class SharedFileProvider : ContentProvider
{
    public const string ClipArea = "clip";
    public const string ShareArea = "share";

    private static string Root => Path.Combine(FileSystem.CacheDirectory, "outgoing");

    /// <summary>Replaces the area's contents with one new file and returns its URI.</summary>
    public static AUri Publish(string area, string fileName, Action<string> write)
    {
        var folder = Path.Combine(Root, area);
        Directory.CreateDirectory(folder);
        foreach (var old in Directory.EnumerateFiles(folder))
        {
            File.Delete(old);
        }

        var name = DocumentLinks.SafeFileName(fileName);
        write(Path.Combine(folder, name));

        var authority = global::Android.App.Application.Context.PackageName + ".files";
        return new AUri.Builder().Scheme("content")!.Authority(authority)!.AppendPath(area)!.AppendPath(name)!.Build()!;
    }

    public static string MimeFor(string name) => Path.GetExtension(name).ToLowerInvariant() switch
    {
        ".pdf" => DocumentTypes.Pdf,
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".docx" => DocumentTypes.Docx,
        ".xlsx" => DocumentTypes.Xlsx,
        _ => "application/octet-stream",
    };

    public override bool OnCreate() => true;

    public override string? GetType(AUri uri) => Resolve(uri) is { } file ? MimeFor(file) : null;

    public override ParcelFileDescriptor? OpenFile(AUri uri, string mode)
    {
        if (mode != "r")
        {
            throw new Java.Lang.SecurityException("Shared files are read-only.");
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

    /// <summary>Exactly two path segments: a known area and a bare file name. No traversal.</summary>
    private static string? Resolve(AUri uri)
    {
        var segments = uri.PathSegments;
        if (segments is null || segments.Count != 2)
        {
            return null;
        }

        var area = segments[0];
        var name = segments[1];
        if (area is not (ClipArea or ShareArea) || string.IsNullOrEmpty(name) || name != Path.GetFileName(name) || name.StartsWith('.'))
        {
            return null;
        }

        var file = Path.Combine(Root, area, name);
        return File.Exists(file) ? file : null;
    }
}
