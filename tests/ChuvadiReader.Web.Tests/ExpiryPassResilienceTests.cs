using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net;
using System.Security.Claims;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Hosting.Workers;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>Keeps what is logged, for tests that must see a line.</summary>
public sealed class ListLogger<T> : ILogger<T>
{
    public ConcurrentQueue<(LogLevel Level, string Text)> Lines { get; } = new();

    public IDisposable? BeginScope<TState>(TState state)
        where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        => Lines.Enqueue((logLevel, formatter(state, exception)));
}

/// <summary>
/// WT-24: the session-expiry pass serves everyone, so no one session may hold or end it. A session whose
/// worker never answers, and one whose worker stops in the middle of the call (which surfaces as a
/// cancellation), are logged and left behind; the others end in the same pass, and the next pass runs.
/// </summary>
public class ExpiryPassResilienceTests
{
    /// <summary>Tabs whose worker, for chosen sign-ins, never answers or stops mid-call.</summary>
    private sealed class TroubledTabs : ITabControl
    {
        public ConcurrentBag<string?> Ended { get; } = [];
        public ConcurrentBag<string?> Noticed { get; } = [];

        public async Task<int> EndAsync(string? sub, string? sid)
        {
            await TroubleAsync(sid).ConfigureAwait(false);
            Ended.Add(sid);
            return 1;
        }

        public async Task NoticeAsync(string sub, string? sid, ExpiryNotice? notice)
        {
            await TroubleAsync(sid).ConfigureAwait(false);
            Noticed.Add(sid);
        }

        public Task AnnounceAsync(MaintenanceNotice? notice) => Task.CompletedTask;

        private static Task TroubleAsync(string? sid) => sid switch
        {
            "never-answers" => new TaskCompletionSource().Task,                       // a stuck worker
            "stops-mid-call" => Task.FromException(new TaskCanceledException()),      // its connection closed under the call
            "breaks" => Task.FromException(new InvalidOperationException("boom")),
            _ => Task.CompletedTask,
        };
    }

    private readonly ManualTime _time = new();
    private readonly TroubledTabs _tabs = new();
    private readonly ListLogger<SessionClock> _log = new();
    private readonly PortalSessions _sessions;
    private readonly SessionClock _clock;

    public ExpiryPassResilienceTests()
    {
        var sangam = Options.Create(new SangamOptions());
        var portal = new PortalOptions();
        portal.Workers.ControlTimeout = TimeSpan.FromMilliseconds(300);
        _sessions = new PortalSessions(_time, sangam, _tabs);
        _clock = new SessionClock(_time, _sessions, _tabs, Options.Create(portal), sangam, _log);
    }

    private static ClaimsPrincipal User(string sid)
        => new(new ClaimsIdentity([new Claim("sub", "person-" + sid), new Claim("sid", sid)], "test"));

    [Fact]
    public async Task One_stuck_session_and_one_whose_worker_stops_mid_call_do_not_keep_the_others_from_ending()
    {
        string[] all = ["fine-1", "never-answers", "stops-mid-call", "breaks", "fine-2"];
        foreach (var sid in all)
        {
            _clock.Touch(User(sid));
        }

        _time.Advance(TimeSpan.FromMinutes(31));
        var watch = Stopwatch.StartNew();
        await _clock.TickAsync().WaitAsync(TimeSpan.FromSeconds(20)); // the pass returns, and never throws
        Assert.True(watch.Elapsed < TimeSpan.FromSeconds(10), $"the pass took {watch.Elapsed}");

        Assert.Equal(["fine-1", "fine-2"], _tabs.Ended.Order());
        foreach (var sid in all)
        {
            // Revoked before anything was awaited: every one of these cookies has stopped working.
            Assert.False(_sessions.IsValid("person-" + sid, sid, _time.GetUtcNow() - TimeSpan.FromHours(1)));
        }

        Assert.Equal(0, _clock.Count);
        var errors = _log.Lines.Where(l => l.Level == LogLevel.Error).Select(l => l.Text).ToList();
        Assert.Equal(3, errors.Count);
        Assert.Single(errors, e => e.Contains("took longer than", StringComparison.Ordinal));
        Assert.Equal(2, errors.Count(e => e.Contains("failed; the other sessions are not affected", StringComparison.Ordinal)));

        // And the clock goes on: someone who signs in afterwards still expires.
        _clock.Touch(User("later"));
        _time.Advance(TimeSpan.FromMinutes(31));
        await _clock.TickAsync().WaitAsync(TimeSpan.FromSeconds(20));
        Assert.Contains("later", _tabs.Ended);
    }

