using System.Net;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using ChuvadiReader.Web.Auth;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;

namespace ChuvadiReader.Web.Tests;

/// <summary>The portal's own OpenID Connect client against <see cref="FakeSangam"/> (no browser).</summary>
public sealed class SangamSignInTests : IAsyncLifetime
{
    private readonly FakeSangam _sangam = new();
    private WebApplication _portal = default!;
    private Uri _base = default!;
    private string? _keyPath;

    public async Task InitializeAsync()
    {
        await _sangam.StartAsync();
        await StartPortalAsync();
    }

    private async Task StartPortalAsync(bool privateKey = false)
    {
        if (_portal is not null)
        {
            await _portal.DisposeAsync();
        }

        var args = new List<string>
        {
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0",
            "--Portal:DataRoot", SpaceLayoutTests.NewTempDir(),
            "--Sangam:Authority", _sangam.Issuer,
            "--Sangam:ClientId", FakeSangam.ClientId,
            "--Logging:LogLevel:Default", "Warning",
        };
        if (privateKey)
        {
            var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
            _sangam.ClientAssertionKey = key;
            _keyPath = Path.Combine(SpaceLayoutTests.NewTempDir(), "client.key.pem");
            File.WriteAllText(_keyPath, key.ExportPkcs8PrivateKeyPem());
            args.AddRange(["--Sangam:PrivateKeyPath", _keyPath, "--Sangam:PrivateKeyId", "portal-key-1"]);
        }
        else
        {
            args.AddRange(["--Sangam:ClientSecret", FakeSangam.ClientSecret]);
        }

        _portal = Program.Build(args.ToArray());
        await _portal.StartAsync();
        _base = new Uri(_portal.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
    }

    public async Task DisposeAsync()
    {
        await _portal.DisposeAsync();
        await _sangam.DisposeAsync();
    }

    private (HttpClient Client, CookieContainer Cookies) Browser(bool follow = true)
    {
        var cookies = new CookieContainer();
        var handler = new HttpClientHandler { CookieContainer = cookies, AllowAutoRedirect = follow, UseCookies = true };
        return (new HttpClient(handler) { BaseAddress = _base }, cookies);
    }

    private async Task<HttpClient> SignedInAsync()
    {
        var (c, _) = Browser();
        var r = await c.GetAsync("/signin/sangam?returnUrl=/library");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Equal("/library", r.RequestMessage!.RequestUri!.AbsolutePath);
        return c;
    }

    [Fact]
    public async Task The_sign_in_page_is_12a_with_continue_with_sangam_only()
    {
        var (c, _) = Browser(follow: false);
        var page = await c.GetAsync("/signin?returnUrl=/library");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = await page.Content.ReadAsStringAsync();
        Assert.Contains("Continue with Sangam", html);
        Assert.Contains("Download the desktop app", html);
        Assert.Contains("https://chuvadi.in/download", html);
        Assert.DoesNotContain("type=\"password\"", html); // D-34: no password on our page
        Assert.DoesNotContain("name=\"username\"", html); // U-9 (a): no Sangam ID field yet
        Assert.Contains("data-chvd-signin=\"/signin/sangam?returnUrl=%2Flibrary\"", html);
        Assert.Contains("js/signin.js", html);
        Assert.Contains("href=\"/terms\"", html); // "Terms of use" (D-86)
        Assert.Contains("Terms of use", html);
        Assert.DoesNotContain("blazor.web.js", html); // no circuit before sign-in

        // An unsafe return address never reaches the page.
        var evil = await (await c.GetAsync("/signin?returnUrl=//evil.example/x")).Content.ReadAsStringAsync();
        Assert.Contains("data-chvd-signin=\"/signin/sangam?returnUrl=%2F\"", evil);
    }

    [Fact]
    public async Task A_failed_sign_in_shows_the_reason_on_the_sign_in_page()
    {
        var (c, _) = Browser();
        var r = await c.GetAsync("/signin-sangam?code=abc&state=" + new string('a', 43) + "&iss=" + Uri.EscapeDataString(_sangam.Issuer));
        Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
        var html = await r.Content.ReadAsStringAsync();
        Assert.Contains("psi-err", html);
        Assert.Contains("Continue with Sangam", html);
    }

    [Fact]
    public async Task Anonymous_pages_go_to_sign_in_and_files_get_401()
    {
        var (c, _) = Browser(follow: false);
        var page = await c.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, page.StatusCode);
        Assert.StartsWith("/signin", page.Headers.Location!.PathAndQuery, StringComparison.Ordinal);
        Assert.Equal(HttpStatusCode.Unauthorized, (await c.GetAsync("/portal/download/x")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/signed-out")).StatusCode);
    }

    [Fact]
    public async Task The_authorize_request_has_pkce_state_nonce_and_exact_redirect()
    {
        var (c, cookies) = Browser(follow: false);
        var r = await c.GetAsync("/signin/sangam");
        var q = Microsoft.AspNetCore.WebUtilities.QueryHelpers.ParseQuery(r.Headers.Location!.Query);
        Assert.StartsWith(_sangam.Issuer + "connect/authorize", r.Headers.Location!.ToString(), StringComparison.Ordinal);
        Assert.Equal("code", q["response_type"]);
        Assert.Equal(FakeSangam.ClientId, q["client_id"]);
        Assert.Equal(new Uri(_base, "/signin-sangam").ToString(), q["redirect_uri"]);
        Assert.Equal("S256", q["code_challenge_method"]);
        Assert.Equal(43, q["code_challenge"].ToString().Length);
        Assert.True(q["state"].ToString().Length >= 40);
        Assert.True(q["nonce"].ToString().Length >= 40);
        Assert.Equal("openid profile email org.current", q["scope"]);
        var flow = cookies.GetCookies(new Uri(_base, "/signin-sangam")).Single();
        Assert.True(flow.HttpOnly);
        Assert.StartsWith(SangamSignIn.FlowCookiePrefix, flow.Name, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_full_sign_in_with_a_client_secret()
    {
        var c = await SignedInAsync();
        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/")).StatusCode);
        Assert.DoesNotContain("client_assertion", _sangam.TokenRequests.Single(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_full_sign_in_with_private_key_jwt()
    {
        await StartPortalAsync(privateKey: true);
        var c = await SignedInAsync();
        Assert.Equal(HttpStatusCode.OK, (await c.GetAsync("/")).StatusCode);
        Assert.Contains("client_assertion", _sangam.TokenRequests.Last(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_callback_without_the_flow_cookie_is_refused()
    {
        var (c, _) = Browser(follow: false);
        var r = await c.GetAsync("/signin-sangam?code=abc&state=" + new string('a', 43) + "&iss=" + Uri.EscapeDataString(_sangam.Issuer));
        Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
    }

    [Fact]
    public async Task A_callback_with_another_state_is_refused()
    {
        var (c, _) = Browser(follow: false);
        var start = await c.GetAsync("/signin/sangam");
        var q = Microsoft.AspNetCore.WebUtilities.QueryHelpers.ParseQuery(start.Headers.Location!.Query);
        var state = q["state"].ToString();
        var forged = state[..16] + new string('x', state.Length - 16);
        var r = await c.GetAsync($"/signin-sangam?code=abc&state={forged}&iss={Uri.EscapeDataString(_sangam.Issuer)}");
        Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
    }

    [Fact]
    public async Task A_response_without_iss_is_refused_when_sangam_promises_it()
    {
        _sangam.OmitIssInResponse = true;
        var (c, _) = Browser();
        var r = await c.GetAsync("/signin/sangam");
        Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
    }

    [Theory]
    [InlineData("nonce")]
    [InlineData("aud")]
    [InlineData("iss")]
    [InlineData("exp")]
    [InlineData("alg-none")]
    [InlineData("alg-hs256")]
    [InlineData("kid")]
    public async Task Bad_id_tokens_are_refused(string what)
    {
        _sangam.MutateIdToken = (h, p) =>
        {
            switch (what)
            {
                case "nonce": p["nonce"] = "other"; break;
                case "aud": p["aud"] = "another-app"; break;
                case "iss": p["iss"] = "https://evil.example/"; break;
                case "exp": p["exp"] = DateTimeOffset.UtcNow.AddMinutes(-10).ToUnixTimeSeconds(); break;
                case "alg-none": h["alg"] = "none"; break;
                case "alg-hs256": h["alg"] = "HS256"; break;
                case "kid": h["kid"] = "unknown-key"; break;
            }
        };
        var (c, _) = Browser();
        var r = await c.GetAsync("/signin/sangam");
        Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
        var (again, _) = Browser(follow: false);
        Assert.Equal(HttpStatusCode.Redirect, (await again.GetAsync("/")).StatusCode);
    }

    [Theory]
    [InlineData("//evil.example/x", "/")]
    [InlineData("https://evil.example/", "/")]
    [InlineData("/\\evil.example", "/")]
    [InlineData("/library?x=1", "/library?x=1")]
    [InlineData(null, "/")]
    public void Return_addresses_stay_on_the_portal(string? input, string expected)
        => Assert.Equal(expected, SangamSignIn.SafeReturnUrl(input));

    [Fact]
    public async Task Sign_out_revokes_the_cookie_and_goes_through_sangam()
    {
        var c = await SignedInAsync();
        var r = await c.GetAsync("/signout");
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        Assert.Equal(SangamSignIn.SignedOutPath, r.RequestMessage!.RequestUri!.AbsolutePath);
        var (check, _) = Browser(follow: false);
        Assert.Equal(HttpStatusCode.Redirect, (await check.GetAsync("/")).StatusCode);
    }

    [Fact]
    public async Task A_copied_cookie_stops_working_after_back_channel_logout()
    {
        var (c, cookies) = Browser();
        await c.GetAsync("/signin/sangam");
        var (copy, copyCookies) = Browser(follow: false);
        foreach (Cookie k in cookies.GetCookies(_base))
        {
            copyCookies.Add(_base, new Cookie(k.Name, k.Value, "/"));
        }

        Assert.Equal(HttpStatusCode.OK, (await copy.GetAsync("/")).StatusCode);
        var post = await PostLogoutAsync(_sangam.LogoutToken(_sangam.Sid));
        Assert.Equal(HttpStatusCode.OK, post.StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await copy.GetAsync("/")).StatusCode);
    }

    [Fact]
    public async Task Back_channel_logout_ends_open_tabs_of_that_sign_in_only()
    {
        var sessions = _portal.Services.GetRequiredService<OpenTabs>();
        int endedA = 0, endedB = 0;
        using var a = sessions.Open(_sangam.Subject, "sid-A", () => { endedA++; return Task.CompletedTask; }, _ => Task.CompletedTask);
        using var b = sessions.Open(_sangam.Subject, "sid-B", () => { endedB++; return Task.CompletedTask; }, _ => Task.CompletedTask);
        Assert.Equal(HttpStatusCode.OK, (await PostLogoutAsync(_sangam.LogoutToken("sid-A"))).StatusCode);
        Assert.Equal((1, 0), (endedA, endedB));

        // sub only: every sign-in of that person.
        using var c = sessions.Open(_sangam.Subject, "sid-C", () => { endedB++; return Task.CompletedTask; }, _ => Task.CompletedTask);
        Assert.Equal(HttpStatusCode.OK, (await PostLogoutAsync(_sangam.LogoutToken(null, _sangam.Subject))).StatusCode);
        Assert.Equal(2, endedB);
    }

    [Theory]
    [InlineData("nonce")]
    [InlineData("no-event")]
    [InlineData("aud")]
    [InlineData("typ")]
    [InlineData("no-jti")]
    [InlineData("no-ids")]
    [InlineData("signature")]
    public async Task Bad_logout_tokens_are_refused(string what)
    {
        var token = _sangam.LogoutToken("sid-X", mutate: (h, p) =>
        {
            switch (what)
            {
                case "nonce": p["nonce"] = "n"; break;
                case "no-event": p.Remove("events"); break;
                case "aud": p["aud"] = "another-app"; break;
                case "typ": h["typ"] = "JWT+other"; break;
                case "no-jti": p.Remove("jti"); break;
                case "no-ids": p.Remove("sid"); break;
            }
        });
        if (what == "signature")
        {
            token = token[..^4] + (token[^4..] == "AAAA" ? "BBBB" : "AAAA");
        }

        Assert.Equal(HttpStatusCode.BadRequest, (await PostLogoutAsync(token)).StatusCode);
    }

    [Fact]
    public async Task A_replayed_logout_token_does_nothing_more()
    {
        var sessions = _portal.Services.GetRequiredService<OpenTabs>();
        var token = _sangam.LogoutToken("sid-R");
        Assert.Equal(HttpStatusCode.OK, (await PostLogoutAsync(token)).StatusCode);
        int ended = 0;
        using var reg = sessions.Open(_sangam.Subject, "sid-R2", () => { ended++; return Task.CompletedTask; }, _ => Task.CompletedTask);
        Assert.Equal(HttpStatusCode.OK, (await PostLogoutAsync(token)).StatusCode);
        Assert.Equal(0, ended);
    }

    private async Task<HttpResponseMessage> PostLogoutAsync(string token)
    {
        using var c = new HttpClient { BaseAddress = _base };
        return await c.PostAsync("/backchannel-logout", new FormUrlEncodedContent(new Dictionary<string, string> { ["logout_token"] = token }));
    }
}

/// <summary>When Sangam is down, the portal says so instead of failing.</summary>
public class SangamUnreachableTests : IAsyncLifetime
{
    private WebApplication _portal = default!;
    private Uri _base = default!;

    public async Task InitializeAsync()
    {
        // A port nothing listens on: bind one, note it, let it go.
        var probe = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
        probe.Start();
        var deadPort = ((System.Net.IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();

        _portal = Program.Build(
        [
            "--environment", "Testing",
            "--urls", "http://127.0.0.1:0",
            "--Portal:DataRoot", SpaceLayoutTests.NewTempDir(),
            "--Sangam:Authority", $"http://127.0.0.1:{deadPort}/",
            "--Sangam:ClientId", FakeSangam.ClientId,
            "--Sangam:ClientSecret", FakeSangam.ClientSecret,
            "--Logging:LogLevel:Default", "Error",
        ]);
        await _portal.StartAsync();
        _base = new Uri(_portal.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.First());
    }

    public async Task DisposeAsync() => await _portal.DisposeAsync();

    [Fact]
    public async Task Continue_with_sangam_says_sangam_cannot_be_reached()
    {
        using var c = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = _base };
        var r = await c.GetAsync("/signin/sangam");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, r.StatusCode);
        var html = await r.Content.ReadAsStringAsync();
        Assert.Contains("be reached right now", html);
        Assert.Contains("psi-err", html);
        Assert.Contains("Continue with Sangam", html); // the sign-in page, ready to try again
    }

    [Fact]
    public async Task Signing_out_still_ends_on_the_signed_out_page()
    {
        using var c = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { BaseAddress = _base };
        var r = await c.GetAsync("/signout");
        Assert.Equal(HttpStatusCode.Redirect, r.StatusCode);
        Assert.Equal("/signed-out", r.Headers.Location!.OriginalString);
    }
}
