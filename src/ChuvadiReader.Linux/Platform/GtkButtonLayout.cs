using ChuvadiReader.Platform;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Reads the desktop's window-button layout exactly the way GTK's own header bars do
/// (gtk/gtkwindowcontrols.c, GTK 4.14: get_layout + update_window_buttons), so Chuvadi shows the buttons a
/// GTK app shows on the same desktop:
/// <list type="bullet">
/// <item>"left:right" — the part before the first ':' is the left end, the part after it the right end;
/// no ':' puts everything on the left.</item>
/// <item>Each part is a comma-separated list; <c>minimize</c>, <c>maximize</c> and <c>close</c> are drawn in
/// that order; anything else (<c>icon</c>, <c>menu</c>, <c>appmenu</c>, <c>spacer</c>, unknown names) is
/// not a window button and is skipped. Names match exactly (GTK uses strcmp: " close" is not close), and a
/// button named twice is drawn twice, as GTK does.</item>
/// <item>Unset (null): the GNOME/KDE default, minimise · maximise · close on the right.</item>
/// </list>
/// Examples: vanilla GNOME "appmenu:close" → close only, right. Ubuntu ":minimize,maximize,close".
/// macOS-like "close,minimize,maximize:" → all three on the left. "close:maximize" → close left, maximise right.
/// </summary>
public static class GtkButtonLayout
{
    private static readonly WindowButton[] Default = [WindowButton.Minimize, WindowButton.Maximize, WindowButton.Close];

    public static WindowButtonLayout Parse(string? layout)
    {
        if (layout is null)
        {
            return new WindowButtonLayout([], Default);
        }

        var colon = layout.IndexOf(':');
        var left = colon < 0 ? layout : layout[..colon];
        var right = colon < 0 ? string.Empty : layout[(colon + 1)..];
        return new WindowButtonLayout(Side(left), Side(right));
    }

    /// <summary>The side the ShellChrome's <see cref="WindowButtons"/> names (where close is; else where any button is).</summary>
    public static WindowButtons SideOf(WindowButtonLayout layout) =>
        layout.Left.Contains(WindowButton.Close) || (!layout.Right.Contains(WindowButton.Close) && layout.Left.Count > 0)
            ? WindowButtons.Left
            : WindowButtons.Right;

    private static WindowButton[] Side(string part)
    {
        var list = new List<WindowButton>();
        foreach (var name in part.Split(','))
        {
            WindowButton? b = name switch
            {
                "minimize" => WindowButton.Minimize,
                "maximize" => WindowButton.Maximize,
                "close" => WindowButton.Close,
                _ => null,
            };
            if (b is { } button)
            {
                list.Add(button);
            }
        }

        return [.. list];
    }
}
