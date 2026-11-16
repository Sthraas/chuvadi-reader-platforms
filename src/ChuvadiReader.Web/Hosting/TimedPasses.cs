namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// The loop behind every timer pass that serves the whole portal (session expiry, worker supervision,
/// housekeeping). WT-24: such a loop must outlive anything one pass does. Only the host stopping ends it; a
/// pass that throws — including a cancellation that is not the host's, which a call into a worker that is
/// just stopping produces — is logged and the next pass runs as usual. A pass that takes long is logged too.
/// </summary>
public static class TimedPasses
{
    /// <summary>A pass longer than this is worth a line in the log.</summary>
    public static readonly TimeSpan Slow = TimeSpan.FromSeconds(5);

    public static async Task RunAsync(string name, TimeSpan every, TimeProvider time, Func<Task> pass, ILogger log, CancellationToken stopping)
    {
        ArgumentNullException.ThrowIfNull(time);
        ArgumentNullException.ThrowIfNull(pass);
        ArgumentNullException.ThrowIfNull(log);
        using var timer = new PeriodicTimer(every, time);
        while (true)
        {
            try
            {
                if (!await timer.WaitForNextTickAsync(stopping).ConfigureAwait(false))
                {
                    return;
                }
            }
            catch (OperationCanceledException)
            {
                return; // the host is stopping
            }

            await OnceAsync(name, time, pass, log, stopping).ConfigureAwait(false);
        }
    }

    /// <summary>One pass, with what <see cref="RunAsync"/> promises: it never throws.</summary>
    public static async Task OnceAsync(string name, TimeProvider time, Func<Task> pass, ILogger log, CancellationToken stopping)
    {
        ArgumentNullException.ThrowIfNull(time);
        ArgumentNullException.ThrowIfNull(pass);
        ArgumentNullException.ThrowIfNull(log);
        var started = time.GetTimestamp();
        try
        {
            await pass().ConfigureAwait(false);
        }
#pragma warning disable CA1031 // by design: whatever one pass throws, the loop that serves everyone goes on
        catch (Exception ex)
#pragma warning restore CA1031
        {
            if (!stopping.IsCancellationRequested)
            {
                log.LogError(ex, "{Name} pass failed; the next one runs as usual", name);
            }
        }

        var took = time.GetElapsedTime(started);
        if (took > Slow && !stopping.IsCancellationRequested)
        {
            log.LogWarning("{Name} pass took {Seconds:0.0} s", name, took.TotalSeconds);
        }
    }
}
