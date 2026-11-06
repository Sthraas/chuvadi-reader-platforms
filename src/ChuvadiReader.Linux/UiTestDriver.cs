#if CHUVADI_UITEST
using System.Collections.Concurrent;
using System.Text.Json;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;

namespace ChuvadiReader.Linux;

/// <summary>
/// UI test driver — compiled only into the test build (dotnet build -p:UiTest=true), never into the
/// shipped app. Reads one command per line on stdin, answers one line per command on stdout:
///   js &lt;function body&gt;   → "OK &lt;json&gt;" (runs in the page; "return …" gives a value; await allowed)
///   commands             → "OK [{id,label,group,keys,enabled}…]" (the Ctrl K registry, IAppCommands)
///   invoke &lt;id&gt;          → "OK true|false" (runs a command on the Blazor dispatcher)
///   open &lt;path&gt;          → "OK true" (as a file arriving from outside: OpenDocumentService.Request)
/// Errors answer "ERR &lt;message&gt;". tools/linux/uitest.py drives it.
/// </summary>
internal static class UiTestDriver
{
    private static readonly ConcurrentDictionary<int, TaskCompletionSource<string>> Pending = new();
    private static int _next;

    public static void Start(IServiceProvider services, LinuxWebViewManager manager)
    {
        GtkHost.JsResult += (token, result) =>
        {
            if (Pending.TryRemove(token, out var tcs))
            {
                tcs.TrySetResult(result);
            }
        };

        var thread = new Thread(() => Loop(services, manager)) { IsBackground = true, Name = "uitest" };
        thread.Start();
        Console.Error.WriteLine("[uitest] driver ready");
    }

    private static void Loop(IServiceProvider services, LinuxWebViewManager manager)
    {
        string? line;
        while ((line = Console.In.ReadLine()) is not null)
        {
            string reply;
            try
            {
                reply = "OK " + Run(services, manager, line).GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                reply = "ERR " + ex.Message.ReplaceLineEndings(" ");
            }

            Console.Out.WriteLine(reply);
            Console.Out.Flush();
        }
    }

    private static async Task<string> Run(IServiceProvider services, LinuxWebViewManager manager, string line)
    {
        var space = line.IndexOf(' ');
        var verb = space < 0 ? line : line[..space];
        var arg = space < 0 ? string.Empty : line[(space + 1)..];
        switch (verb)
        {
            case "js":
            {
                var token = Interlocked.Increment(ref _next);
                var tcs = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
                Pending[token] = tcs;
                GtkHost.Post(() => Native.EvalJs(token, arg));
                var result = await tcs.Task.WaitAsync(TimeSpan.FromSeconds(30));
                return result.StartsWith('!') ? throw new InvalidOperationException(result[1..]) : result;
            }

            case "commands":
            {
                var commands = services.GetRequiredService<IAppCommands>();
                var list = await manager.Dispatcher.InvokeAsync(() => commands.Commands
                    .Select(c => new { c.Id, c.Label, c.Group, c.Keys, Enabled = c.IsEnabled })
                    .ToList());
                return JsonSerializer.Serialize(list);
            }

            case "invoke":
            {
                var commands = services.GetRequiredService<IAppCommands>();
                var ok = await manager.Dispatcher.InvokeAsync(() => commands.InvokeAsync(arg));
                return ok ? "true" : "false";
            }

            case "open":
                await manager.Dispatcher.InvokeAsync(() => services.GetRequiredService<OpenDocumentService>().Request(arg));
                return "true";

            default:
                throw new InvalidOperationException("unknown command " + verb);
        }
    }
}
#endif