    [Fact]
    public async Task A_warning_that_cannot_be_delivered_does_not_keep_the_others_from_being_warned()
    {
        foreach (var sid in new[] { "never-answers", "stops-mid-call", "fine-1" })
        {
            _clock.Touch(User(sid));
        }

        _time.Advance(TimeSpan.FromMinutes(26));
        await _clock.TickAsync().WaitAsync(TimeSpan.FromSeconds(20));
        Assert.Equal(["fine-1"], _tabs.Noticed);
        Assert.Equal(3, _clock.Count); // all still tracked, and all end on time
        _time.Advance(TimeSpan.FromMinutes(5));
        await _clock.TickAsync().WaitAsync(TimeSpan.FromSeconds(20));
        Assert.Equal(0, _clock.Count);
        Assert.Equal(["fine-1"], _tabs.Ended);
    }

    [Fact]
    public async Task The_timer_loop_survives_a_pass_that_is_cancelled_or_throws_and_ends_only_with_the_host()
    {
        // The fault behind WT-24: a cancellation that is not the host's (a worker call cut off as the worker
        // stops) used to be taken for the host stopping, and the loop ended for good without a line in the log.
        var log = new ListLogger<SessionClock>();
        var passes = 0;
        using var stop = new CancellationTokenSource();
        var loop = TimedPasses.RunAsync("Session expiry", TimeSpan.FromMilliseconds(20), TimeProvider.System, () =>
        {
            var n = Interlocked.Increment(ref passes);
            return n switch
            {
                1 => Task.FromException(new TaskCanceledException()),
                2 => Task.FromException(new OperationCanceledException()),
                3 => throw new InvalidOperationException("thrown before the first await"),
                _ => Task.CompletedTask,
            };
        }, log, stop.Token);

        var until = Stopwatch.StartNew();
        while (Volatile.Read(ref passes) < 6 && until.Elapsed < TimeSpan.FromSeconds(10))
        {
            await Task.Delay(20);
        }

        Assert.True(Volatile.Read(ref passes) >= 6, "the loop stopped after a failed pass");
        Assert.False(loop.IsCompleted);
        Assert.Equal(3, log.Lines.Count(l => l.Level == LogLevel.Error && l.Text.Contains("Session expiry pass failed", StringComparison.Ordinal)));

        await stop.CancelAsync();
        await loop.WaitAsync(TimeSpan.FromSeconds(5)); // the host stopping ends it, quietly
    }

    [Fact]
    public async Task A_slow_pass_is_logged()
    {
        var log = new ListLogger<SessionClock>();
        var time = new SteppingTime();
        await TimedPasses.OnceAsync("Session expiry", time, () =>
        {
            time.Step(TimeSpan.FromSeconds(7));
            return Task.CompletedTask;
        }, log, CancellationToken.None);
        Assert.Contains(log.Lines, l => l.Level == LogLevel.Warning && l.Text.Contains("Session expiry pass took 7.0 s", StringComparison.Ordinal));
    }

    private sealed class SteppingTime : TimeProvider
    {
        private long _ticks;

        public override long TimestampFrequency => TimeSpan.TicksPerSecond;

        public override long GetTimestamp() => _ticks;

        public void Step(TimeSpan by) => _ticks += by.Ticks;
    }
}

