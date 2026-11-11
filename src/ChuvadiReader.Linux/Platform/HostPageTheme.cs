using System.Text;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Puts the saved theme on the host page's root element before it is served, so the page's first paint is in that
/// theme. Without it the page painted light parchment between the window's own pre-paint colour and the app's
/// first render: a light flash on every start in the dark theme.
/// </summary>
public static class HostPageTheme
{
    private static readonly string[] Themes = ["light", "dark", "palm", "indigo", "contrast"];

    /// <summary>The page with <c>data-theme</c> on its root element; unchanged for an unknown theme, a page that
    /// already has one, or anything that isn't the host page.</summary>
    public static byte[] Apply(byte[] page, string? theme)
    {
        if (theme is null || Array.IndexOf(Themes, theme) < 0)
        {
            return page;
        }

        var html = Encoding.UTF8.GetString(page);
        var at = html.IndexOf("<html ", StringComparison.Ordinal);
        var end = at < 0 ? -1 : html.IndexOf('>', at);
        if (end < 0 || html.AsSpan(at, end - at).Contains("data-theme=", StringComparison.Ordinal))
        {
            return page; // not the host page, or its root tag already names a theme
        }

        return Encoding.UTF8.GetBytes(html.Insert(at + "<html ".Length, $"data-theme=\"{theme}\" "));
    }
}
