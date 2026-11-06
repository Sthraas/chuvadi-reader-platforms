using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>
/// Sign-in on every endpoint (security check S-1 in docs/web/TEST-PLAN.md): every route is listed, and
/// only a fixed set may be reached without signing in. A new anonymous route fails this test until it is
/// added here on purpose.
/// </summary>
public class EndpointAuthTests
{
    /// <summary>Routes a visitor may reach before signing in, and why.</summary>
    private static readonly HashSet<string> Anonymous = new(StringComparer.Ordinal)
    {
        "/signin",                 // 12a sign-in page
        "/signin/sangam",          // leaves for Sangam
        "/signin-sangam",          // Sangam's answer (state, PKCE and iss checked)
        "/signout",                // ends a sign-in (cross-site refused)
        "/signout-sangam",         // back from Sangam's end-session
        "/signed-out",             // the signed-out page
        "/backchannel-logout",     // Sangam's signed logout token
        "/licence",                // licence agreement and notices (Terms of use)
        "/healthz",                // "ok", for monitoring
        "/error",                  // where unexpected failures land
    };

    private static async Task<IReadOnlyList<(string Route, bool AllowsAnonymous, bool StaticFile)>> RoutesAsync(params string[] extra)
    {
        var sangam = new FakeSangam();
        await sangam.StartAsync();
        try
        {
            await using var app = Program.Build(
            [
                "--environment", "Testing",
                "--urls", "http://127.0.0.1:0",
                "--Portal:DataRoot", SpaceLayoutTests.NewTempDir(),
                "--Sangam:Authority", sangam.Issuer,
                "--Sangam:ClientId", FakeSangam.ClientId,
                "--Sangam:ClientSecret", FakeSangam.ClientSecret,
                "--Logging:LogLevel:Default", "Error",
                .. extra,
            ]);
            await app.StartAsync();
            var routes = app.Services.GetRequiredService<EndpointDataSource>().Endpoints.OfType<RouteEndpoint>()
                .Select(e => ("/" + e.RoutePattern.RawText!.TrimStart('/'),
                    e.Metadata.GetMetadata<IAllowAnonymous>() is not null,
                    e.DisplayName?.Contains("StaticAssets", StringComparison.OrdinalIgnoreCase) == true
                        || e.Metadata.Any(m => m.GetType().Name.Contains("StaticAsset", StringComparison.Ordinal))))
                .ToList();
            await app.StopAsync();
            return routes;
        }
        finally
        {
            await sangam.DisposeAsync();
        }
    }

    [Theory]
    [InlineData("Single")]
    [InlineData("Gateway")]
    public async Task Only_the_listed_routes_can_be_reached_without_signing_in(string mode)
    {
        var routes = await RoutesAsync("--Portal:Mode", mode);
        Assert.NotEmpty(routes);
        var open = routes.Where(r => r.AllowsAnonymous && !r.StaticFile).Select(r => r.Route).Distinct().ToList();
        Assert.All(open, r => Assert.Contains(r, Anonymous));

        // The check sees what it should: the known open routes are found…
        Assert.Contains("/healthz", open);
        Assert.Contains("/licence", open);
        Assert.Contains("/backchannel-logout", open);

        // …and the person's own routes are protected (the fallback policy covers routes without metadata).
        bool Protected(string route) => routes.Any(r => r.Route == route) && routes.Where(r => r.Route == route).All(r => !r.AllowsAnonymous);
        Assert.True(Protected("/portal/activity"));
        if (mode == "Gateway")
        {
            Assert.True(Protected("/{**path}")); // the relay to workers: pages, circuit, uploads, downloads, print
        }
        else
        {
            Assert.True(Protected("/"));
            Assert.True(Protected("/portal/download/{token}"));
            Assert.True(Protected("/portal/upload/{ticket}/files"));
            Assert.True(Protected("/portal/upload/{ticket}/files/{fileId}"));
            Assert.True(Protected("/portal/print/{ticket}"));
        }
    }
}
