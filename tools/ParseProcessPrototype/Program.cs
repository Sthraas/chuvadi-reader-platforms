// TESTING ONLY (never shipped). D-198 B2 prototype for docs/foundation/PARSE-PROCESS-DESIGN.md.
//   engine                 the parse process: reads requests on stdin, answers on stdout (Wire)
//   bench <fixtures dir>   the app's side: measures, prints a report
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using ParseProcessPrototype;

if (args.Length > 0 && args[0] == "engine") return await Engine.RunAsync();
if (args.Length > 1 && args[0] == "bench") return await Bench.RunAsync(args[1], args.Skip(2).ToArray());
if (args.Length > 1 && args[0] == "coldfirst")
{
    // The first document a running app opens today: library code loaded and compiled in the app's own process.
    long t0 = System.Diagnostics.Stopwatch.GetTimestamp();
    using var s = await new ChuvadiPdfReader().OpenAsync(args[1], Path.GetFileName(args[1]));
    await s.RenderPageSvgAsync(0);
    Console.WriteLine((System.Diagnostics.Stopwatch.GetElapsedTime(t0).TotalMilliseconds).ToString("0.0"));
    return 0;
}
Console.Error.WriteLine("usage: engine | bench <fixtures folder> [--heap-mb N] [--limit-s N]");
return 2;

static class Engine
{
    // The Word model has an abstract block type; the real contract would declare its kinds once (source-generated).
    internal static readonly JsonSerializerOptions Json = new()
    {
        TypeInfoResolver = new System.Text.Json.Serialization.Metadata.DefaultJsonTypeInfoResolver
        {
            Modifiers =
            {
                ti =>
                {
                    if (ti.Type != typeof(WordBlock)) return;
                    ti.PolymorphismOptions = new() { TypeDiscriminatorPropertyName = "k" };
                    foreach (var (t, k) in new (Type, string)[] { (typeof(WordHeading), "h"), (typeof(WordPara), "p"), (typeof(WordTableBlock), "t") })
                        ti.PolymorphismOptions.DerivedTypes.Add(new(t, k));
                },
            },
        },
    };

    public static async Task<int> RunAsync()
    {
        var input = Console.OpenStandardInput();
        var output = Console.OpenStandardOutput();
        var reader = new ChuvadiPdfReader();
        IPdfSession? session = null;
        while (Wire.Read(input) is { } req)
        {
            string arg = Encoding.UTF8.GetString(req.Payload);
            try
            {
                switch (req.Code)
                {
                    case Wire.Ping: Wire.Write(output, Wire.Ok, Environment.ProcessId.ToString()); break;
                    case Wire.Open:
                        session?.Dispose();
                        session = await reader.OpenAsync(arg, Path.GetFileName(arg));
                        Wire.Write(output, Wire.Ok, session.Document.PageCount.ToString());
                        break;
                    case Wire.Render:
                        Wire.Write(output, Wire.Ok, await session!.RenderPageSvgAsync(int.Parse(arg)));
                        break;
                    case Wire.Close: session?.Dispose(); session = null; Wire.Write(output, Wire.Ok, ""); break;
                    case Wire.Word:
                        Wire.Write(output, Wire.Ok, JsonSerializer.SerializeToUtf8Bytes(new DocxViewService().Load(arg), Json));
                        break;
                    case Wire.Excel:
                        Wire.Write(output, Wire.Ok, JsonSerializer.SerializeToUtf8Bytes(new XlsxViewService().Load(arg), Json));
                        break;
                    case Wire.StackOverflow: Recurse(0); break;   // never returns: the process ends
                    case Wire.Spin: while (true) Thread.SpinWait(1000);
                    case Wire.Allocate:
                        var keep = new List<byte[]>();
                        while (true) { var b = new byte[16 << 20]; Array.Fill(b, (byte)1); keep.Add(b); }
                    case Wire.Stacks: Wire.Write(output, Wire.Ok, Stacks.Describe()); break;
                    case Wire.Echo: Wire.Write(output, Wire.Ok, req.Payload); break;
                    case Wire.Quit: session?.Dispose(); Wire.Write(output, Wire.Ok, ""); return 0;
                    default: Wire.Write(output, Wire.Failed, "unknown op"); break;
                }
            }
            catch (Exception ex)
            {
                Wire.Write(output, Wire.Failed, ex.GetType().Name + ": " + ex.Message);
            }
        }
        return 0;
    }

