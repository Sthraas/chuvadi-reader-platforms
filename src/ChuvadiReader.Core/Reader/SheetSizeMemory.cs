namespace ChuvadiReader.Core.Reader;

/// <summary>
/// D-190: column widths and row heights a person set on screen to read a sheet (dragging a header's edge, or a
/// double press to fit). For viewing only: they are never written to the file and never change what a cell holds.
/// Kept with the tab, in memory; they go when the tab closes. Sizes are pixels at 100 %.
/// </summary>
public sealed class SheetSizeMemory
{
    /// <summary>The smallest size a drag can give: a column or row cannot be dragged out of sight.</summary>
    public const double Smallest = 8;

    /// <summary>The largest size a drag or a fit can give.</summary>
    public const double LargestWidth = 1200, LargestHeight = 600;

    /// <summary>One sheet's own sizes, by 1-based column and row number.</summary>
    public sealed class Sizes
    {
        public Dictionary<int, double> Cols { get; } = new();

        public Dictionary<int, double> Rows { get; } = new();

        public bool Any => Cols.Count + Rows.Count > 0;
    }

    private readonly Dictionary<(string File, string Sheet), Sizes> _sheets = new();

    /// <summary>The sheet's own sizes, or null when it is shown at the file's sizes.</summary>
    public Sizes? Find(string file, string sheet) =>
        _sheets.TryGetValue((file, sheet), out var sizes) && sizes.Any ? sizes : null;

    public void SetColumn(string file, string sheet, int column, double px) =>
        For(file, sheet).Cols[column] = Math.Clamp(px, Smallest, LargestWidth);

    public void SetRow(string file, string sheet, int row, double px) =>
        For(file, sheet).Rows[row] = Math.Clamp(px, Smallest, LargestHeight);

    /// <summary>One column back to the file's own width.</summary>
    public void ClearColumn(string file, string sheet, int column)
    {
        if (_sheets.TryGetValue((file, sheet), out var sizes)) sizes.Cols.Remove(column);
    }

    public void ClearRow(string file, string sheet, int row)
    {
        if (_sheets.TryGetValue((file, sheet), out var sizes)) sizes.Rows.Remove(row);
    }

    /// <summary>The whole sheet back to the file's own sizes.</summary>
    public void Reset(string file, string sheet) => _sheets.Remove((file, sheet));

    private Sizes For(string file, string sheet)
    {
        if (!_sheets.TryGetValue((file, sheet), out var sizes)) _sheets[(file, sheet)] = sizes = new Sizes();
        return sizes;
    }
}
