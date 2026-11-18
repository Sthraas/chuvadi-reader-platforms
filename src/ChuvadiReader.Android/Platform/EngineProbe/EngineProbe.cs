// D-202 measurement probe (test-only). Compiled ONLY with -p:ChuvadiEngineProbe=true; never in a shipped build.
//
// Measures, on a device or emulator, what Foundation's parse-process design (D1, E2) costs on Android:
//   - how long a second process of the app (android:process=":engine") takes to start .NET and answer;
//   - its memory;
//   - how pages could travel (a pipe the engine hands back over Binder; Binder itself is capped near 1 MB);
//   - what happens on a stack overflow and on runaway allocation in the engine, and whether the app survives.
//
// Driven by docs/android/ci/engine_probe.py through EngineProbeActivity (am start -n …/in.chuvadi.reader.EngineProbeActivity
// --es cmd <start|pipe|alloc|overflow-thread|overflow-binder|stop>). Every result is a log line, tag ChuvadiProbe.
using System.Diagnostics.CodeAnalysis;
using global::Android.App;
using global::Android.Content;
using global::Android.OS;
using global::Android.Runtime;
using AProcess = global::Android.OS.Process;

namespace ChuvadiReader.Android.Platform.EngineProbe;

internal static class Probe
{
    public const string Tag = "ChuvadiProbe";
    public const string EngineSuffix = ":engine";

    /// <summary>ElapsedRealtime of the first managed code in this process (set by MainApplication's constructor).</summary>
    public static long RuntimeAt;

    /// <summary>ElapsedRealtime when MainApplication.OnCreate returned (MAUI set up, or skipped in the engine).</summary>
    public static long AppCreatedAt;

    public static bool InEngineProcess => global::Android.App.Application.ProcessName?.EndsWith(EngineSuffix, StringComparison.Ordinal) == true;

    public static long Now => SystemClock.ElapsedRealtime();

    public static void Log(string line) => global::Android.Util.Log.Info(Tag, line);

    public static long RssKb()
    {
        foreach (var line in File.ReadLines("/proc/self/status"))
        {
            if (line.StartsWith("VmRSS:", StringComparison.Ordinal))
            {
                return long.Parse(line[6..].Trim().Split(' ')[0], System.Globalization.CultureInfo.InvariantCulture);
            }
        }

        return -1;
    }
}

/// <summary>A minimal MAUI application for the engine process: no window, no Blazor, no Chuvadi services.</summary>
internal sealed class EngineApp : Microsoft.Maui.Controls.Application
{
}

/// <summary>The engine: a bound service in its own process, answering over a hand-written Binder.</summary>
[Service(Name = "in.chuvadi.reader.EngineProbeService", Process = Probe.EngineSuffix, Exported = false)]
public sealed class EngineProbeService : Service
{
    private long _createdAt;

    public override void OnCreate()
    {
        _createdAt = Probe.Now;
        base.OnCreate();
    }

    public override IBinder OnBind(Intent? intent) => new EngineBinder(_createdAt, Probe.Now);
}

internal sealed class EngineBinder(long createdAt, long boundAt) : Binder
{
    public const int Ping = 1, Pipe = 2, Alloc = 3, OverflowThread = 4, OverflowBinder = 5;