/// <summary>WT-24 at the gateway, against a real worker process: a call to a worker that is stuck, or that
/// is stopped while the call is on its way, comes back as "not reached" in bounded time and never throws.</summary>
[Collection("gateway")]
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public class WorkerCallLimitTests(GatewayFixture gateway) : IClassFixture<GatewayFixture>, IAsyncLifetime
{
    private TimeSpan _was;

    private WorkerOptions Options => gateway.App.Services.GetRequiredService<IOptions<PortalOptions>>().Value.Workers;

    public async Task InitializeAsync()
    {
        _was = Options.ControlTimeout;
        foreach (var w in gateway.Pool.Running.ToList())
        {
            await gateway.Pool.StopAsync(w.Key);
        }
    }

    public Task DisposeAsync()
    {
        Options.ControlTimeout = _was;
        return Task.CompletedTask;
    }

    private static void Signal(string name, int pid)
    {
        using var kill = Process.Start(new ProcessStartInfo("kill", ["-" + name, pid.ToString(System.Globalization.CultureInfo.InvariantCulture)]) { UseShellExecute = false })!;
        kill.WaitForExit();
        Assert.Equal(0, kill.ExitCode);
    }

    private async Task<WorkerProcess> StartWorkerAsync(string user)
    {
        using var c = gateway.Client(user);
        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/")).StatusCode);
        return gateway.WorkerOf(user);
    }

    [Fact]
    public async Task A_worker_that_does_not_answer_is_given_up_after_the_time_limit_and_the_others_are_served()
    {
        var stuck = await StartWorkerAsync("wt24-stuck");
        await StartWorkerAsync("wt24-fine");
        Signal("STOP", stuck.Id); // frozen: it takes the call and never answers
        try
        {
            Options.ControlTimeout = TimeSpan.FromSeconds(1);
            var watch = Stopwatch.StartNew();
            Assert.Equal(0, await gateway.Pool.EndAsync("wt24-stuck", null));
            await gateway.Pool.NoticeAsync("wt24-stuck", null, new ExpiryNotice(DateTimeOffset.UtcNow.AddMinutes(1), ExpiryReason.Idle));
            await gateway.Pool.AnnounceAsync(null);           // every worker, the frozen one among them
            Assert.Equal(0, await gateway.Pool.EndAsync(null, "no-such-sid")); // every worker again
            Assert.Contains(gateway.Pool.Running, w => w.Key == UserKey.FromSub("wt24-fine"));
            await gateway.Pool.SuperviseAsync(CancellationToken.None); // health: one failed check for the frozen one
            Assert.True(watch.Elapsed < TimeSpan.FromSeconds(12), $"five calls took {watch.Elapsed}");
            Assert.Contains(gateway.Pool.Running, w => w.Key == stuck.Key); // not ended on one missed answer
        }
        finally
        {
            Signal("CONT", stuck.Id);
        }
    }

    [Fact]
    public async Task A_worker_killed_while_the_end_call_is_on_its_way_is_not_reached_and_nothing_is_thrown()
    {
        var worker = await StartWorkerAsync("wt24-killed");
        Signal("STOP", worker.Id);
        Options.ControlTimeout = TimeSpan.FromSeconds(30);
        var watch = Stopwatch.StartNew();
        var ending = gateway.Pool.EndAsync("wt24-killed", null);
        await Task.Delay(300);
        Assert.False(ending.IsCompleted); // the call is in flight
        Signal("KILL", worker.Id);
        Assert.Equal(0, await ending.WaitAsync(TimeSpan.FromSeconds(10)));
        Assert.True(watch.Elapsed < TimeSpan.FromSeconds(10));
    }

    [Fact]
    public async Task A_worker_stopped_by_the_gateway_while_the_end_call_is_on_its_way_is_not_reached_and_nothing_is_thrown()
    {
        // The race Web Test hit: the session clock's end call in flight while the supervisor stops the same
        // worker. Stopping closes the worker's connection under the call, which surfaces as a cancellation.
        var worker = await StartWorkerAsync("wt24-stopped");
        Signal("STOP", worker.Id);
        Options.ControlTimeout = TimeSpan.FromSeconds(30);
        var ending = gateway.Pool.EndAsync("wt24-stopped", null);
        await Task.Delay(300);
        Assert.False(ending.IsCompleted);
        var stopping = gateway.Pool.StopAsync(worker.Key);
        Assert.Equal(0, await ending.WaitAsync(TimeSpan.FromSeconds(5)));
        Signal("CONT", worker.Id); // let it see its input close and stop
        await stopping.WaitAsync(TimeSpan.FromSeconds(20));
        Assert.DoesNotContain(gateway.Pool.Running, w => w.Key == worker.Key);
    }
}
