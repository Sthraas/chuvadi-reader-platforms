using Chuvadi.Zip;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// D-129 (O-3): a save that produces two or more files ("Split to folder", Scatter, export pages and the
/// like) reaches the browser as one .zip, so there is no multi-download prompt and Safari doesn't block
/// the second file. Written with Chuvadi.Zip, streaming from each file, so memory stays small however
/// large the files.
/// </summary>
public static class ZipBundle
{
    /// <summary>Writes <paramref name="files"/> (all inside <paramref name="folder"/>) to a new .zip in
    /// <paramref name="intoFolder"/>, keeping their paths relative to <paramref name="folder"/>.
    /// Returns the zip's path.</summary>
    public static async Task<string> WriteAsync(string folder, IReadOnlyList<string> files, string intoFolder, CancellationToken ct)
    {
        var path = Path.Combine(intoFolder, NameFor(files));
        var entries = files.OrderBy(f => f, StringComparer.Ordinal).Select(f => (Path.GetRelativePath(folder, f).Replace('\\', '/'), f)).ToList();
        await WriteEntriesAsync(path, entries, ct).ConfigureAwait(false);
        return path;
    }

    /// <summary>Writes the given files, each under its entry name, to a new owner-only .zip at <paramref name="path"/>.</summary>
    public static async Task WriteEntriesAsync(string path, IReadOnlyList<(string Entry, string File)> entries, CancellationToken ct)
    {
        var create = new FileStreamOptions { Mode = FileMode.CreateNew, Access = FileAccess.Write, Share = FileShare.None };
        if (!OperatingSystem.IsWindows())
        {
            create.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite; // owner only, from the start
        }

        await using var output = new FileStream(path, create);
        await using var zip = ZipWriter.Create(output);
        foreach (var (entry, file) in entries)
        {
            ct.ThrowIfCancellationRequested();
            await zip.AddFileAsync(entry, file, null, ct).ConfigureAwait(false);
        }
    }

    /// <summary>The download's name: what the files' names share ("report-p1.pdf", "report-p2.pdf" →
    /// "report.zip"), or "Chuvadi files.zip" when they share nothing useful.</summary>
    public static string NameFor(IReadOnlyList<string> files)
    {
        var names = files.Select(Path.GetFileNameWithoutExtension).Where(n => !string.IsNullOrEmpty(n)).ToList();
        var common = names.Count == 0 ? string.Empty : names.Aggregate((a, b) =>
        {
            var n = 0;
            while (n < a!.Length && n < b!.Length && a[n] == b[n])
            {
                n++;
            }

            return a[..n];
        })!;
        char[] separators = [' ', '-', '_', '.', '(', '[', ','];
        if (names.Any(n => n!.Length > common.Length) && common.Length > 0 && !separators.Contains(common[^1])
            && common.LastIndexOfAny(separators) is > 0 and var cut)
        {
            common = common[..cut]; // "report-p1", "report-p2" share "report-p": keep whole words, "report"
        }

        common = common.TrimEnd(separators);
        return SpaceLayout.SafeFileName(common.Length >= 2 ? common + ".zip" : "Chuvadi files.zip", "Chuvadi files") is var safe
            && safe.EndsWith(".zip", StringComparison.OrdinalIgnoreCase) ? safe : safe + ".zip";
    }
}