    protected override bool OnTransact(int code, Parcel data, Parcel? reply, int flags)
    {
        switch (code)
        {
            case Ping:
                reply!.WriteInt(AProcess.MyPid());
                reply.WriteLong(AProcess.StartElapsedRealtime);
                reply.WriteLong(Probe.RuntimeAt);
                reply.WriteLong(Probe.AppCreatedAt);
                reply.WriteLong(createdAt);
                reply.WriteLong(boundAt);
                reply.WriteLong(Probe.Now);
                reply.WriteLong(Probe.RssKb());
                reply.WriteLong(GC.GetTotalMemory(false) / 1024);
                return true;

            case Pipe:
                {
                    var megabytes = data.ReadInt();
                    var ends = ParcelFileDescriptor.CreatePipe()!;
                    var write = ends[1];
                    new Thread(() =>
                    {
                        using var stream = new ParcelFileDescriptor.AutoCloseOutputStream(write);
                        var chunk = new byte[64 * 1024];
                        for (var i = 0; i < megabytes * 16; i++)
                        {
                            chunk[0] = (byte)i;
                            stream.Write(chunk, 0, chunk.Length);
                        }
                    }) { IsBackground = true }.Start();
                    reply!.WriteInt(1);
                    ends[0].WriteToParcel(reply, ParcelableWriteFlags.ReturnValue);
                    ends[0].Close();
                    return true;
                }

            case Alloc:
                {
                    var held = new List<byte[]>();
                    var outcome = "no limit reached at 4096 MB";
                    try
                    {
                        while (held.Count < 4096 / 16)
                        {
                            var block = new byte[16 * 1024 * 1024];
                            Array.Fill(block, (byte)1);   // touch it, so it is really resident
                            held.Add(block);
                            if (held.Count % 8 == 0)
                            {
                                Probe.Log($"alloc engine holds {held.Count * 16} MB, rss {Probe.RssKb() / 1024} MB");
                            }
                        }
                    }
                    catch (OutOfMemoryException)
                    {
                        outcome = "OutOfMemoryException caught";
                    }

                    var mb = held.Count * 16;
                    held.Clear();
                    GC.Collect();
                    reply!.WriteString($"{outcome}; held {mb} MB");
                    return true;
                }

            case OverflowThread:
                {
                    string result;
                    var thread = new Thread(() =>
                    {
                        try
                        {
                            Probe.Log("overflow-thread: recursing on a new thread (default stack)");
                            Recurse(0);
                            result = "returned";
                        }
                        catch (Exception ex)
                        {
                            result = "caught " + ex.GetType().Name;
                        }
                    });
                    result = "?";
                    thread.Start();
                    thread.Join();
                    reply!.WriteString(result);
                    return true;
                }

            case OverflowBinder:
                {
                    string result;
                    try
                    {
                        Probe.Log("overflow-binder: recursing on the Binder thread");
                        Recurse(0);
                        result = "returned";
                    }
                    catch (Exception ex)
                    {
                        result = "caught " + ex.GetType().Name;
                    }

                    reply!.WriteString(result);
                    return true;
                }

            default:
                return base.OnTransact(code, data, reply, flags);
        }
    }

    [SuppressMessage("Major Bug", "S2190:Recursion should not be infinite", Justification = "The point of the probe.")]
    private static int Recurse(int depth)
    {
        Span<byte> pad = stackalloc byte[256];
        pad[depth % 256] = (byte)depth;
        return Recurse(depth + 1) + pad[0];
    }
}

/// <summary>
/// The app side, in the main process: binds the engine, times it, and runs one command per launch.
/// A transparent activity, started by the test script (exported only in this test build).
/// </summary>
[Activity(Name = "in.chuvadi.reader.EngineProbeActivity", Exported = true, Theme = "@android:style/Theme.Translucent.NoTitleBar",
    NoHistory = true, ExcludeFromRecents = true, TaskAffinity = "in.chuvadi.reader.probe")]
public sealed class EngineProbeActivity : Activity
{
    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        var cmd = Intent?.GetStringExtra("cmd") ?? "start";
        var arg = Intent?.GetIntExtra("arg", 0) ?? 0;
        Finish();
        new Thread(() =>
        {
            try
            {
                EngineClient.Run(cmd, arg);
            }
            catch (Exception ex)
            {
                Probe.Log($"{cmd} client error {ex.GetType().Name}: {ex.Message}");
            }
        }) { IsBackground = true }.Start();
    }
}

internal static class EngineClient
{
    private static Connection? _connection;

    public static void Run(string cmd, int arg)
    {
        switch (cmd)
        {
            case "start":
                Start();
                break;
            case "stop":
                Stop();
                break;
            case "pipe":
                PipeRun(arg <= 0 ? 64 : arg);
                break;
            case "alloc":
                Call("alloc", EngineBinder.Alloc, p => p.ReadString());
                break;
            case "overflow-thread":
                Call("overflow-thread", EngineBinder.OverflowThread, p => p.ReadString());
                break;
            case "overflow-binder":
                Call("overflow-binder", EngineBinder.OverflowBinder, p => p.ReadString());
                break;
            default:
                Probe.Log($"{cmd} unknown");
                break;
        }
    }

