using System.Net;
using System.Net.Http.Json;
using System.Text;
using ChuvadiReader.Web.Files;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;

namespace ChuvadiReader.Web.Tests;

/// <summary>Runs the real portal on Kestrel (loopback, random port) in the Testing environment.</summary>
public sealed class PortalFixture : IAsyncLifetime
{
    public WebApplication App { get; private set; } = default!;
    public Uri Base { get; private set; } = default!;
    public string DataRoot { get; } = SpaceLayoutTests.NewTempDir();

    public async Task InitializeAsync()
    {
        App = Program.Build(
        [
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0",
            "--Portal:DataRoot", DataRoot,
            "--Logging:LogLevel:Default", "Warning",
        ]);
        await App.StartAsync();
        var address = App.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First();
        Base = new Uri(address);
    }

    public async Task DisposeAsync() => await App.DisposeAsync();

    public HttpClient Client(string user, bool withOrigin = true)
    {
        var c = new HttpClient { BaseAddress = Base };
        c.DefaultRequestHeaders.Add("X-Dev-User", user);
        if (withOrigin)
        {
            c.DefaultRequestHeaders.Add("Origin", Base.GetLeftPart(UriPartial.Authority));
        }

        return c;
    }

    public TransferRegistry Registry => App.Services.GetRequiredService<TransferRegistry>();

    public static string KeyOf(string user) => UserKey.From(SpaceLayoutTests.Principal(user))!;
}

public class EndpointTests : IClassFixture<PortalFixture>
{
    private static readonly byte[] Pdf = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");
    private readonly PortalFixture _portal;

    public EndpointTests(PortalFixture portal) => _portal = portal;

