namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-24: several files handed over at once become tabs in a known order. macOS gives the app a batch of
/// opened files as an unordered set, so the order they were given in (Finder's selection, the command line) cannot
/// be recovered, and tabs came out shuffled. A batch is put in Finder's Name order instead — by file name, ignoring
/// case, numbers by value ("page 2" before "page 10") — then by extension and full path, so the same batch always
/// opens the same way. The comparison is written out here: .NET's own numeric ordering (CompareOptions.NumericOrdering)
/// is not supported by the globalization layer on Apple platforms and threw on a real Mac.
/// </summary>
internal static class FileBatchOrder
{
    public static IReadOnlyList<string> Sort(IEnumerable<string> paths) =>
        paths.OrderBy(p => Path.GetFileNameWithoutExtension(p), Comparer<string>.Create(Natural))
             .ThenBy(p => Path.GetExtension(p), StringComparer.OrdinalIgnoreCase)   // "Annex.pdf" before "annex b.pdf"
             .ThenBy(p => p, StringComparer.Ordinal)
             .ToArray();

    /// <summary>Text compared ignoring case, runs of digits compared by value.</summary>
    internal static int Natural(string? a, string? b)
    {
        a ??= string.Empty;
        b ??= string.Empty;
        int i = 0, j = 0;
        while (i < a.Length && j < b.Length)
        {
            if (char.IsAsciiDigit(a[i]) && char.IsAsciiDigit(b[j]))
            {
                int si = i, sj = j;
                while (i < a.Length && char.IsAsciiDigit(a[i])) { i++; }
                while (j < b.Length && char.IsAsciiDigit(b[j])) { j++; }
                var da = a.AsSpan(si, i - si).TrimStart('0');
                var db = b.AsSpan(sj, j - sj).TrimStart('0');
                var c = da.Length != db.Length ? da.Length.CompareTo(db.Length) : da.SequenceCompareTo(db);
                if (c != 0)
                {
                    return c;
                }
            }
            else
            {
                var c = char.ToUpperInvariant(a[i]).CompareTo(char.ToUpperInvariant(b[j]));
                if (c != 0)
                {
                    return c;
                }

                i++;
                j++;
            }
        }

        return (a.Length - i).CompareTo(b.Length - j);
    }
}
