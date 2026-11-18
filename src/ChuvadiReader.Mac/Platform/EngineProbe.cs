#pragma warning disable CA1416 // System.Diagnostics.Process on Mac Catalyst: whether it works is what this proves
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// D-198 / D-202 (C1): proof, on the runners, of what the parse engine needs on a Mac before any of it is built —
/// that the app can start its own executable a second time as a child that never starts UIKit, talk to it over pipes,
/// end it, and what Mono does with a heap cap (<c>MONO_GC_PARAMS=max-heap-size</c>), a deep stack and a stack
/// overflow. Smoke only (<c>CHUVADI_SMOKE_ENGINE=1</c>); nothing here is used by the app itself.
/// The child side runs from <see cref="Program"/> before UIApplication.Main when the first argument is
/// <see cref="Switch"/>.
/// </summary>
internal static unsafe class EngineProbe
{
    public const string Switch = "--chvd-engine-probe";

    // ---- child -------------------------------------------------------------------------------------------------

    public static int RunChild(string[] args)
    {
        var mode = args.Length > 1 ? args[1] : "hello";
        Say($"ready pid={Environment.ProcessId} mode={mode} runtime=\"{RuntimeInformation.FrameworkDescription}\" arch={RuntimeInformation.ProcessArchitecture}"
            + $" gcparams=\"{Environment.GetEnvironmentVariable("MONO_GC_PARAMS") ?? ""}\" gcavail={GC.GetGCMemoryInfo().TotalAvailableMemoryBytes / 1048576}MB");
        try
        {
            switch (mode)
            {
                case "hello":
                    // The child's Console: on Mac Catalyst, Console.Out goes to the system log (stderr) and
                    // Console.In is not supported — shown by this mode.
                    var line = Console.In.ReadLine();
                    Say("echo " + line);
                    return 0;
                case "wire-pipe":
                    return WirePipe(args);
                case "wire-socket":
                    return WireSocket(args);
                case "alloc":
                    return Alloc();
                case "deep16":
                    return Deep(16 * 1024 * 1024, "thread-16MB");
                case "deepdefault":
                    return Deep(0, "thread-default");
                case "deeppool":
                    return DeepPool();
                case "deepmain":
                    Say("deep main " + Depth(TargetBytes));
                    return 0;
                case "overflow":
                    var t = new Thread(() => Endless(0), 16 * 1024 * 1024);
                    t.Start();
                    t.Join();
                    Say("overflow returned (not expected)");
                    return 0;
                case "hang":
                    while (true) { Thread.Sleep(1000); }
                default:
                    Say("unknown mode");
                    return 2;
            }
        }
        catch (Exception ex)
        {
            Say("caught " + ex.GetType().FullName + ": " + ex.Message);
            return 4;
        }
    }

    /// <summary>Anonymous pipes the parent made inheritable: args[2] is the parent→child end, args[3] child→parent.</summary>
    private static int WirePipe(string[] args)
    {
        using var input = new System.IO.Pipes.AnonymousPipeClientStream(System.IO.Pipes.PipeDirection.In, args[2]);
        using var output = new System.IO.Pipes.AnonymousPipeClientStream(System.IO.Pipes.PipeDirection.Out, args[3]);
        return Serve(input, output, "pipe");
    }

    /// <summary>A Unix-domain socket the parent listens on: args[2] is its path.</summary>
    private static int WireSocket(string[] args)
    {
        using var socket = new System.Net.Sockets.Socket(System.Net.Sockets.AddressFamily.Unix, System.Net.Sockets.SocketType.Stream, System.Net.Sockets.ProtocolType.Unspecified);
        socket.Connect(new System.Net.Sockets.UnixDomainSocketEndPoint(args[2]));
        using var stream = new System.Net.Sockets.NetworkStream(socket, ownsSocket: false);
        return Serve(stream, stream, "socket");
    }

