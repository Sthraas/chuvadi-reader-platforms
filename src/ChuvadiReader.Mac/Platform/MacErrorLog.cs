using System.Text;
using Foundation;
using Microsoft.Extensions.Logging;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// D-132: warnings and errors go to ~/Library/Logs/Chuvadi/chuvadi.log, so a failure on a person's Mac can be
/// diagnosed. Kept on the Mac and never sent anywhere. About 1 MB at most: the file rolls over to chuvadi.1.log
/// at 512 KB, and the older roll-over is replaced. Console.app shows it under Log Reports.
/// Nothing the person was reading goes in: every message passes <see cref="LogScrubber"/> — file paths and names
/// become their extension and a short hash, quoted values (where an exception would quote document text or a
/// password) become a hash, links keep only their scheme and host, and each entry is capped in length.
/// </summary>
internal sealed class MacErrorLog : ILoggerProvider
{
    internal const long RollAt = 512 * 1024;
    private static readonly object Gate = new();
    private readonly string _file;
    private readonly string _rolled;
    private readonly LogScrubber _scrub;

    public MacErrorLog(string appDataFolder)
    {
        Folder = LogsFolder();
        Directory.CreateDirectory(Folder);
        _file = Path.Combine(Folder, "chuvadi.log");
        _rolled = Path.Combine(Folder, "chuvadi.1.log");
        _scrub = new LogScrubber(LogScrubber.LoadOrCreateSalt(Path.Combine(appDataFolder, "log-salt")));
    }

    public string Folder { get; }

    public static string LogsFolder()
    {
        var library = NSFileManager.DefaultManager.GetUrls(NSSearchPathDirectory.LibraryDirectory, NSSearchPathDomain.User)
            .FirstOrDefault()?.Path ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library");
        return Path.Combine(library, "Logs", "Chuvadi");
    }

    public ILogger CreateLogger(string categoryName) => new Logger(this, categoryName);

    public void Dispose()
    {
    }

    /// <summary>Unhandled exceptions anywhere in the app (they may never reach a logger).</summary>
    public void WatchUnhandled()
    {
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            Write(LogLevel.Critical, "Unhandled", e.ExceptionObject as Exception, "unhandled exception");
        TaskScheduler.UnobservedTaskException += (_, e) =>
            Write(LogLevel.Error, "UnobservedTask", e.Exception, "unobserved task exception");
    }

    internal void Write(LogLevel level, string category, Exception? exception, string message)
    {
        try
        {
            var line = new StringBuilder()
                .Append(DateTimeOffset.Now.ToString("yyyy-MM-dd'T'HH:mm:ss.fffzzz", System.Globalization.CultureInfo.InvariantCulture))
                .Append(' ').Append(level).Append(' ').Append(category).Append(": ")
                .Append(_scrub.Clean(message));
            for (var ex = exception; ex is not null; ex = ex.InnerException)
            {
                line.Append(ex == exception ? " | " : " | inner ").Append(ex.GetType().FullName).Append(": ").Append(_scrub.Clean(ex.Message));
            }

            if (exception?.StackTrace is { Length: > 0 } stack)
            {
                line.Append(" | at ").Append(_scrub.CleanStack(stack));
            }

            line.Append('\n');
            var bytes = Encoding.UTF8.GetBytes(line.ToString());
            lock (Gate)
            {
                if (File.Exists(_file) && new FileInfo(_file).Length + bytes.Length > RollAt)
                {
                    File.Move(_file, _rolled, overwrite: true);
                }

                using var stream = new FileStream(_file, FileMode.Append, FileAccess.Write, FileShare.Read);
                stream.Write(bytes);
            }
        }
        catch
        {
            // The log must never be the thing that fails.
        }
    }

    private sealed class Logger(MacErrorLog log, string category) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => logLevel >= LogLevel.Warning && logLevel != LogLevel.None;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            if (IsEnabled(logLevel))
            {
                log.Write(logLevel, eventId.Id != 0 ? $"{category}[{eventId.Id}]" : category, exception, formatter(state, null));
            }
        }
    }
}