    private static void Start()
    {
        Stop();
        var context = global::Android.App.Application.Context;
        var connection = new Connection();
        var bindAt = Probe.Now;
        var bound = context.BindService(new Intent(context, typeof(EngineProbeService)), connection, Bind.AutoCreate);
        if (!bound || !connection.Connected.Wait(TimeSpan.FromSeconds(30)))
        {
            Probe.Log($"start failed: bound {bound}");
            return;
        }

        var connectedAt = connection.ConnectedAt;
        _connection = connection;
        using var data = Parcel.Obtain();
        using var reply = Parcel.Obtain();
        connection.Binder!.Transact(EngineBinder.Ping, data, reply, 0);
        var answeredAt = Probe.Now;
        var pid = reply.ReadInt();
        var forkAt = reply.ReadLong();
        var runtimeAt = reply.ReadLong();
        var appAt = reply.ReadLong();
        var serviceAt = reply.ReadLong();
        var boundAt = reply.ReadLong();
        var engineNow = reply.ReadLong();
        var rssKb = reply.ReadLong();
        var heapKb = reply.ReadLong();
        connection.EnginePid = pid;
        _ = engineNow;
        // All in ms after bindService was called (ElapsedRealtime is the same clock in both processes).
        Probe.Log(
            $"start pid {pid} fork {forkAt - bindAt} runtime {runtimeAt - bindAt} app {appAt - bindAt} service {serviceAt - bindAt} " +
            $"bound {boundAt - bindAt} connected {connectedAt - bindAt} answered {answeredAt - bindAt} rssKb {rssKb} heapKb {heapKb} " +
            $"appRssKb {Probe.RssKb()}");
    }

    private static void Stop()
    {
        if (_connection is not { } c)
        {
            return;
        }

        _connection = null;
        try
        {
            global::Android.App.Application.Context.UnbindService(c);
        }
        catch (Java.Lang.IllegalArgumentException)
        {
            // already gone
        }

        if (c.EnginePid > 0)
        {
            AProcess.KillProcess(c.EnginePid);   // same app, same user: allowed
        }

        Probe.Log($"stop pid {c.EnginePid}");
    }

    private static void PipeRun(int megabytes)
    {
        if (_connection is not { Binder: { } binder })
        {
            Probe.Log("pipe not started");
            return;
        }

        using var data = Parcel.Obtain();
        using var reply = Parcel.Obtain();
        data.WriteInt(megabytes);
        var t0 = Probe.Now;
        binder.Transact(EngineBinder.Pipe, data, reply, 0);
        reply.ReadInt();
        var fd = (ParcelFileDescriptor)ParcelFileDescriptor.Creator!.CreateFromParcel(reply)!;
        using var stream = new ParcelFileDescriptor.AutoCloseInputStream(fd);
        var buffer = new byte[64 * 1024];
        long total = 0;
        int n;
        while ((n = stream.Read(buffer, 0, buffer.Length)) > 0)
        {
            total += n;
        }

        var ms = Math.Max(1, Probe.Now - t0);
        Probe.Log($"pipe {total / (1024 * 1024)} MB in {ms} ms = {total / 1024.0 / 1024.0 / (ms / 1000.0):F0} MB/s");
    }

    private static void Call(string name, int code, Func<Parcel, string?> read)
    {
        if (_connection is not { Binder: { } binder } c)
        {
            Probe.Log($"{name} not started");
            return;
        }

        using var data = Parcel.Obtain();
        using var reply = Parcel.Obtain();
        var t0 = Probe.Now;
        try
        {
            binder.Transact(code, data, reply, 0);
            Probe.Log($"{name} answered in {Probe.Now - t0} ms: {read(reply)}");
        }
        catch (Exception ex)
        {
            Probe.Log($"{name} engine gone after {Probe.Now - t0} ms: {ex.GetType().Name}; died notice {c.Died.Wait(TimeSpan.FromSeconds(5))}; app pid {AProcess.MyPid()} alive");
        }
    }

    private sealed class Connection : Java.Lang.Object, IServiceConnection, IBinderDeathRecipient
    {
        public readonly ManualResetEventSlim Connected = new();
        public readonly ManualResetEventSlim Died = new();
        public long ConnectedAt;
        public IBinder? Binder;
        public int EnginePid;

        public void OnServiceConnected(ComponentName? name, IBinder? service)
        {
            ConnectedAt = Probe.Now;
            Binder = service;
            service?.LinkToDeath(this, 0);
            Connected.Set();
        }

        public void OnServiceDisconnected(ComponentName? name) => Probe.Log("engine disconnected (onServiceDisconnected)");

        public void BinderDied()
        {
            Probe.Log("engine died (binderDied)");
            Died.Set();
        }
    }
}