    /// <summary>"ready", then: a ping line → "pong", a length-prefixed block → its length back, and EOF → exit 0.</summary>
    private static int Serve(Stream input, Stream output, string kind)
    {
        var w = new StreamWriter(output) { AutoFlush = true };
        w.WriteLine("PROBE ready " + kind);
        var r = new BinaryReader(input);
        var ping = ReadLine(input);
        w.WriteLine("PROBE pong " + ping);
        var len = r.ReadInt32();
        var buffer = new byte[1 << 20];
        long got = 0;
        while (got < len)
        {
            var n = input.Read(buffer, 0, (int)Math.Min(buffer.Length, len - got));
            if (n == 0) { break; }
            got += n;
        }

        w.WriteLine("PROBE got " + got);
        var tail = input.Read(buffer, 0, 1); // the parent closes its end: 0 means end of stream
        Say("wire " + kind + " end of stream=" + (tail == 0 ? 1 : 0));
        return tail == 0 ? 0 : 5;
    }

    private static string ReadLine(Stream s)
    {
        var bytes = new List<byte>();
        int b;
        while ((b = s.ReadByte()) >= 0 && b != '\n') { bytes.Add((byte)b); }
        return System.Text.Encoding.UTF8.GetString(bytes.ToArray());
    }

    private static void Say(string line)
    {
        Console.Out.WriteLine("PROBE " + line);
        Console.Out.Flush();
    }

    /// <summary>16 MB arrays, every page touched, until out of memory or the stop mark (so an uncapped run ends).</summary>
    private static int Alloc()
    {
        var stopMb = int.TryParse(Environment.GetEnvironmentVariable("CHUVADI_PROBE_STOP_MB"), out var s) ? s : 1024;
        var held = new List<byte[]>();
        var mb = 0;
        var clock = Stopwatch.StartNew();
        try
        {
            while (mb < stopMb)
            {
                var block = new byte[16 * 1024 * 1024];
                for (var i = 0; i < block.Length; i += 4096)
                {
                    block[i] = 1;
                }

                held.Add(block);
                mb += 16;
                if (mb % 128 == 0)
                {
                    Say($"alloc {mb}MB rss={Environment.WorkingSet / 1048576}MB");
                }
            }

            Say($"alloc reached the stop mark {mb}MB without running out, rss={Environment.WorkingSet / 1048576}MB, {clock.ElapsedMilliseconds}ms");
            return 0;
        }
        catch (OutOfMemoryException)
        {
            var at = mb;
            held.Clear();
            GC.Collect();
            Say($"alloc out of memory at {at}MB after {clock.ElapsedMilliseconds}ms; still running after it (rss={Environment.WorkingSet / 1048576}MB)");
            return 3;
        }
    }

    // About 10 MB of stack: more than the usual 512 KB–8 MB defaults, less than the engine's stated 16 MB.
    private const long TargetBytes = 10L * 1024 * 1024;

    private static int Deep(int stack, string what)
    {
        string? result = null;
        var t = stack > 0 ? new Thread(() => result = Depth(TargetBytes), stack) : new Thread(() => result = Depth(TargetBytes));
        t.Start();
        t.Join();
        Say($"deep {what} {result}");
        return 0;
    }

    private static int DeepPool()
    {
        string? result = null;
        using var done = new ManualResetEventSlim();
        ThreadPool.QueueUserWorkItem(_ => { result = Depth(TargetBytes); done.Set(); });
        done.Wait();
        Say("deep thread-pool " + result);
        return 0;
    }

    private static long _top;

