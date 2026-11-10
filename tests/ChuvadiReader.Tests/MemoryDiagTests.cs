using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Tests;

// DIAGNOSTIC BRANCH ONLY.
[Collection(nameof(MemoryAfterCloseTests))]
public sealed class MemoryDiagTests
{
    public MemoryDiagTests()
    {
        MemoryRelief.Settle = TimeSpan.Zero;
        MemoryRelief.FollowUp = TimeSpan.Zero;
        MemoryRelief.MinGap = TimeSpan.Zero;
        (MemoryRelief.Last ?? Task.CompletedTask).Wait(TimeSpan.FromSeconds(30));
        MemoryRelief.ResetForTests();
        MemoryRelief.MinGap = TimeSpan.Zero;
    }

    private static (long Live, long Committed) Measure()
    {
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        GC.WaitForPendingFinalizers();
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        return (GC.GetTotalMemory(false), GC.GetGCMemoryInfo().TotalCommittedBytes);
    }

    private static string Where() =>
        $"t{Environment.CurrentManagedThreadId}{(Thread.CurrentThread.IsThreadPoolThread ? "p" : "x")}/{SynchronizationContext.Current?.GetType().Name ?? "none"}";

    [Fact]
    public async Task MemoryDiag()
    {
        var path = MemoryAfterCloseTests.HeavyPageForDiag();
        MemoryRelief.ResetForTests();
        var before = Measure();
        var start = Where();

        var drawnChars = await OpenDrawClose(path);
        var afterHelper = Where();
        await Task.Yield();
        await (MemoryRelief.Last ?? Task.CompletedTask).WaitAsync(TimeSpan.FromSeconds(30));
        await Task.Yield();
        var after = Measure();
        var weak = ChuvadiPdfSession.LastAnsweredForDiag;
        var a1 = weak?.IsAlive;
        var draining1 = ChuvadiPdfSession.DrainingForDiag;
        await Task.Delay(300);
        var m2 = Measure(); var a2 = weak?.IsAlive;
        await Task.Delay(3000);
        var m3 = Measure(); var a3 = weak?.IsAlive;

        const long mb = 1024 * 1024;
        File.AppendAllText(Environment.GetEnvironmentVariable("CHVD_DIAG") ?? Path.Combine(Path.GetTempPath(), "chvd-diag.txt"),
            $"cores={Environment.ProcessorCount} server={System.Runtime.GCSettings.IsServerGC} chars={drawnChars / mb}M live {before.Live / mb}->{after.Live / mb}->{m2.Live / mb}->{m3.Live / mb} pageAlive {a1}/{a2}/{a3} drainersAtMeasure={draining1} start={start} afterHelper={afterHelper} cont={s_cont} now={Where()}\n");
        Assert.True(after.Live - before.Live < 16 * mb, $"live memory after close: {before.Live / mb} -> {after.Live / mb} MB");
    }

    private static string s_cont = "";

    private static async Task<long> OpenDrawClose(string path)
    {
        var session = await new ChuvadiReader.Core.Reader.ChuvadiPdfReader().OpenAsync(path, Path.GetFileName(path));
        var chars = (await session.RenderPageSvgAsync(0)).Length;
        s_cont = Where();
        session.Dispose();
        return chars;
    }
}
