using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Linux.Platform;

/// <summary>What the Linux host is: desktop form factor, Ctrl labels, 12 px window corners (handout), and
/// the window buttons exactly as the desktop lays them out (GNOME/KDE setting) — followed live: when the
/// person changes the layout while Chuvadi is open, <see cref="IPlatformInfo.ChromeChanged"/> is raised and
/// the top bar redraws (D-101).</summary>
internal sealed class LinuxPlatformInfo : IPlatformInfo
{
    private ShellChrome _chrome;

    private LinuxPlatformInfo(ShellChrome chrome) => _chrome = chrome;

    /// <summary>Main thread, after GTK init (reads GtkSettings and listens for its changes).</summary>
    public static LinuxPlatformInfo Create()
    {
        var info = new LinuxPlatformInfo(ChromeFor(Native.ButtonLayout()));
        GtkHost.ButtonLayoutChanged += info.OnLayoutChanged;
        return info;
    }

    public PlatformKind Kind => PlatformKind.Linux;

    public FormFactor FormFactor => FormFactor.Desktop;

    public event Action? FormFactorChanged { add { } remove { } }

    public InputKinds Input => InputKinds.Mouse | InputKinds.Keyboard;

    public ShellChrome Chrome => Volatile.Read(ref _chrome);

    public event Action? ChromeChanged;

    public PlatformCapabilities Capabilities => FixedPlatformInfo.DesktopCapabilities;

    public IKeyLabels Keys { get; } = new CtrlKeyLabels();

    private void OnLayoutChanged(string layout)
    {
        var chrome = ChromeFor(layout);
        if (chrome.ButtonLayout is { } now && Chrome.ButtonLayout is { } was
            && now.Left.SequenceEqual(was.Left) && now.Right.SequenceEqual(was.Right))
        {
            return;
        }

        Volatile.Write(ref _chrome, chrome);
        ChromeChanged?.Invoke();
    }

    private static ShellChrome ChromeFor(string? layoutText)
    {
        var layout = GtkButtonLayout.Parse(layoutText);
        return new ShellChrome(
            GtkButtonLayout.SideOf(layout),
            NativeMenuBar: false,
            AccountMenu: false,
            TitleBarDrag: true,
            CornerRadiusPx: 12) { ButtonLayout = layout };
    }
}

/// <summary>Text and image clipboard through GdkClipboard (the desktop converts formats on paste).</summary>
public sealed class LinuxClipboard : IClipboard
{
    private readonly LinuxImageClipboard _images = new();

    public bool CanCopyText => true;

    public bool CanCopyImage => true;

    public Task SetTextAsync(string text, CancellationToken ct = default)
    {
        var value = text ?? string.Empty;
        return GtkHost.InvokeAsync(() =>
        {
            Native.ClipboardSetText(value);
            return true;
        });
    }

    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default) => _images.SetImageAsync(pngBytes, ct);
}

/// <summary>"Show in folder": the desktop's file manager with the file selected (FileManager1 over
/// D-Bus — Nautilus, Dolphin, Nemo, Thunar). Without one, opens the containing folder.</summary>
public sealed class LinuxFileManager : IFileManager
{
    public bool IsAvailable => true;

    public Task<bool> RevealAsync(string localPath, CancellationToken ct = default) => Task.Run(() =>
    {
        string full;
        try
        {
            full = Path.GetFullPath(localPath);
        }
        catch (ArgumentException)
        {
            return false;
        }

        if (!File.Exists(full))
        {
            return false;
        }

        if (Native.Reveal(full) != 0)
        {
            return true;
        }

        try
        {
            var psi = new ProcessStartInfo("xdg-open") { UseShellExecute = false };
            psi.ArgumentList.Add(Path.GetDirectoryName(full)!);
            using var p = Process.Start(psi);
            return p is not null;
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or IOException)
        {
            return false;
        }
    }, ct);
}
