using System.Net;
using System.Security.Claims;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>A clock tests move by hand.</summary>
public sealed class ManualTime : TimeProvider
{
    private DateTimeOffset _now = new(2026, 11, 7, 9, 0, 0, TimeSpan.Zero);

    public override DateTimeOffset GetUtcNow() => _now;

    public void Advance(TimeSpan by) => _now += by;
}

/// <summary>Records what the clock asks of the tabs.</summary>
public sealed class RecordingTabs : ITabControl
{
    public List<(string? Sub, string? Sid)> Ended { get; } = new();
    public List<(string Sub, string? Sid, ExpiryNotice? Notice)> Notices { get; } = new();

    public Task<int> EndAsync(string? sub, string? sid)
    {
        Ended.Add((sub, sid));
        return Task.FromResult(1);
    }

    public Task NoticeAsync(string sub, string? sid, ExpiryNotice? notice)
    {
        Notices.Add((sub, sid, notice));
        return Task.CompletedTask;
    }

    public Task AnnounceAsync(MaintenanceNotice? notice) => Task.CompletedTask;
}

/// <summary>D-30: 30 minutes idle, 8 hours at most, a warning 5 minutes before.</summary>
public class SessionClockTests
{
    private readonly ManualTime _time = new();
    private readonly RecordingTabs _tabs = new();
    private readonly PortalSessions _sessions;
    private readonly SessionClock _clock;

    public SessionClockTests()
    {
        var sangam = Options.Create(new SangamOptions());
        _sessions = new PortalSessions(_time, sangam, _tabs);
        _clock = new SessionClock(_time, _sessions, _tabs, Options.Create(new PortalOptions()), sangam, NullLogger<SessionClock>.Instance);
    }