    private (UploadTicket Ticket, string Folder) NewUpload(string user, long maxBytes = 1024 * 1024)
    {
        var folder = Path.Combine(_portal.DataRoot, "up-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        return (_portal.Registry.CreateUpload(PortalFixture.KeyOf(user), "s-" + user, folder, PickKind.Pdf, true, 5, maxBytes, TimeSpan.FromMinutes(5)), folder);
    }

    [Fact]
    public async Task Upload_round_trip_in_chunks()
    {
        var (t, _) = NewUpload("alice");
        using var c = _portal.Client("alice");
        var begin = await c.PostAsJsonAsync($"/portal/upload/{t.Id}/files", new { name = "scan.pdf", size = Pdf.Length });
        Assert.Equal(HttpStatusCode.OK, begin.StatusCode);
        var id = (await begin.Content.ReadFromJsonAsync<Dictionary<string, object>>())!["id"].ToString();

        var r1 = await c.PutAsync($"/portal/upload/{t.Id}/files/{id}?offset=0", new ByteArrayContent(Pdf[..6]));
        Assert.Equal(HttpStatusCode.OK, r1.StatusCode);
        var r2 = await c.PutAsync($"/portal/upload/{t.Id}/files/{id}?offset=6", new ByteArrayContent(Pdf[6..]));
        Assert.Equal(HttpStatusCode.OK, r2.StatusCode);

        var file = Assert.Single(t.Completed([id!]));
        Assert.Equal(Pdf, File.ReadAllBytes(file.Path));
    }

    [Fact]
    public async Task Another_person_cannot_use_my_upload_ticket()
    {
        var (t, _) = NewUpload("alice");
        using var mallory = _portal.Client("mallory");
        var r = await mallory.PostAsJsonAsync($"/portal/upload/{t.Id}/files", new { name = "x.pdf", size = 10 });
        Assert.Equal(HttpStatusCode.NotFound, r.StatusCode);
    }

    [Fact]
    public async Task Uploads_without_the_portal_origin_are_refused()
    {
        var (t, _) = NewUpload("alice");
        using var noOrigin = _portal.Client("alice", withOrigin: false);
        var r = await noOrigin.PostAsJsonAsync($"/portal/upload/{t.Id}/files", new { name = "x.pdf", size = 10 });
        Assert.Equal(HttpStatusCode.Forbidden, r.StatusCode);

        using var evil = _portal.Client("alice", withOrigin: false);
        evil.DefaultRequestHeaders.Add("Origin", "https://evil.example");
        r = await evil.PostAsJsonAsync($"/portal/upload/{t.Id}/files", new { name = "x.pdf", size = 10 });
        Assert.Equal(HttpStatusCode.Forbidden, r.StatusCode);
    }

    [Fact]
    public async Task A_chunk_over_the_limit_is_refused()
    {
        var (t, _) = NewUpload("alice", maxBytes: 64 * 1024 * 1024);
        using var c = _portal.Client("alice");
        var big = 5 * 1024 * 1024;
        var begin = await c.PostAsJsonAsync($"/portal/upload/{t.Id}/files", new { name = "big.pdf", size = big });
        var id = (await begin.Content.ReadFromJsonAsync<Dictionary<string, object>>())!["id"].ToString();
        // The server answers before reading the body, so the client may see the 400 or a closed connection.
        try
        {
            var r = await c.PutAsync($"/portal/upload/{t.Id}/files/{id}?offset=0", new ByteArrayContent(new byte[big]));
            Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
        }
        catch (HttpRequestException)
        {
        }

        var file = t.Find(id!)!;
        Assert.Equal(0, file.Received);
        Assert.False(File.Exists(file.Path));
    }

    [Fact]
    public async Task Download_is_single_use_and_owner_only()
    {
        var path = Path.Combine(_portal.DataRoot, Guid.NewGuid().ToString("N") + ".pdf");
        await File.WriteAllBytesAsync(path, Pdf);
        var d = _portal.Registry.CreateDownload(PortalFixture.KeyOf("alice"), "s", path, "Signed copy.pdf", TimeSpan.FromMinutes(1), deleteAfter: false);

        using var mallory = _portal.Client("mallory");
        Assert.Equal(HttpStatusCode.NotFound, (await mallory.GetAsync($"/portal/download/{d.Id}")).StatusCode);

        using var alice = _portal.Client("alice");
        // Mallory's attempt doesn't burn the ticket.
        var ok = await alice.GetAsync($"/portal/download/{d.Id}");
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        Assert.Equal(Pdf, await ok.Content.ReadAsByteArrayAsync());
        Assert.Equal("application/pdf", ok.Content.Headers.ContentType!.MediaType);
        Assert.Contains("attachment", ok.Content.Headers.ContentDisposition!.DispositionType, StringComparison.Ordinal);
        Assert.Equal("no-store", ok.Headers.CacheControl!.ToString());

        Assert.Equal(HttpStatusCode.NotFound, (await alice.GetAsync($"/portal/download/{d.Id}")).StatusCode);
    }

    [Fact]
    public async Task Print_serves_the_pdf_inline_to_its_owner_only()
    {
        var path = Path.Combine(_portal.DataRoot, Guid.NewGuid().ToString("N") + ".pdf");
        await File.WriteAllBytesAsync(path, Pdf);
        var p = _portal.Registry.CreatePrint(PortalFixture.KeyOf("alice"), "s", path, "lab report", TimeSpan.FromMinutes(1));

        using var mallory = _portal.Client("mallory");
        Assert.Equal(HttpStatusCode.NotFound, (await mallory.GetAsync($"/portal/print/{p.Id}")).StatusCode);

        using var alice = _portal.Client("alice");
        var r = await alice.GetAsync($"/portal/print/{p.Id}");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Equal("application/pdf", r.Content.Headers.ContentType!.MediaType);
        Assert.Equal("inline", r.Content.Headers.ContentDisposition!.DispositionType);
    }

    [Fact]
    public async Task Every_response_carries_the_security_headers()
    {
        using var c = _portal.Client("alice");
        var r = await c.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Contains(r.Headers.GetValues("Content-Security-Policy"), v => v.Contains("default-src 'self'", StringComparison.Ordinal));
        Assert.Equal("nosniff", r.Headers.GetValues("X-Content-Type-Options").Single());
        Assert.Equal("no-referrer", r.Headers.GetValues("Referrer-Policy").Single());
        Assert.False(r.Headers.Contains("Server"));
    }

    [Fact]
    public async Task The_ui_assets_are_served()
    {
        using var c = _portal.Client("alice");
        foreach (var path in new[] { "/_content/ChuvadiReader.Ui/css/shell.css", "/js/portal.js", "/_content/ChuvadiReader.Ui/js/theme.js", "/_framework/blazor.web.js" })
        {
            Assert.Equal(HttpStatusCode.OK, (await c.GetAsync(path)).StatusCode);
        }
    }
}
