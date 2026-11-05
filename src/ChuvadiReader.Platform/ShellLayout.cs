namespace ChuvadiReader.Platform;

/// <summary>
/// The one value the Ui switches its chrome on. Derived from <see cref="PlatformKind"/> and
/// <see cref="FormFactor"/>; hosts never set it directly.
/// </summary>
public enum ShellLayout
{
    /// <summary>Windows, macOS, Linux: D-10 side rails, window buttons (Reader Side Rails).</summary>
    Desktop,

    /// <summary>Android tablet: same rails at 72 / 72 / 60 px, 48 px targets (Portal &amp; Android 12d-12f).</summary>
    Tablet,

    /// <summary>Android phone: bottom bar, tool strip, View sheet (Portal &amp; Android 12g-12j).</summary>
    Phone,

    /// <summary>Web portal: desktop rails, account menu, Sangam sign-in, server status text (Portal &amp; Android 12a-12c).</summary>
    Portal,
}

/// <summary>Derivation rule for <see cref="ShellLayout"/>, shared by every host and the Ui.</summary>
public static class ShellLayouts
{
    /// <summary>
    /// Web is always <see cref="ShellLayout.Portal"/> (portal chrome on any browser size; how the portal
    /// adapts to a small browser is decision F-5). Otherwise the form factor decides.
    /// </summary>
    public static ShellLayout From(PlatformKind kind, FormFactor formFactor) =>
        kind == PlatformKind.Web
            ? ShellLayout.Portal
            : formFactor switch
            {
                FormFactor.Tablet => ShellLayout.Tablet,
                FormFactor.Phone => ShellLayout.Phone,
                _ => ShellLayout.Desktop,
            };

    /// <summary>The value written to <c>&lt;html data-shell="…"&gt;</c>.</summary>
    public static string Key(ShellLayout layout) => layout switch
    {
        ShellLayout.Tablet => "tablet",
        ShellLayout.Phone => "phone",
        ShellLayout.Portal => "portal",
        _ => "desktop",
    };

    /// <summary>Shorthand for <c>From(info.Kind, info.FormFactor)</c>.</summary>
    public static ShellLayout Shell(this IPlatformInfo info) => From(info.Kind, info.FormFactor);
}
