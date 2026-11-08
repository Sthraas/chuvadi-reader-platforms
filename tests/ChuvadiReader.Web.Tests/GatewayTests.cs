using System.Net;
using System.Net.Sockets;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Hosting.Workers;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>A gateway (Development sign-in) whose workers are real processes of the built portal.</summary>
public sealed class GatewayFixture : IAsyncLifetime
{
    public WebApplication App { get; private set; } = default!;
    public Uri Base { get; private set; } = default!;
    public string DataRoot { get; } = SpaceLayoutTests.NewTempDir();
    public string SocketFolder { get; } = Path.Combine(Path.GetTempPath(), "chvd-t-" + Guid.NewGuid().ToString("N")[..8]);

    /// <summary>The portal's own build output next to this test build (same configuration).</summary>
    public static string WorkerCommand()
    {
        var bin = AppContext.BaseDirectory; // tests/ChuvadiReader.Web.Tests/bin/<Config>/net10.0/
        var config = new DirectoryInfo(bin).Parent!.Name;
        var root = Path.GetFullPath(Path.Combine(bin, "..", "..", "..", "..", ".."));
        var dll = Path.Combine(root, "src", "ChuvadiReader.Web", "bin", config, "net10.0", "ChuvadiReader.Web.dll");
        return File.Exists(dll) ? dll : throw new FileNotFoundException("Build src/ChuvadiReader.Web first.", dll);
    }

    public async Task InitializeAsync()
    {
        App = Program.Build(
        [
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0",
            "--Portal:Mode", "Gateway",
            "--Portal:DataRoot", DataRoot,
            "--Portal:Workers:Command", WorkerCommand(),
            "--Portal:Workers:SocketFolder", SocketFolder,
            "--Portal:Workers:MaxWorkers", "3",
            "--Portal:Workers:IdleStop", "00:00:01",
            "--Portal:Workers:CheckInterval", "01:00:00", // tests call SuperviseAsync themselves
            "--Portal:Workers:MemoryLimitMB", "512",
            "--Logging:LogLevel:Default", "Warning",
        ]);
        await App.StartAsync();
        Base = new Uri(App.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
    }

    public WorkerPool Pool => App.Services.GetRequiredService<WorkerPool>();

    public HttpClient Client(string user)
    {
        var c = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = Base };
        c.DefaultRequestHeaders.Add("X-Dev-User", user);
        c.DefaultRequestHeaders.Add("Origin", Base.GetLeftPart(UriPartial.Authority));
        return c;
    }

    public WorkerProcess WorkerOf(string user) => Pool.Running.Single(w => w.Key == UserKey.FromSub(user));

    public async Task DisposeAsync()
    {
        await App.DisposeAsync();
        Directory.Delete(DataRoot, recursive: true);
    }
}

