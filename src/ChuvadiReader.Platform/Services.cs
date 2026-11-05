namespace ChuvadiReader.Platform;

// ─────────────────────────────────────────────────────────────────────────────
// File model (decision pending: option C "working path + write-back", see PLATFORM-INTERFACE.md §3).
//
// Core works on local file paths today, and the existing IFilePicker returns paths. Every host
// therefore guarantees that what it hands to Core is a readable local path:
//   * Windows / macOS / Linux: the real path.
//   * Android: a working copy in the app's private storage, made from the content URI.
//   * Web: a working copy in the signed-in person's encrypted, per-user server storage.
// After Core or Ui writes a file the person chose (Save, Save as, export to a folder), it calls
// IFileWriteBack.CommitAsync(path). Desktop hosts do nothing; Android writes the bytes back to
// the URI; Web stores the file and/or starts the browser download.
// ─────────────────────────────────────────────────────────────────────────────

/// <summary>Outcome of <see cref="IFileWriteBack.CommitAsync"/>.</summary>
public enum WriteBackOutcome
{
    /// <summary>Nothing to do: the path is the real file (desktop hosts).</summary>
    NotNeeded,

    /// <summary>The bytes reached their destination.</summary>
    Done,

    /// <summary>The person cancelled (e.g. a browser download prompt).</summary>
    Cancelled,

    /// <summary>The destination refused the write. <see cref="WriteBackResult.Message"/> is user-facing.</summary>
    Failed,
}

/// <summary>Result of a write-back. <paramref name="Message"/> is short and user-facing.</summary>
public sealed record WriteBackResult(WriteBackOutcome Outcome, string? Message = null)
{
    public static readonly WriteBackResult NotNeeded = new(WriteBackOutcome.NotNeeded);

    public bool Succeeded => Outcome is WriteBackOutcome.NotNeeded or WriteBackOutcome.Done;
}

/// <summary>
/// Sends a file Chuvadi has just written at a local path back to where the person meant it to go.
/// Call it after every write to a path that came from a picker or from an opened document.
/// </summary>
public interface IFileWriteBack
{
    /// <summary>False on hosts where every path is the real file (desktop). Callers may skip the call.</summary>
    bool IsNeeded { get; }

    /// <summary>Commits one file, or every file inside a folder path returned by a folder picker.</summary>
    Task<WriteBackResult> CommitAsync(string localPath, CancellationToken ct = default);
}

/// <summary>Host default for desktop: paths are real files.</summary>
public sealed class NoFileWriteBack : IFileWriteBack
{
    public bool IsNeeded => false;

    public Task<WriteBackResult> CommitAsync(string localPath, CancellationToken ct = default) =>
        Task.FromResult(WriteBackResult.NotNeeded);
}

/// <summary>Folders the app uses. Replaces direct use of Environment.SpecialFolder in Core and Ui.</summary>
public interface IAppPaths
{
    /// <summary>Settings, sessions, recovery drafts. Per user on Web.</summary>
    string AppDataFolder { get; }

    /// <summary>Scratch files (renders, intermediate PDFs). Per user on Web; cleared by the host.</summary>
    string WorkingFolder { get; }

    /// <summary>Suggested default save folder, or null when the host has no visible file system (Web).</summary>
    string? DefaultSaveFolder { get; }
}

/// <summary>Who is using the app. Desktop: the local account name, never signed in until Sangam is added.</summary>
public interface IAccount
{
    bool IsSignedIn { get; }

    /// <summary>Name for the user chip, e.g. "Arun S.".</summary>
    string DisplayName { get; }

    /// <summary>Sangam ID when signed in.</summary>
    string? Email { get; }

    event Action? Changed;

    /// <summary>Starts Sangam sign-in. Returns false where sign-in isn't available yet.</summary>
    Task<bool> SignInAsync(CancellationToken ct = default);

    Task SignOutAsync(CancellationToken ct = default);
}

/// <summary>Text and image clipboard. Supersedes IImageClipboard and the JS navigator.clipboard call.</summary>
public interface IClipboard
{
    bool CanCopyText { get; }

    bool CanCopyImage { get; }

    Task SetTextAsync(string text, CancellationToken ct = default);

    /// <summary>Copies a PNG image (raw bytes).</summary>
    Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default);
}

/// <summary>
/// "Show in folder": opens the system file manager with the file selected (Explorer, Finder,
/// the Linux desktop's file manager). Not available on Android or Web.
/// </summary>
public interface IFileManager
{
    bool IsAvailable { get; }

    Task<bool> RevealAsync(string localPath, CancellationToken ct = default);
}

/// <summary>Share sheet (Android, macOS). No Ui calls this yet; adding a Share action is a design decision for Arun.</summary>
public interface IShare
{
    bool IsAvailable { get; }

    Task<bool> ShareFileAsync(string localPath, string title, CancellationToken ct = default);
}

/// <summary>App lifecycle events the host raises on its UI thread.</summary>
public interface IAppLifecycle
{
    /// <summary>The app is going to the background or the page is closing: flush drafts and sessions now.</summary>
    event Func<Task>? Suspending;

    event Action? Resumed;

    /// <summary>
    /// Android back button / gesture. Handlers return true when they consumed it (closed a sheet,
    /// a card or a drawer). When nobody does, the host performs its default (leave the app).
    /// </summary>
    event Func<bool>? BackRequested;
}

/// <summary>One command the Ui offers (the same list the Ctrl K command bar shows).</summary>
/// <param name="Id">Stable id, e.g. "doc.print".</param>
/// <param name="Label">User-facing label.</param>
/// <param name="Group">Menu it belongs to: Document, Read, Mark, Arrange, Protect, View.</param>
/// <param name="Keys">Canonical shortcut text ("Ctrl P"), or null.</param>
/// <param name="IsEnabled">False when the command can't run now.</param>
public sealed record AppCommandInfo(string Id, string Label, string Group, string? Keys, bool IsEnabled);

/// <summary>
/// Lets a native menu (macOS menu bar) show and run the Ui's commands.
/// The Ui publishes; the host reads and invokes.
/// </summary>
public interface IAppCommands
{
    IReadOnlyList<AppCommandInfo> Current { get; }

    event Action? Changed;

    /// <summary>Called by the Ui whenever its command list or enabled states change.</summary>
    void Publish(IReadOnlyList<AppCommandInfo> commands, Func<string, Task> invoke);

    /// <summary>Called by the host when a native menu item is chosen.</summary>
    Task InvokeAsync(string id);
}
