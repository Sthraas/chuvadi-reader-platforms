using System.Globalization;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-24: several files handed over at once become tabs in a known order. macOS gives the app a batch of
/// opened files as an unordered set, so the order they were given in (Finder's selection, the command line) cannot
/// be recovered, and tabs came out shuffled. A batch is put in Finder's Name order instead — by file name, ignoring
/// case, numbers by value ("page 2" before "page 10") — then by full path, so the same batch always opens the same way.
/// </summary>
internal static class FileBatchOrder
{
    private static readonly CompareInfo Compare = CultureInfo.InvariantCulture.CompareInfo;
    private const CompareOptions Options = CompareOptions.IgnoreCase | CompareOptions.NumericOrdering;

    public static IReadOnlyList<string> Sort(IEnumerable<string> paths) =>
        paths.OrderBy(p => Path.GetFileNameWithoutExtension(p), Comparer<string>.Create((a, b) => Compare.Compare(a, b, Options)))
             .ThenBy(p => Path.GetExtension(p), StringComparer.OrdinalIgnoreCase)   // "Annex.pdf" before "annex b.pdf"
             .ThenBy(p => p, StringComparer.Ordinal)
             .ToArray();
}