/// <summary>D-24: one worker process per person behind our own gateway.</summary>
[Collection("gateway")]
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public class GatewayTests(GatewayFixture gateway) : IClassFixture<GatewayFixture>, IAsyncLifetime
{
    /// <summary>Each test starts with no workers (the pool has three slots).</summary>
    public async Task InitializeAsync()
    {
        foreach (var w in gateway.Pool.Running.ToList())
        {
            await gateway.Pool.StopAsync(w.Key);
        }
    }

    public Task DisposeAsync() => Task.CompletedTask;

    [Fact]
    public async Task Each_person_gets_their_own_worker_process()
    {
        using var asha = gateway.Client("gw-asha");
        using var ravi = gateway.Client("gw-ravi");
        var page = await asha.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        Assert.Contains("blazor.web.js", await page.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.OK, (await ravi.GetAsync("/")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await asha.GetAsync("/library")).StatusCode);

        var a = gateway.WorkerOf("gw-asha");
        var r = gateway.WorkerOf("gw-ravi");
        Assert.NotEqual(a.Id, r.Id);
        Assert.NotEqual(Environment.ProcessId, a.Id);
        Assert.False(a.HasExited);
    }

    [Fact]
    public async Task A_worker_gets_a_private_home_a_memory_cap_and_none_of_the_gateways_secrets()
    {
        using var c = gateway.Client("gw-env");
        await c.GetAsync("/");
        var w = gateway.WorkerOf("gw-env");
        var env = (await File.ReadAllTextAsync($"/proc/{w.Id}/environ")).Split('\0').Where(e => e.Contains('=')).ToDictionary(e => e[..e.IndexOf('=')], e => e[(e.IndexOf('=') + 1)..]);
        Assert.Equal(Path.Combine(w.Folder, "home"), env["HOME"]);
        Assert.Equal(Path.Combine(w.Folder, "tmp"), env["TMPDIR"]);
        Assert.Equal("0x20000000", env["DOTNET_GCHeapHardLimit"]);
        Assert.Equal("Worker", env["Portal__Mode"]);
        Assert.DoesNotContain(env.Keys, k => k.StartsWith("Sangam__", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(env.Values, v => v.Length >= 32 && v == w.Secret); // the secret came on standard input
        Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute, File.GetUnixFileMode(w.Folder));
        Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute, File.GetUnixFileMode(gateway.SocketFolder));
    }

    [Fact]
    public async Task A_worker_answers_only_its_gateway()
    {
        using var c = gateway.Client("gw-direct");
        await c.GetAsync("/");
        var w = gateway.WorkerOf("gw-direct");
        using var handler = new SocketsHttpHandler
        {
            ConnectCallback = async (_, ct) =>
            {
                var s = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
                await s.ConnectAsync(new UnixDomainSocketEndPoint(w.Socket), ct);
                return new NetworkStream(s, ownsSocket: true);
            },
        };
        using var direct = new HttpClient(handler) { BaseAddress = new Uri("http://worker/") };

        // No secret: refused, whatever identity is claimed.
        using var noSecret = new HttpRequestMessage(HttpMethod.Get, "/");
        noSecret.Headers.Add(GatewayHeaders.Sub, GatewayHeaders.Encode("gw-direct"));
        Assert.Equal(HttpStatusCode.Unauthorized, (await direct.SendAsync(noSecret)).StatusCode);

        // The secret but someone else: refused (a worker serves one person).
        using var other = new HttpRequestMessage(HttpMethod.Get, "/");
        other.Headers.Add(GatewayHeaders.Secret, w.Secret);
        other.Headers.Add(GatewayHeaders.Sub, GatewayHeaders.Encode("gw-someone-else"));
        Assert.Equal(HttpStatusCode.Unauthorized, (await direct.SendAsync(other)).StatusCode);
    }

    [Fact]
    public async Task Browsers_cannot_reach_worker_controls_or_pose_as_someone_else()
    {
        using var c = gateway.Client("gw-poser");
        Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync("/_worker/health")).StatusCode);

        using var req = new HttpRequestMessage(HttpMethod.Get, "/");
        req.Headers.Add(GatewayHeaders.Sub, GatewayHeaders.Encode("gw-victim"));
        req.Headers.Add(GatewayHeaders.Secret, "guess-guess-guess-guess-guess-guess-guess");
        Assert.Equal(HttpStatusCode.OK, (await c.SendAsync(req)).StatusCode);
        Assert.DoesNotContain(gateway.Pool.Running, w => w.Key == UserKey.FromSub("gw-victim"));
        Assert.Contains(gateway.Pool.Running, w => w.Key == UserKey.FromSub("gw-poser"));
    }

    [Fact]
    public async Task Ending_a_sign_in_reaches_the_worker_and_an_unused_worker_is_stopped_with_its_files()
    {
        using var c = gateway.Client("gw-end");
        await c.GetAsync("/");
        var w = gateway.WorkerOf("gw-end");
        Assert.True(Directory.Exists(w.Folder));

        await gateway.App.Services.GetRequiredService<PortalSessions>().RevokeAsync("gw-end", null);
        await Task.Delay(1200); // past IdleStop
        await gateway.Pool.SuperviseAsync(CancellationToken.None);

        Assert.DoesNotContain(gateway.Pool.Running, x => x.Key == w.Key);
        Assert.True(w.HasExited);
        Assert.False(Directory.Exists(w.Folder));
        Assert.False(File.Exists(w.Socket));
    }

    [Fact]
    public async Task A_crashed_worker_is_cleaned_up_and_replaced_on_the_next_request()
    {
        using var c = gateway.Client("gw-crash");
        await c.GetAsync("/");
        var first = gateway.WorkerOf("gw-crash");
        first.Process.Kill();
        await first.Process.WaitForExitAsync();

        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/")).StatusCode);
        var second = gateway.WorkerOf("gw-crash");
        Assert.NotEqual(first.Id, second.Id);
        Assert.True(Directory.Exists(second.Folder));
    }

    [Fact]
    public async Task When_every_slot_is_taken_new_people_are_told_the_portal_is_busy()
    {
        var users = new List<HttpClient>();
        try
        {
            for (var i = 0; gateway.Pool.Count < 3 && i < 5; i++)
            {
                var u = gateway.Client("gw-fill-" + i);
                users.Add(u);
                await u.GetAsync("/");
            }

            using var late = gateway.Client("gw-late");
            var resp = await late.GetAsync("/");
            Assert.Equal(HttpStatusCode.ServiceUnavailable, resp.StatusCode);
            Assert.Contains("busy", await resp.Content.ReadAsStringAsync());
        }
        finally
        {
            foreach (var u in users)
            {
                u.Dispose();
            }

            foreach (var w in gateway.Pool.Running.ToList())
            {
                await gateway.Pool.StopAsync(w.Key);
            }
        }
    }

    [Fact]
    public async Task Many_requests_at_once_from_a_new_person_start_exactly_one_worker()
    {
        using var c = gateway.Client("gw-burst");
        var answers = await Task.WhenAll(Enumerable.Range(0, 20).Select(_ => c.GetAsync("/")));
        Assert.All(answers, a => Assert.Equal(HttpStatusCode.OK, a.StatusCode));
        Assert.Single(gateway.Pool.Running, w => w.Key == UserKey.FromSub("gw-burst"));
        Assert.Single(Directory.GetDirectories(Path.Combine(gateway.DataRoot, "workers")));
    }

    [Fact]
    public async Task The_health_check_needs_no_sign_in_and_starts_no_worker()
    {
        using var anonymous = new HttpClient { BaseAddress = gateway.Base };
        var resp = await anonymous.GetAsync("/healthz");
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        Assert.Equal("ok", await resp.Content.ReadAsStringAsync());
        Assert.Empty(gateway.Pool.Running);
    }

    [Fact]
    public async Task The_error_page_needs_no_sign_in_so_a_failure_cannot_loop()
    {
        using var anonymous = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = gateway.Base };
        var resp = await anonymous.GetAsync("/error");
        Assert.Equal(HttpStatusCode.InternalServerError, resp.StatusCode);
        Assert.Contains("Something went wrong", await resp.Content.ReadAsStringAsync());
        Assert.Empty(gateway.Pool.Running);
    }

    [Fact]
    public async Task The_legal_pages_are_readable_before_sign_in_marked_draft_and_start_no_worker()
    {
        using var anonymous = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = gateway.Base };
        async Task<string> Page(string path)
        {
            var resp = await anonymous.GetAsync(path);
            Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
            return await resp.Content.ReadAsStringAsync();
        }

        var terms = await Page("/terms");
        Assert.Contains("CHUVADI WEB PORTAL - TERMS OF USE", terms);
        Assert.Contains("DRAFT, to be reviewed by counsel", terms); // D-86: kept marked DRAFT
        Assert.Contains("<title>Terms of use &#183; Chuvadi</title>", terms);
        Assert.Contains("data-chvd-docs=\"/terms /privacy /licence?part=cookies /licence?part=notices\"", terms);
        Assert.Contains("js/legal.js", terms);
        Assert.DoesNotContain("blazor.web.js", terms);

        var privacy = await Page("/privacy");
        Assert.Contains("CHUVADI - PRIVACY NOTICE", privacy);
        Assert.Contains("DRAFT, to be reviewed by counsel", privacy);
        Assert.Contains("COOKIE AND BROWSER STORAGE NOTICE", await Page("/licence?part=cookies"));
        Assert.Contains("Third-party notices", await Page("/licence?part=notices"));

        // The portal shows its own documents, not the apps' licence agreement; anything unknown opens the terms.
        Assert.DoesNotContain("END USER LICENCE AGREEMENT", await Page("/licence"));
        Assert.Contains("TERMS OF USE", await Page("/licence?part=<script>"));
        Assert.Empty(gateway.Pool.Running);
    }

    [Fact]
    public async Task Static_files_come_from_the_gateway_without_starting_a_worker()
    {
        using var c = gateway.Client("gw-static");
        var css = await c.GetAsync("/css/portal.css");
        Assert.Equal(HttpStatusCode.OK, css.StatusCode);
        Assert.DoesNotContain(gateway.Pool.Running, w => w.Key == UserKey.FromSub("gw-static"));
    }

    [Fact]
    public async Task A_relayed_reader_page_keeps_the_portals_full_content_policy()
    {
        // WT-01: Blazor adds "frame-ancestors 'self'" to interactive pages; relayed, it must add to the
        // gateway's policy, not replace it.
        using var c = gateway.Client("gw-csp");
        var r = await c.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var policies = r.Headers.GetValues("Content-Security-Policy").ToList();
        Assert.Contains(SecurityHeaders.ContentSecurityPolicy, policies);
        Assert.All(policies, p => Assert.Contains("frame-ancestors 'self'", p, StringComparison.Ordinal));
        Assert.Equal("nosniff", r.Headers.GetValues("X-Content-Type-Options").Single());
    }

    [Fact]
    public async Task The_circuit_opens_only_from_the_portals_own_pages()
    {
        // WT-07: a foreign Origin (a sibling sub-domain counts as same-site for the cookie) is refused.
        using var own = gateway.Client("gw-origin");
        using var ok = await own.PostAsync("/_blazor/negotiate?negotiateVersion=1", null);
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);

        foreach (var origin in new[] { "https://evil.example", "null" })
        {
            using var req = new HttpRequestMessage(HttpMethod.Post, "/_blazor/negotiate?negotiateVersion=1");
            req.Headers.Remove("Origin");
            req.Headers.TryAddWithoutValidation("Origin", origin);
            using var foreign = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = gateway.Base };
            foreign.DefaultRequestHeaders.Add("X-Dev-User", "gw-origin");
            Assert.Equal(HttpStatusCode.Forbidden, (await foreign.SendAsync(req)).StatusCode);
        }

        using var bare = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = gateway.Base };
        bare.DefaultRequestHeaders.Add("X-Dev-User", "gw-origin");
        Assert.Equal(HttpStatusCode.Forbidden, (await bare.PostAsync("/_blazor/negotiate?negotiateVersion=1", null)).StatusCode); // opening needs an Origin

        // A closing page's beacon (Safari sends no usable Origin) still ends its circuit; a foreign one doesn't.
        Assert.NotEqual(HttpStatusCode.Forbidden, (await bare.PostAsync("/_blazor/disconnect", new StringContent("circuitId=x"))).StatusCode);
        using var evil = new HttpRequestMessage(HttpMethod.Post, "/_blazor/disconnect") { Content = new StringContent("circuitId=x") };
        evil.Headers.TryAddWithoutValidation("Origin", "https://evil.example");
        Assert.Equal(HttpStatusCode.Forbidden, (await bare.SendAsync(evil)).StatusCode);
    }
}

[CollectionDefinition("gateway", DisableParallelization = true)]
public class GatewayCollection
{
}
