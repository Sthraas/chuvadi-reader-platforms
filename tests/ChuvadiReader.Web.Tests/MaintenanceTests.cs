using System.Net.Http.Json;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Hosting.Workers;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>Planned restarts are announced in advance (coordinator, 7 Nov).</summary>
public class MaintenanceTests
{
    private readonly string _dir = SpaceLayoutTests.NewTempDir();
    private static readonly DateTimeOffset Now = new(2026, 11, 8, 15, 0, 0, TimeSpan.Zero);

    private string File(params string[] lines)
    {
        var path = Path.Combine(_dir, "maintenance");
        System.IO.File.WriteAllLines(path, lines);
        return path;
    }

    [Fact]
    public void The_file_gives_the_time_and_optionally_the_text()
    {
        var notice = MaintenanceAnnouncer.Read(File("2026-11-08T22:00+05:30"), Now, out var problem);
        Assert.Null(problem);
        Assert.Equal(new DateTimeOffset(2026, 11, 8, 22, 0, 0, TimeSpan.FromHours(5.5)), notice!.At);
        Assert.Null(notice.Message);

        var custom = MaintenanceAnnouncer.Read(File("2026-11-08T16:30:00Z", "Back in ten minutes with Word layout."), Now, out _);
        Assert.Equal("Back in ten minutes with Word layout.", custom!.Message);
    }

    [Theory]
    [InlineData("2026-11-08T22:00")]   // no zone: refused, the server's own zone would be a guess
    [InlineData("tonight at ten")]
    public void A_time_without_its_zone_is_refused_with_a_reason(string line)
    {
        Assert.Null(MaintenanceAnnouncer.Read(File(line), Now, out var problem));
        Assert.Contains("offset", problem);
    }

    [Fact]
    public void No_file_an_empty_file_or_a_past_time_announce_nothing()
    {
        Assert.Null(MaintenanceAnnouncer.Read(Path.Combine(_dir, "none"), Now, out _));
        Assert.Null(MaintenanceAnnouncer.Read(File(""), Now, out _));
        Assert.Null(MaintenanceAnnouncer.Read(File("2026-11-08T14:59Z"), Now, out var problem));
        Assert.Null(problem);
    }

    [Fact]
    public async Task Open_tabs_get_the_banner_and_lose_it_when_the_file_goes()
    {
        var tabs = new OpenTabs();
        var changes = 0;
        tabs.MaintenanceChanged += () => changes++;
        var path = File(DateTimeOffset.UtcNow.AddHours(1).ToString("O"));
        var announcer = new MaintenanceAnnouncer(tabs, Options.Create(new PortalOptions { MaintenanceNoticeFile = path }), TimeProvider.System,
            NullLogger<MaintenanceAnnouncer>.Instance);

        await announcer.CheckAsync();
        Assert.NotNull(tabs.Maintenance);
        await announcer.CheckAsync(); // unchanged: no new event
        Assert.Equal(1, changes);

        System.IO.File.Delete(path);
        await announcer.CheckAsync();
        Assert.Null(tabs.Maintenance);
        Assert.Equal(2, changes);
    }
}

/// <summary>The gateway passes announcements to every worker, including ones started later.</summary>
[Collection("gateway")]
public class GatewayMaintenanceTests(GatewayFixture gateway) : IClassFixture<GatewayFixture>
{
    private static async Task<DateTimeOffset?> AnnouncedIn(WorkerProcess worker)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, WorkerHost.ControlPrefix + "/health");
        worker.Sign(req, null);
        using var resp = await worker.Client.SendAsync(req);
        var health = await resp.Content.ReadFromJsonAsync<Health>();
        return health!.Maintenance;
    }

    private sealed record Health(int Tabs, int Circuits, DateTimeOffset? Maintenance);

    [Fact]
    public async Task Running_and_later_workers_both_show_the_restart()
    {
        using var early = gateway.Client("gw-maint-early");
        await early.GetAsync("/");
        var at = DateTimeOffset.UtcNow.AddHours(2);
        await gateway.Pool.AnnounceAsync(new MaintenanceNotice(at, null));
        Assert.Equal(at, await AnnouncedIn(gateway.WorkerOf("gw-maint-early")));

        using var late = gateway.Client("gw-maint-late");
        await late.GetAsync("/");
        Assert.Equal(at, await AnnouncedIn(gateway.WorkerOf("gw-maint-late")));

        await gateway.Pool.AnnounceAsync(null);
        Assert.Null(await AnnouncedIn(gateway.WorkerOf("gw-maint-early")));
        foreach (var w in gateway.Pool.Running.ToList())
        {
            await gateway.Pool.StopAsync(w.Key);
        }
    }
}
