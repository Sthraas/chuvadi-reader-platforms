using System.Text;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Hosting;

/// <summary>Shortcut labels for Windows, Linux, Android and Web: canonical text is shown as written.</summary>
public sealed class CtrlKeyLabels : IKeyLabels
{
    public string Primary => "Ctrl";

    public string Format(string canonical) => canonical;
}

/// <summary>macOS shortcut labels: "Ctrl Shift S" → "⌘⇧S", "Ctrl Alt W" → "⌘⌥W" (Apple's order: ⌃⌥⇧⌘).</summary>
public sealed class MacKeyLabels : IKeyLabels
{
    public string Primary => "⌘";

    public string Format(string canonical)
    {
        if (string.IsNullOrWhiteSpace(canonical)) return canonical;

        // macOS conventions that are not a plain Ctrl → ⌘ swap:
        // F11 is Show Desktop on a Mac; full screen is ⌃⌘F (the Mac host binds Immersive to it).
        if (canonical == "F11") return "⌃⌘F";

        bool cmd = false, shift = false, alt = false;
        var rest = new List<string>();
        foreach (var part in canonical.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        {
            switch (part)
            {
                case "Ctrl": cmd = true; break;
                case "Shift": shift = true; break;
                case "Alt": alt = true; break;
                default: rest.Add(part); break;
            }
        }

        // Next/previous tab is ⌃Tab on a Mac — ⌘Tab is the system app switcher (reader.js accepts ⌃Tab).
        var control = cmd && rest.Count == 1 && rest[0] == "Tab";
        if (control) cmd = false;

        var sb = new StringBuilder();
        if (control) sb.Append('⌃');
        if (alt) sb.Append('⌥');
        if (shift) sb.Append('⇧');
        if (cmd) sb.Append('⌘');
        sb.Append(string.Join(' ', rest));
        return sb.ToString();
    }
}

/// <summary>Lifecycle for hosts that never suspend (desktop): events are never raised.</summary>
public sealed class NoAppLifecycle : IAppLifecycle
{
    public event Func<Task>? Suspending { add { } remove { } }

    public event Action? Resumed { add { } remove { } }

    public event Func<bool>? BackRequested { add { } remove { } }
}

/// <summary>Desktop account until Sangam arrives: the local user name, never signed in.</summary>
public sealed class LocalAccount : IAccount
{
    public bool IsSignedIn => false;

    public string DisplayName => Environment.UserName;

    public string? Email => null;

    public event Action? Changed { add { } remove { } }

    public Task<bool> SignInAsync(CancellationToken ct = default) => Task.FromResult(false);

    public Task SignOutAsync(CancellationToken ct = default) => Task.CompletedTask;
}

/// <summary>A fixed <see cref="IPlatformInfo"/> for hosts whose form factor never changes (desktop).</summary>
public sealed class FixedPlatformInfo(
    PlatformKind kind,
    InputKinds input,
    ShellChrome chrome,
    PlatformCapabilities capabilities,
    IKeyLabels keys) : IPlatformInfo
{
    public PlatformKind Kind => kind;

    public FormFactor FormFactor => FormFactor.Desktop;

    public event Action? FormFactorChanged { add { } remove { } }

    public InputKinds Input => input;

    public ShellChrome Chrome => chrome;

    public PlatformCapabilities Capabilities => capabilities;

    public IKeyLabels Keys => keys;

    /// <summary>Everything a desktop file system offers.</summary>
    public static PlatformCapabilities DesktopCapabilities { get; } = new()
    {
        PickFolders = true,
        SaveInPlace = true,
        WatchFolders = true,
        RevealInFolder = true,
        DropFiles = true,
        Share = false,
        MultipleWindows = false,
        SavesAsDownload = false,
        ServerSide = false,
    };
}
