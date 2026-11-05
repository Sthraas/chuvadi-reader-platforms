using ChuvadiReader.Platform;

namespace ChuvadiReader.Ui.Components.Platform;

/// <summary>Snapshot of the platform facts the Ui renders from; cascaded by <c>PlatformRoot</c>.</summary>
public sealed record PlatformState(PlatformKind Kind, FormFactor FormFactor, InputKinds Input, ShellChrome Chrome, PlatformCapabilities Capabilities)
{
    /// <summary>What the Ui switches chrome on: desktop, tablet, phone or portal.</summary>
    public ShellLayout Shell => ShellLayouts.From(Kind, FormFactor);

    public string ShellKey => ShellLayouts.Key(Shell);

    public string KindKey => Kind switch
    {
        PlatformKind.Windows => "windows",
        PlatformKind.MacOS => "macos",
        PlatformKind.Linux => "linux",
        PlatformKind.Android => "android",
        _ => "web",
    };

    public string FormFactorKey => FormFactor switch
    {
        FormFactor.Tablet => "tablet",
        FormFactor.Phone => "phone",
        _ => "desktop",
    };

    public string InputKey => string.Join(' ', new[]
    {
        Input.HasFlag(InputKinds.Mouse) ? "mouse" : null,
        Input.HasFlag(InputKinds.Touch) ? "touch" : null,
        Input.HasFlag(InputKinds.Pen) ? "pen" : null,
        Input.HasFlag(InputKinds.Keyboard) ? "keyboard" : null,
    }.Where(s => s is not null));

    public static PlatformState From(IPlatformInfo p) => new(p.Kind, p.FormFactor, p.Input, p.Chrome, p.Capabilities);
}
