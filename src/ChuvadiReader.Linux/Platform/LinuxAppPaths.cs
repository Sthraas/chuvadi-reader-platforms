using ChuvadiReader.Hosting.Desktop;
using ChuvadiReader.Platform;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Folders on Linux. Same as the shared <see cref="DesktopAppPaths"/> (XDG config folder, system temp)
/// except the default save folder: .NET returns an empty string for the Documents folder when it
/// doesn't exist yet, and Core would then save "Chuvadi Documents" under /tmp, which is wiped at
/// reboot. Here the save folder is always the person's Documents folder (XDG_DOCUMENTS_DIR from
/// user-dirs.dirs, as .NET reads it, else ~/Documents), created when first used.
/// </summary>
public sealed class LinuxAppPaths : IAppPaths
{
    private readonly DesktopAppPaths _desktop = new();

    public LinuxAppPaths()
    {
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments, Environment.SpecialFolderOption.DoNotVerify);
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (string.IsNullOrEmpty(docs) || !Path.IsPathRooted(docs) || string.Equals(docs.TrimEnd('/'), home.TrimEnd('/'), StringComparison.Ordinal))
        {
            // No XDG documents folder configured (or it points at home itself): use ~/Documents.
            docs = string.IsNullOrEmpty(home) ? null : Path.Combine(home, "Documents");
        }

        DefaultSaveFolder = docs;
    }

    public string AppDataFolder => _desktop.AppDataFolder;

    public string WorkingFolder => _desktop.WorkingFolder;

    public string? DefaultSaveFolder { get; }
}
