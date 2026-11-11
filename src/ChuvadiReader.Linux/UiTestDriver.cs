#if CHUVADI_UITEST
using System.Collections.Concurrent;
using System.Text.Json;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;

namespace ChuvadiReader.Linux;

/// <summary>
/// UI test driver — compiled only into the test build (dotnet build -p:UiTest=true), never into the
/// shipped app. Reads one command per line on stdin, "&lt;n&gt; &lt;verb&gt; &lt;args&gt;", and answers "&lt;n&gt; OK &lt;json&gt;" or
/// "&lt;n&gt; ERR &lt;message&gt;" on stdout. Each command runs on its own, so one that waits (a command that opens
/// a dialog) never holds up the next.
///   js &lt;function body&gt;   → the result (runs in the page; "return …" gives a value; await allowed)
///   commands             → [{id,label,group,keys,enabled}…] (the Ctrl K registry, IAppCommands)
///   invoke &lt;id&gt;          → true | false | "pending" (still running after 2 s, e.g. waiting in a dialog)
///   open &lt;path&gt;          → true (as a file arriving from outside: OpenDocumentService.Request)
///   set-layout &lt;layout&gt;   → true (sets GTK's gtk-decoration-layout, as a desktop settings change does)
///   render-info          → {"noGpu":…,"compositingOff":…} (what the host chose at start-up, B-12)
///   drop &lt;p1&gt;\t&lt;p2&gt;…    → true (the window's drop handler, with these paths, as GTK's drop target calls it)
/// tools/linux/uitest.py drives it.
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

    private static readonly object WriteLock = new();

    private static void Loop(IServiceProvider services, LinuxWebViewManager manager)
    {
        string? line;
        while ((line = Console.In.ReadLine()) is not null)
        {
            var space = line.IndexOf(' ');
            if (space <= 0)
            {
                continue;
            }

            var id = line[..space];
            var command = line[(space + 1)..];
            _ = Task.Run(async () =>
            {
                string reply;
                try
                {
                    reply = "OK " + await Run(services, manager, command);
                }
                catch (Exception ex)
                {
                    reply = "ERR " + ex.Message.ReplaceLineEndings(" ");
                }

                lock (WriteLock)
                {
                    Console.Out.WriteLine(id + " " + reply);
                    Console.Out.Flush();
                }
            });
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
                var run = manager.Dispatcher.InvokeAsync(() => commands.InvokeAsync(arg));
                if (await Task.WhenAny(run, Task.Delay(TimeSpan.FromSeconds(2))) != run)
                {
                    return "\"pending\"";
                }

                return await run ? "true" : "false";
            }

            case "open":
                await manager.Dispatcher.InvokeAsync(() => services.GetRequiredService<OpenDocumentService>().Request(arg));
                return "true";

            case "set-layout":
                GtkHost.Post(() => Native.SetButtonLayout(arg));
                return "true";

            case "pinch":
            {
                // "x y ratio": one pinch step at a place in the view, sent as the gesture sends it (no pinch under Xvfb).
                var parts = arg.Split(' ', StringSplitOptions.RemoveEmptyEntries)
                    .Select(v => double.Parse(v, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                GtkHost.Post(() => Native.Pinch(parts[0], parts[1], parts[2]));
                return "true";
            }

            case "start-mark":
                return await GtkHost.InvokeAsync(() => Native.StartMarkShown() != 0) ? "true" : "false";

            case "gc-count":
                return JsonSerializer.Serialize(new { reliefPasses = Platform.GlibcTrim.Relieved });

            case "gc":
            {
                // What an aggressive collection gives back (test-only; the sixteenth patch's relief runs the same call).
                var before = Environment.WorkingSet;
                var heapBefore = GC.GetGCMemoryInfo().HeapSizeBytes;
                GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
                var info = GC.GetGCMemoryInfo();
                return JsonSerializer.Serialize(new
                {
                    reliefPasses = Platform.GlibcTrim.Relieved,
                    residentBeforeMb = before / 1048576,
                    residentAfterMb = Environment.WorkingSet / 1048576,
                    heapBeforeMb = heapBefore / 1048576,
                    heapAfterMb = info.HeapSizeBytes / 1048576,
                    committedAfterMb = info.TotalCommittedBytes / 1048576,
                });
            }

            case "render-info":
            {
                var tcs = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
                GtkHost.Post(() => tcs.SetResult(Native.RenderInfo()));
                var info = await tcs.Task.WaitAsync(TimeSpan.FromSeconds(10));
                return JsonSerializer.Serialize(new { noGpu = (info & 1) != 0, compositingOff = (info & 2) != 0 });
            }

            case "drop":
                GtkHost.Post(() => GtkHost.SimulateDrop(arg.Split('\t', StringSplitOptions.RemoveEmptyEntries)));
                return "true";

            default:
                throw new InvalidOperationException("unknown command " + verb);
        }
    }
}
#endif