    private ClaimsPrincipal User(string sid, DateTimeOffset? signedIn = null)
    {
        var claims = new List<Claim> { new("sub", "person-1"), new("sid", sid) };
        if (signedIn is { } at)
        {
            claims.Add(new Claim(SessionClock.SignedInClaim, at.ToUnixTimeSeconds().ToString(System.Globalization.CultureInfo.InvariantCulture)));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "test"));
    }

    [Fact]
    public async Task Idle_session_is_warned_at_25_minutes_and_ended_at_30()
    {
        _clock.Touch(User("s1"));
        _time.Advance(TimeSpan.FromMinutes(24));
        await _clock.TickAsync();
        Assert.Empty(_tabs.Notices);

        _time.Advance(TimeSpan.FromMinutes(1));
        await _clock.TickAsync();
        var warned = Assert.Single(_tabs.Notices);
        Assert.Equal(ExpiryReason.Idle, warned.Notice!.Reason);
        Assert.Equal(_time.GetUtcNow() + TimeSpan.FromMinutes(5), warned.Notice.EndsAt);

        await _clock.TickAsync(); // nothing new to say
        Assert.Single(_tabs.Notices);

        _time.Advance(TimeSpan.FromMinutes(5));
        await _clock.TickAsync();
        Assert.Equal(("person-1", "s1"), Assert.Single(_tabs.Ended));
        Assert.False(_sessions.IsValid("person-1", "s1", _time.GetUtcNow() - TimeSpan.FromHours(1))); // the cookie stops working
        Assert.Equal(0, _clock.Count);
    }

    [Fact]
    public async Task Activity_during_the_warning_takes_it_down()
    {
        _clock.Touch(User("s2"));
        _time.Advance(TimeSpan.FromMinutes(26));
        await _clock.TickAsync();
        Assert.NotNull(Assert.Single(_tabs.Notices).Notice);

        _clock.Touch(User("s2"));
        await _clock.TickAsync();
        Assert.Null(_tabs.Notices[^1].Notice);
        _time.Advance(TimeSpan.FromMinutes(20));
        await _clock.TickAsync();
        Assert.Empty(_tabs.Ended);
    }

    [Fact]
    public async Task Eight_hours_end_a_session_however_busy()
    {
        var start = _time.GetUtcNow();
        while (_time.GetUtcNow() < start + TimeSpan.FromMinutes(470))
        {
            _clock.Touch(User("s3", start));
            _time.Advance(TimeSpan.FromMinutes(10));
            await _clock.TickAsync();
        }

        Assert.Empty(_tabs.Notices);
        _time.Advance(TimeSpan.FromMinutes(6)); // 7 h 56 min
        _clock.Touch(User("s3", start));
        await _clock.TickAsync();
        var notice = Assert.Single(_tabs.Notices).Notice!;
        Assert.Equal(ExpiryReason.Absolute, notice.Reason);
        Assert.Equal(start + TimeSpan.FromHours(8), notice.EndsAt);

        _clock.Touch(User("s3", start)); // activity doesn't move an absolute end
        await _clock.TickAsync();
        Assert.Single(_tabs.Notices);

        _time.Advance(TimeSpan.FromMinutes(5));
        _clock.Touch(User("s3", start));
        await _clock.TickAsync();
        Assert.Single(_tabs.Ended);
    }

    [Fact]
    public async Task A_sign_in_ended_elsewhere_is_forgotten_without_ending_twice()
    {
        _clock.Touch(User("s4"));
        await _sessions.RevokeAsync("person-1", "s4");
        Assert.Single(_tabs.Ended);
        await _clock.TickAsync();
        Assert.Equal(0, _clock.Count);
        _time.Advance(TimeSpan.FromHours(1));
        await _clock.TickAsync();
        Assert.Single(_tabs.Ended);
    }

    [Fact]
    public async Task Open_tabs_get_the_warning_and_new_tabs_see_it_too()
    {
        var tabs = new OpenTabs();
        var seen = new List<ExpiryNotice?>();
        using var first = tabs.Open("p", "sid", () => Task.CompletedTask, n => { seen.Add(n); return Task.CompletedTask; });
        var notice = new ExpiryNotice(DateTimeOffset.UtcNow.AddMinutes(5), ExpiryReason.Idle);
        await tabs.NoticeAsync("p", "sid", notice);
        var lateSeen = new List<ExpiryNotice?>();
        using var late = tabs.Open("p", "sid", () => Task.CompletedTask, n => { lateSeen.Add(n); return Task.CompletedTask; });
        using var other = tabs.Open("p", "other-sid", () => Task.CompletedTask, _ => throw new InvalidOperationException("not this sign-in"));
        Assert.Equal([notice], seen);
        Assert.Equal([notice], lateSeen);

        await tabs.NoticeAsync("p", "sid", null);
        Assert.Equal([notice, null], seen);
        Assert.Equal(2, await tabs.EndAsync("p", "sid"));
        Assert.Equal(1, tabs.Count);
    }

    [Fact]
    public void Circuit_traffic_and_static_files_are_not_activity()
    {
        Assert.False(ActivityTracking.CountsAsActivity("/_blazor"));
        Assert.False(ActivityTracking.CountsAsActivity("/_blazor/negotiate"));
        Assert.False(ActivityTracking.CountsAsActivity("/_content/ChuvadiReader.Ui/css/app.css"));
        Assert.False(ActivityTracking.CountsAsActivity("/js/portal.js"));
        Assert.True(ActivityTracking.CountsAsActivity("/"));
        Assert.True(ActivityTracking.CountsAsActivity("/library"));
        Assert.True(ActivityTracking.CountsAsActivity("/portal/activity"));
        Assert.True(ActivityTracking.CountsAsActivity("/portal/upload/t/files"));
    }
}

/// <summary>The page's input reports.</summary>
public class ActivityEndpointTests(PortalFixture portal) : IClassFixture<PortalFixture>
{
    [Fact]
    public async Task Activity_reports_need_the_portals_origin_and_header()
    {
        using var ok = portal.Client("activity-user");
        using var req = new HttpRequestMessage(HttpMethod.Post, "/portal/activity");
        req.Headers.Add("X-Chvd-Activity", "1");
        Assert.Equal(HttpStatusCode.NoContent, (await ok.SendAsync(req)).StatusCode);

        using var noHeader = new HttpRequestMessage(HttpMethod.Post, "/portal/activity");
        Assert.Equal(HttpStatusCode.Forbidden, (await ok.SendAsync(noHeader)).StatusCode);

        using var crossSite = portal.Client("activity-user", withOrigin: false);
        crossSite.DefaultRequestHeaders.Add("Origin", "https://elsewhere.example");
        using var cross = new HttpRequestMessage(HttpMethod.Post, "/portal/activity");
        cross.Headers.Add("X-Chvd-Activity", "1");
        Assert.Equal(HttpStatusCode.Forbidden, (await crossSite.SendAsync(cross)).StatusCode);
    }

    [Fact]
    public async Task A_page_load_starts_the_clock_for_that_person()
    {
        var clock = portal.App.Services.GetRequiredService<SessionClock>();
        using var c = portal.Client("clock-user");
        await c.GetAsync("/");
        Assert.NotNull(clock.EndOf("clock-user", null));
    }
}
