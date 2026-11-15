namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Where a page goes on the sheet (Mac Test M-26): the page as shown (its /Rotate counted) is centred in the sheet's
/// printable area — scaled to it when the request says fit to page, at its own size otherwise, and in that case
/// still made smaller if it would not fit, so no part of a page is ever cut off.
/// </summary>
internal static class PrintFit
{
    /// <summary>Scale, and the left and top of the placed page, in the sheet's points.</summary>
    public readonly record struct Placement(double Scale, double X, double Y, double Width, double Height);

    public static Placement Place(double shownWidth, double shownHeight, double areaX, double areaY, double areaWidth, double areaHeight, bool fitToPage)
    {
        if (shownWidth <= 0 || shownHeight <= 0 || areaWidth <= 0 || areaHeight <= 0)
        {
            return new Placement(1, areaX, areaY, Math.Max(shownWidth, 0), Math.Max(shownHeight, 0));
        }

        var fit = Math.Min(areaWidth / shownWidth, areaHeight / shownHeight);
        var scale = fitToPage ? fit : Math.Min(1, fit);
        var w = shownWidth * scale;
        var h = shownHeight * scale;
        return new Placement(scale, areaX + (areaWidth - w) / 2, areaY + (areaHeight - h) / 2, w, h);
    }

    /// <summary>The page's size as shown: width and height change places for a quarter turn.</summary>
    public static (double Width, double Height) Shown(double width, double height, int rotation)
        => ((rotation % 180) + 180) % 180 == 90 ? (height, width) : (width, height);
}