    /// <summary>Recurses until <paramref name="bytes"/> of stack are in use, measured by the address of a local.</summary>
    private static string Depth(long bytes)
    {
        byte here;
        _top = (long)&here;
        var frames = Down(bytes, 0);
        return $"ok {bytes / 1048576}MB used in {frames} frames";
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int Down(long bytes, int frames)
    {
        var pad = stackalloc byte[64];
        pad[0] = (byte)frames;
        return _top - (long)pad >= bytes ? frames + pad[0] - pad[0] : Down(bytes, frames + 1);
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int Endless(int n)
    {
        var pad = stackalloc byte[64];
        pad[0] = (byte)n;
        return Endless(n + 1) + pad[0];
    }

    // ---- parent ------------------------------------------------------------------------------------------------

    /// <summary>Runs every probe in a child of this app and logs what happened. Called from the smoke, off the main thread.</summary>
    public static void RunAll()
    {
        var self = Environment.ProcessPath ?? string.Empty;
        MacSmoke.Log("engine-probe self=" + Path.GetFileName(self) + " exists=" + (File.Exists(self) ? 1 : 0));
        Run(self, "hello", null, 30);
        Wire(self, socket: false);
        Wire(self, socket: true);
        Run(self, "alloc", "max-heap-size=256m", 120);
        Run(self, "alloc", null, 120);                 // no cap: stops itself at 1024 MB
        Run(self, "deep16", null, 30);
        Run(self, "deepdefault", null, 30);
        Run(self, "deeppool", null, 30);
        Run(self, "deepmain", null, 30);
        Run(self, "overflow", null, 60);
        Run(self, "hang", null, 3);                    // the parent's own time limit ends it
        MacSmoke.Log("engine-probe done");
    }

    /// <summary>The engine's wire: start the child, wait for "ready", ping, send 8 MB, close, and time each part.</summary>
    private static void Wire(string self, bool socket)
    {
        var tag = socket ? "wire-socket" : "wire-pipe";
        try
        {
            var info = new ProcessStartInfo(self) { UseShellExecute = false, RedirectStandardError = true };
            info.ArgumentList.Add(Switch);
            info.ArgumentList.Add(tag);
            info.Environment.Remove("CHUVADI_SMOKE");
            info.Environment.Remove("CHUVADI_SMOKE_ENGINE");
            Stream toChild, fromChild;
            System.IO.Pipes.AnonymousPipeServerStream? outPipe = null, inPipe = null;
            System.Net.Sockets.Socket? listener = null;
            string? socketPath = null;
            if (socket)
            {
                socketPath = Path.Combine(Path.GetTempPath(), "chvd-" + Environment.ProcessId + ".sock");
                File.Delete(socketPath);
                listener = new System.Net.Sockets.Socket(System.Net.Sockets.AddressFamily.Unix, System.Net.Sockets.SocketType.Stream, System.Net.Sockets.ProtocolType.Unspecified);
                listener.Bind(new System.Net.Sockets.UnixDomainSocketEndPoint(socketPath));
                listener.Listen(1);
                info.ArgumentList.Add(socketPath);
            }
            else
            {
                outPipe = new System.IO.Pipes.AnonymousPipeServerStream(System.IO.Pipes.PipeDirection.Out, HandleInheritability.Inheritable);
                inPipe = new System.IO.Pipes.AnonymousPipeServerStream(System.IO.Pipes.PipeDirection.In, HandleInheritability.Inheritable);
                info.ArgumentList.Add(outPipe.GetClientHandleAsString());
                info.ArgumentList.Add(inPipe.GetClientHandleAsString());
            }

            var clock = Stopwatch.StartNew();
            using var child = Process.Start(info) ?? throw new InvalidOperationException("Process.Start returned null");
            var errors = new List<string>();
            child.ErrorDataReceived += (_, e) => { if (e.Data is not null) { lock (errors) { errors.Add(e.Data); } } };
            child.BeginErrorReadLine();
            if (socket)
            {
                var accepted = listener!.Accept();
                toChild = fromChild = new System.Net.Sockets.NetworkStream(accepted, ownsSocket: true);
            }
            else
            {
                outPipe!.DisposeLocalCopyOfClientHandle();
                inPipe!.DisposeLocalCopyOfClientHandle();
                toChild = outPipe;
                fromChild = inPipe;
            }

            var ready = ReadLine(fromChild);
            var readyMs = clock.ElapsedMilliseconds;
            var w = new StreamWriter(toChild) { AutoFlush = true };
            var t0 = clock.Elapsed;
            w.WriteLine("ping");
            var pong = ReadLine(fromChild);
            var pingUs = (clock.Elapsed - t0).TotalMilliseconds * 1000;
            var block = new byte[8 * 1024 * 1024];
            var t1 = clock.Elapsed;
            toChild.Write(BitConverter.GetBytes(block.Length));
            toChild.Write(block);
            toChild.Flush();
            var got = ReadLine(fromChild);
            var mbps = 8 / Math.Max((clock.Elapsed - t1).TotalSeconds, 1e-6);
            var t2 = clock.Elapsed;
            toChild.Dispose();                      // the child sees end of stream and must exit by itself
            if (!ReferenceEquals(toChild, fromChild)) { fromChild.Dispose(); }
            var exited = child.WaitForExit(10000);
            var endMs = (clock.Elapsed - t2).TotalMilliseconds;
            if (!exited) { child.Kill(); }
            child.WaitForExit();
            MacSmoke.Log($"engine-probe {tag}: ready={readyMs}ms ({ready}) ping={pingUs:0}us ({pong}) 8MB={mbps:0}MB/s ({got}) exit-after-close={(exited ? endMs.ToString("0") + "ms code=" + child.ExitCode : "no (killed)")}");
            lock (errors) { foreach (var l in errors.Take(4)) { MacSmoke.Log($"engine-probe {tag} err: {l}"); } }
            listener?.Dispose();
            if (socketPath is not null) { File.Delete(socketPath); }
        }
        catch (Exception ex)
        {
            MacSmoke.Log($"engine-probe {tag}: failed: {ex.GetType().FullName}: {ex.Message}");
        }
    }

    private static void Run(string self, string mode, string? gcParams, int seconds)
    {
        var tag = mode + (gcParams is null ? string.Empty : " gc=" + gcParams);
        try
        {
            var info = new ProcessStartInfo(self)
            {
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            info.ArgumentList.Add(Switch);
            info.ArgumentList.Add(mode);
            info.Environment.Remove("CHUVADI_SMOKE");          // the child must never act as the smoke app
            info.Environment.Remove("CHUVADI_SMOKE_ENGINE");
            info.Environment.Remove("MONO_GC_PARAMS");
            if (gcParams is not null)
            {
                info.Environment["MONO_GC_PARAMS"] = gcParams;
            }

            var clock = Stopwatch.StartNew();
            using var child = Process.Start(info) ?? throw new InvalidOperationException("Process.Start returned null");
            long firstLineMs = -1;
            var lines = new List<string>();
            var errors = new List<string>();
            child.OutputDataReceived += (_, e) =>
            {
                if (e.Data is null) { return; }
                if (firstLineMs < 0) { firstLineMs = clock.ElapsedMilliseconds; }
                lock (lines) { lines.Add(e.Data); }
            };
            child.ErrorDataReceived += (_, e) => { if (e.Data is not null) { lock (errors) { errors.Add(e.Data); } } };
            child.BeginOutputReadLine();
            child.BeginErrorReadLine();
            if (mode == "hello")
            {
                child.StandardInput.WriteLine("ping-" + Environment.ProcessId);
                child.StandardInput.Flush();
            }

            long peakMb = 0;
            var ended = false;
            while (clock.Elapsed < TimeSpan.FromSeconds(seconds))
            {
                if (child.WaitForExit(200)) { ended = true; break; }
                try { child.Refresh(); peakMb = Math.Max(peakMb, child.WorkingSet64 / 1048576); } catch { }
            }

            if (!ended)
            {
                child.Kill(entireProcessTree: true);
                child.WaitForExit(5000);
            }

            child.WaitForExit(); // flush the async readers
            MacSmoke.Log($"engine-probe {tag}: started={firstLineMs}ms exit={(ended ? child.ExitCode.ToString() : "killed-at-limit")} total={clock.ElapsedMilliseconds}ms peak-seen={peakMb}MB");
            lock (lines) { foreach (var l in lines.TakeLast(6)) { MacSmoke.Log($"engine-probe {tag} out: {l}"); } }
            lock (errors) { foreach (var l in errors.Take(8)) { MacSmoke.Log($"engine-probe {tag} err: {l}"); } }
        }
        catch (Exception ex)
        {
            MacSmoke.Log($"engine-probe {tag}: could not start: {ex.GetType().FullName}: {ex.Message}");
        }
    }
}
