using ChuvadiReader.Platform;

namespace ChuvadiReader.Hosting.Desktop;

/// <summary>
/// Standard per-user folders on Windows, macOS and Linux. The Windows values equal what Core uses
/// today (%AppData%\Chuvadi, Documents); macOS uses ~/Library/Application Support/Chuvadi and Linux
/// follows XDG ($XDG_CONFIG_HOME or ~/.config).
/// </summary>
public sealed class DesktopAppPaths : IAppPaths
{
    public DesktopAppPaths()
    {
        AppDataFolder = ResolveAppData();
        // Same folder Core uses today (Path.GetTempPath()), so moving Core to IAppPaths changes nothing on desktop.
        WorkingFolder = Path.GetTempPath();
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        DefaultSaveFolder = string.IsNullOrEmpty(docs) ? null : docs;
    }

    public string AppDataFolder { get; }

    public string WorkingFolder { get; }

    public string? DefaultSaveFolder { get; }

    private static string ResolveAppData()
    {
        if (OperatingSystem.IsMacOS())
        {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return Path.Combine(home, "Library", "Application Support", "Chuvadi");
        }

        if (OperatingSystem.IsLinux())
        {
            var xdg = Environment.GetEnvironmentVariable("XDG_CONFIG_HOME");
            var root = !string.IsNullOrEmpty(xdg) && Path.IsPathRooted(xdg)
                ? xdg
                : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config");
            return Path.Combine(root, "Chuvadi");
        }

        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Chuvadi");
    }
}
