using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Hosting.Acme;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>A server that accepts connections and never answers: a hanging Sangam.</summary>
public sealed class SilentServer : IDisposable
{
    private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
    private readonly List<Socket> _held = new();

    public SilentServer()
    {
        _listener.Start();
        _ = Task.Run(async () =>
        {
            try
            {
                while (true)
                {
                    var s = await _listener.AcceptSocketAsync();
                    lock (_held)
                    {
                        _held.Add(s);
                    }
                }
            }
            catch (Exception ex) when (ex is SocketException or ObjectDisposedException)
            {
            }
        });
    }

    public string Issuer => $"http://127.0.0.1:{((IPEndPoint)_listener.LocalEndpoint).Port}/";

    public void Dispose()
    {
        _listener.Stop();
        lock (_held)
        {
            _held.ForEach(s => s.Dispose());
        }
    }
}

/// <summary>O-1 (every call to Sangam has a 10 s limit) and O-2 (Sangam is probed before we send anyone there).</summary>
public sealed class SangamTimeoutTests : IAsyncLifetime
{
    private readonly FakeSangam _sangam = new();
    private readonly List<WebApplication> _portals = new();

    public Task InitializeAsync() => _sangam.StartAsync();

    public async Task DisposeAsync()
    {
        foreach (var p in _portals)
        {
            await p.DisposeAsync();
        }

        await _sangam.DisposeAsync();
    }

    private async Task<HttpClient> PortalAsync(string authority, params string[] extra)
    {
        var app = Program.Build(
        [
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0",
            "--Portal:DataRoot", SpaceLayoutTests.NewTempDir(),
            "--Sangam:Authority", authority,
            "--Sangam:ClientId", FakeSangam.ClientId,
            "--Sangam:ClientSecret", FakeSangam.ClientSecret,
            "--Logging:LogLevel:Default", "Error",
            .. extra,
        ]);
        await app.StartAsync();
        _portals.Add(app);
        var baseUri = new Uri(app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
        var handler = new HttpClientHandler { CookieContainer = new CookieContainer(), UseCookies = true };
        return new HttpClient(handler) { BaseAddress = baseUri, Timeout = TimeSpan.FromSeconds(60) };
    }

    private static async Task AssertSangamUnreachableAsync(HttpResponseMessage r)
    {
        Assert.Equal(HttpStatusCode.ServiceUnavailable, r.StatusCode);
        var html = await r.Content.ReadAsStringAsync();
        Assert.Contains("be reached right now", html);
        Assert.Contains("Continue with Sangam", html);
    }

    [Fact]
    public void Calls_to_sangam_are_limited_to_ten_seconds_by_default()
    {
        var o = new SangamOptions();
        Assert.Equal(TimeSpan.FromSeconds(10), o.CallTimeout);
        Assert.Equal(TimeSpan.FromSeconds(2), o.ProbeTimeout);
        Assert.Equal(TimeSpan.FromSeconds(30), o.ProbeCacheFor);
        using var factory = new DefaultHttpClientFactoryLite();
        using var client = new SangamMetadata(Options.Create(o), factory, TimeProvider.System).Client();
        Assert.Equal(TimeSpan.FromSeconds(10), client.Timeout);
    }

    [Fact]
    public async Task A_hanging_discovery_gives_up_at_the_call_limit()
    {
        using var silent = new SilentServer();
        using var factory = new DefaultHttpClientFactoryLite();
        var metadata = new SangamMetadata(Options.Create(new SangamOptions { Authority = silent.Issuer, CallTimeout = TimeSpan.FromSeconds(1) }), factory, TimeProvider.System);
        var clock = Stopwatch.StartNew();
        await Assert.ThrowsAnyAsync<TaskCanceledException>(() => metadata.DiscoveryAsync(CancellationToken.None));
        Assert.InRange(clock.Elapsed, TimeSpan.FromSeconds(0.5), TimeSpan.FromSeconds(8));
    }

    [Fact]
    public async Task A_hanging_token_call_shows_our_message_instead_of_a_page_that_never_loads()
    {
        using var c = await PortalAsync(_sangam.Issuer, "--Sangam:CallTimeout", "00:00:01");
        _sangam.TokenDelay = TimeSpan.FromSeconds(30);
        var clock = Stopwatch.StartNew();
        var r = await c.GetAsync("/signin/sangam?returnUrl=/"); // to Sangam and back to our callback, which redeems the code
        Assert.InRange(clock.Elapsed, TimeSpan.Zero, TimeSpan.FromSeconds(8));
        await AssertSangamUnreachableAsync(r);
        _sangam.TokenDelay = TimeSpan.Zero;
    }

    [Fact]
    public async Task A_sangam_that_doesnt_answer_the_probe_is_reported_before_anyone_is_sent_there()
    {
        using var silent = new SilentServer();
        using var c = await PortalAsync(silent.Issuer, "--Sangam:ProbeTimeout", "00:00:01", "--Sangam:CallTimeout", "00:01:00");
        var clock = Stopwatch.StartNew();
        await AssertSangamUnreachableAsync(await c.GetAsync("/signin/sangam"));
        Assert.InRange(clock.Elapsed, TimeSpan.Zero, TimeSpan.FromSeconds(6)); // the probe's limit, not the 60 s call limit
    }

    [Fact]
    public async Task Sangam_going_down_after_discovery_is_cached_still_shows_our_message()
    {
        using var c = await PortalAsync(_sangam.Issuer, "--Sangam:ProbeCacheFor", "00:00:00");
        var ok = await c.GetAsync("/signin/sangam?returnUrl=/library");
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode); // signed in; the discovery document is now cached
        await _sangam.DisposeAsync();
        using var fresh = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = c.BaseAddress };
        await AssertSangamUnreachableAsync(await fresh.GetAsync("/signin/sangam")); // not a redirect to a dead Sangam
        await _sangam.StartAsync(); // for DisposeAsync
    }

    [Fact]
    public async Task The_probe_answer_is_reused_for_thirty_seconds()
    {
        using var c = await PortalAsync(_sangam.Issuer);
        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/signin/sangam?returnUrl=/")).StatusCode);
        var seen = _sangam.DiscoveryRequests; // one probe, one discovery
        using var again = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = c.BaseAddress };
        Assert.Equal(HttpStatusCode.Redirect, (await again.GetAsync("/signin/sangam")).StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await again.GetAsync("/signin/sangam")).StatusCode);
        Assert.Equal(seen, _sangam.DiscoveryRequests);
        Assert.Equal(2, seen);
    }
}
