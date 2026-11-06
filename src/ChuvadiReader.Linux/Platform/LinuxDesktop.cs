using System.Diagnostics;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Linux.Platform;

/// <summary>What the Linux host is: desktop form factor, Ctrl labels, window buttons on the side the
/// desktop's own button layout puts them (GNOME/KDE setting), 12 px window corners (handout).</summary>
internal static class LinuxPlatformInfo
{
    /// <summary>Main thread, after GTK init (reads GtkSettings).</summary>
    public static IPlatformInfo Create() => new FixedPlatformInfo(
        PlatformKind.Linux,
        InputKinds.Mouse | InputKinds.Keyboard,
        new ShellChrome(
            Native.ButtonsOnLeft() != 0 ? WindowButtons.Left : WindowButtons.Right,
            NativeMenuBar: false,
            AccountMenu: false,
            TitleBarDrag: true,
            CornerRadiusPx: 12),
        FixedPlatformInfo.DesktopCapabilities,
        new CtrlKeyLabels());
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
