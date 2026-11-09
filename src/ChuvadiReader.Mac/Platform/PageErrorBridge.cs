using Foundation;
using Microsoft.Extensions.Logging;
using WebKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Mac Test M-19: errors that happen in the page reach the D-132 error log. When a Razor component throws,
/// MAUI Blazor's renderer only tells the page (the "An error occurred" bar, plus the exception's message and
/// .NET stack trace on console.error) and rethrows into a dispatcher task nobody awaits — no logger and no
/// unhandled-exception event ever sees it. The host page (wwwroot/index.html) forwards console.error,
/// window errors and unhandled promise rejections here, and they are logged as errors (scrubbed as always).
/// </summary>
internal sealed class PageErrorBridge : NSObject, IWKScriptMessageHandler
{
    public const string Name = "chvdLog";
    private readonly ILogger _log;

    private PageErrorBridge(ILogger log) => _log = log;

    internal static IDisposable? ReloadWatch; // kept for the app's life

    public static void Attach(WKWebView view, IServiceProvider services)
    {
        var log = services.GetRequiredService<ILoggerFactory>().CreateLogger("ChuvadiReader.Ui.Page");
        view.Configuration.UserContentController.AddScriptMessageHandler(new PageErrorBridge(log), Name);

        // Mac Test M-19 / M-18: when WebKit's content process ends, nothing throws in the page or in .NET first —
        // WebKit loads the page again and the old Blazor session is disposed (only that follow-on error was logged).
        // The Ui never navigates its own page, so any load after the first is that event: log it as the error.
        var loads = 0;
        ReloadWatch = view.AddObserver("loading", NSKeyValueObservingOptions.New, _ =>
        {
            if (view.IsLoading && ++loads > 1)
            {
                log.LogError("the page was loaded again (load {Count}) — WebKit's content process ended or the page was reset; the Ui session was lost", loads);
            }
        });
    }

    [Export("userContentController:didReceiveScriptMessage:")]
    public void DidReceiveScriptMessage(WKUserContentController userContentController, WKScriptMessage message)
    {
        var text = message.Body?.ToString() ?? string.Empty;
        if (text.Length == 0)
        {
            return;
        }

        // First line is the message; the rest is the stack (.NET's for a component exception, JS's otherwise).
        var nl = text.IndexOf('\n');
        var head = nl < 0 ? text : text[..nl];
        var stack = nl < 0 ? null : text[(nl + 1)..];
        _log.LogError(new PageError(head, stack), "page error");
    }

    /// <summary>A page error carried as an exception so the log writes its message and stack the usual way.</summary>
    private sealed class PageError(string message, string? stack) : Exception(message)
    {
        public override string? StackTrace => stack;
    }
}