    static int Recurse(int n) { Span<byte> pad = stackalloc byte[256]; pad[0] = (byte)n; return Recurse(n + 1) + pad[0]; }
}

/// <summary>The app's side of one parse process: starts it, sends one request at a time, and treats the end of the
/// stream (the process died) or a missed time limit (it is then ended) as the answer "the engine is gone".</summary>
sealed class EngineClient : IDisposable
{
    public Process Process { get; }
    private readonly Stream _in, _out;
    public TimeSpan Limit { get; set; } = TimeSpan.FromSeconds(30);

    private EngineClient(Process p) { Process = p; _in = p.StandardInput.BaseStream; _out = p.StandardOutput.BaseStream; }

    public static EngineClient Start(int heapMb)
    {
        var self = Environment.ProcessPath!;
        var psi = new ProcessStartInfo(self) { RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false };
        if (Path.GetFileNameWithoutExtension(self) == "dotnet") psi.ArgumentList.Add(typeof(EngineClient).Assembly.Location);
        psi.ArgumentList.Add("engine");
        if (heapMb > 0) psi.Environment["DOTNET_GCHeapHardLimit"] = "0x" + ((long)heapMb << 20).ToString("X");
        psi.Environment["DOTNET_DbgEnableMiniDump"] = "0";
        psi.Environment["DOTNET_EnableCrashReport"] = "0";
        psi.Environment["DOTNET_gcServer"] = "0";
        var p = Process.Start(psi)!;
        p.ErrorDataReceived += (_, e) => { if (e.Data is { Length: > 0 } d) LastError = d; };
        p.BeginErrorReadLine();
        return new EngineClient(p);
    }

    public static string? LastError;

    /// <summary>Ok text, or throws EngineGone (died, or ended for passing the time limit) / EngineFailed.</summary>
    public byte[] Call(byte op, string arg = "")
    {
        Wire.Write(_in, op, arg);
        var read = Task.Run(() => Wire.Read(_out));
        if (!read.Wait(Limit))
        {
            try { Process.Kill(entireProcessTree: true); } catch { }
            throw new EngineGone($"passed its time limit ({Limit.TotalSeconds:0} s) and was ended");
        }
        if (read.Result is not { } r)
        {
            Process.WaitForExit(2000);
            throw new EngineGone($"ended (exit code {(Process.HasExited ? Process.ExitCode : -1)})");
        }
        if (r.Code != Wire.Ok) throw new EngineFailed(Encoding.UTF8.GetString(r.Payload));
        return r.Payload;
    }

    public string CallText(byte op, string arg = "") => Encoding.UTF8.GetString(Call(op, arg));

    public long RssKb()
    {
        try
        {
            if (OperatingSystem.IsLinux())
                foreach (var line in File.ReadLines($"/proc/{Process.Id}/status"))
                    if (line.StartsWith("VmRSS:")) return long.Parse(line.Split(' ', StringSplitOptions.RemoveEmptyEntries)[1]);
            Process.Refresh();
            return Process.WorkingSet64 / 1024;
        }
        catch { return -1; }
    }

    public void Dispose()
    {
        try { if (!Process.HasExited) { Wire.Write(_in, Wire.Quit, ""); Process.WaitForExit(2000); } } catch { }
        try { if (!Process.HasExited) Process.Kill(); } catch { }
        Process.Dispose();
    }
}

sealed class EngineGone(string m) : Exception(m);
sealed class EngineFailed(string m) : Exception(m);
