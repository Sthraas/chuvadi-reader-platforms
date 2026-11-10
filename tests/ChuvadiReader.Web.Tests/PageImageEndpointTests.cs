using System.Net;
using System.Security.Claims;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-158: drawn pages served by address, only to the person and sign-in that drew them.</summary>
public class PageImageEndpointTests(PortalFixture portal) : IClassFixture<PortalFixture>
{
    private static readonly byte[] Png = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 1, 2, 3, 4];

    private static ClaimsPrincipal Person(string sub, string? sid = null)
    {
        var claims = new List<Claim> { new("sub", sub) };
        if (sid is not null)
        {
            claims.Add(new Claim("sid", sid));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "test"));
    }

    private (PageImages Images, string Address) Draw(string sub)
    {
        var images = portal.App.Services.GetRequiredService<PageImages>();
        var token = images.Add(PortalPageImageOwner.For(Person(sub))!, Png); // what the dev sign-in gives: no sid
        return (images, "/" + PageImages.AddressOf(token));
    }

    [Fact]
    public async Task The_person_who_drew_a_page_gets_its_image_private_and_never_cached()
    {
        var (_, address) = Draw("img-owner");
        using var c = portal.Client("img-owner", withOrigin: false);
        using var r = await c.GetAsync(address);
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Equal("image/png", r.Content.Headers.ContentType?.MediaType);
        Assert.Equal(Png, await r.Content.ReadAsByteArrayAsync());
        Assert.True(r.Headers.CacheControl is { Private: true, NoStore: true, Public: false });
        Assert.Equal("same-origin", r.Headers.GetValues("Cross-Origin-Resource-Policy").Single());
        Assert.False(r.Headers.Contains("Access-Control-Allow-Origin")); // no CORS
    }

    [Fact]
    public async Task Anyone_else_unknown_freed_or_malformed_gets_the_same_404()
    {
        var (images, address) = Draw("img-alice");
        using var bob = portal.Client("img-bob", withOrigin: false);
        Assert.Equal(HttpStatusCode.NotFound, (await bob.GetAsync(address)).StatusCode);

        using var alice = portal.Client("img-alice", withOrigin: false);
        foreach (var bad in new[]
                 {
                     "/" + PageImages.AddressOf(new string('0', 32)),          // well formed, unknown
                     address.Replace(".png", ".PNG"), address + "x",          // not the address
                     "/" + PageImages.PathPrefix + "..%2F..%2Fetc%2Fpasswd",   // no directory paths
                     "/" + PageImages.PathPrefix + address[^36..^4].ToUpperInvariant() + ".png",
                 })
        {
            Assert.Equal(HttpStatusCode.NotFound, (await alice.GetAsync(bad)).StatusCode);
        }

        images.Remove(address[^36..^4]); // freed with its page or document
        Assert.Equal(HttpStatusCode.NotFound, (await alice.GetAsync(address)).StatusCode);
    }

    [Fact]
    public async Task Not_signed_in_or_from_another_site_gets_nothing()
    {
        var (_, address) = Draw("img-carol");
        // WT-20: 404 and nothing redirected, so the token is never copied into a returnUrl.
        using var anonymous = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = portal.Base };
        using var refused = await anonymous.GetAsync(address);
        Assert.Equal(HttpStatusCode.NotFound, refused.StatusCode);
        Assert.Null(refused.Headers.Location);
        Assert.Empty(await refused.Content.ReadAsByteArrayAsync());

        foreach (var (header, value) in new[]
                 {
                     ("Sec-Fetch-Site", "cross-site"), ("Sec-Fetch-Site", "same-site"), ("Origin", "https://evil.example"),
                 })
        {
            using var c = portal.Client("img-carol", withOrigin: false);
            c.DefaultRequestHeaders.Add(header, value);
            Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync(address)).StatusCode);
        }

        using var own = portal.Client("img-carol", withOrigin: false);
        own.DefaultRequestHeaders.Add("Sec-Fetch-Site", "same-origin");
        Assert.Equal(HttpStatusCode.OK, (await own.GetAsync(address)).StatusCode);
    }

    private sealed class FixedAuth(ClaimsPrincipal user) : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync() => Task.FromResult(new AuthenticationState(user));
    }

    [Fact]
    public void The_drawing_and_the_fetch_compute_the_same_owner_and_other_sign_ins_differ()
    {
        var alice = Person("alice", "sid-1");
        Assert.Equal(PortalPageImageOwner.For(alice), new PortalPageImageOwner(new FixedAuth(alice)).Current);
        Assert.NotEqual(PortalPageImageOwner.For(alice), PortalPageImageOwner.For(Person("alice", "sid-2"))); // her other sign-in
        Assert.NotEqual(PortalPageImageOwner.For(alice), PortalPageImageOwner.For(Person("bob", "sid-1")));

        var nobody = new PortalPageImageOwner(new FixedAuth(new ClaimsPrincipal(new ClaimsIdentity()))).Current;
        Assert.StartsWith("nobody/", nobody);
        Assert.NotEqual(nobody, new PortalPageImageOwner(new FixedAuth(new ClaimsPrincipal(new ClaimsIdentity()))).Current);
        Assert.Null(PortalPageImageOwner.For(new ClaimsPrincipal(new ClaimsIdentity())));
    }

    [Fact]
    public void Page_image_fetches_dont_keep_a_session_alive()
        => Assert.False(ChuvadiReader.Web.Auth.ActivityTracking.CountsAsActivity("/" + PageImages.PathPrefix + "abc.png"));
}
