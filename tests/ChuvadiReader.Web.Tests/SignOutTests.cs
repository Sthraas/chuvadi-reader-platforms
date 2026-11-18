using System.Security.Claims;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-194: Sign out asks about unsaved work first, and waits for a download the card has just handed over.</summary>
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public sealed class SignOutTests : IDisposable
{
    private sealed class Nav : NavigationManager
    {
        public List<string> Went { get; } = [];

        public Nav() => Initialize("https://reader.example.in/", "https://reader.example.in/reader");

        protected override void NavigateToCore(string uri, bool forceLoad)
        {
            lock (Went)
            {
                Went.Add(uri + (forceLoad ? " (full load)" : string.Empty));
            }

            if (!forceLoad)
            {
                Uri = ToAbsoluteUri(uri).ToString();
                NotifyLocationChanged(false);
            }
        }
    }

    private sealed class Work : IUnsavedWork
    {
        public bool HasUnsavedWork { get; set; }

        public bool Answer { get; set; }

        public int Asked { get; private set; }

        public Func<Task>? WhileAsking { get; set; }

        public event Action? Changed
        {
            add { }
            remove { }
        }

        public async Task<bool> ConfirmCloseAsync()
        {
            Asked++;
            if (WhileAsking is not null)
            {
                await WhileAsking();
            }

            return Answer;
        }
    }

    private sealed class SignedIn : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync()
            => Task.FromResult(new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", "ila"), new Claim("sid", "sid-9")], "test"))));
    }

    private readonly string _root = SpaceLayoutTests.NewTempDir();
    private readonly Nav _nav = new();
    private readonly Work _work = new();
    private readonly TransferRegistry _registry = new(TimeProvider.System);
    private readonly SessionSpace _space;
    private readonly ServiceProvider _services;
    private readonly WebAccount _account;

    public SignOutTests()
    {
        _space = TestSessions.Space(new SignedIn(), Options.Create(new PortalOptions { DataRoot = _root }));
        _services = new ServiceCollection()
            .AddSingleton<IUnsavedWork>(_work)
            .AddSingleton(_registry)
            .AddSingleton(_space)
            .BuildServiceProvider();
        _account = new WebAccount(new SignedIn(), _nav, _services);
    }

    public void Dispose()
    {
        _services.Dispose();
        Directory.Delete(_root, recursive: true);
    }

    [Fact]
    public async Task With_nothing_unsaved_sign_out_goes_straight_to_the_sign_out_address()
    {
        await _account.SignOutAsync();
        Assert.Equal(0, _work.Asked);
        Assert.Equal(["/signout (full load)"], _nav.Went);
    }

    [Fact]
    public async Task With_unsaved_work_the_card_is_asked_and_cancel_keeps_the_person_signed_in()
    {
        _work.HasUnsavedWork = true;
        _work.Answer = false;
        await _account.SignOutAsync();
        Assert.Equal(1, _work.Asked);
        Assert.Empty(_nav.Went);

        _work.Answer = true; // Save as, or Discard
        await _account.SignOutAsync();
        Assert.Equal(2, _work.Asked);
        Assert.Equal(["/signout (full load)"], _nav.Went);
    }

    [Fact]
    public async Task After_the_card_sign_out_goes_only_once_the_uis_own_move_home_is_done()
    {
        // Found by close_card.py in Chrome and WebKit: after Save as the Ui closes the documents and goes Home;
        // started after the sign-out's full page load, that move interrupted it.
        _work.HasUnsavedWork = true;
        _work.Answer = true;
        _work.WhileAsking = () =>
        {
            _ = Task.Run(async () =>
            {
                await Task.Delay(200);
                _nav.NavigateTo("/"); // the Ui, after closing the last document
            });
            return Task.CompletedTask;
        };

        await _account.SignOutAsync();
        Assert.Equal(["/", "/signout (full load)"], _nav.Went);
    }

    [Fact]
    public async Task When_the_ui_does_not_move_sign_out_waits_no_longer_than_a_moment()
    {
        _work.HasUnsavedWork = true;
        _work.Answer = true;
        var watch = System.Diagnostics.Stopwatch.StartNew();
        await _account.SignOutAsync();
        Assert.InRange(watch.ElapsedMilliseconds, 0, 3000);
        Assert.Equal(["/signout (full load)"], _nav.Went);
    }

    [Fact]
    public async Task After_save_as_sign_out_waits_until_the_browser_has_asked_for_the_download()
    {
        // The card's "Save as" hands the browser a download link; signing out deletes the session's files.
        await _space.EnsureAsync(default);
        var file = Path.Combine(_root, "marked.pdf");
        await File.WriteAllTextAsync(file, "%PDF-1.7");
        DownloadTicket? ticket = null;
        _work.HasUnsavedWork = true;
        _work.Answer = true;
        _work.WhileAsking = () =>
        {
            ticket = _registry.CreateDownload(_space.UserKey, _space.ConnectionId, file, "marked.pdf", TimeSpan.FromMinutes(5), deleteAfter: false);
            return Task.CompletedTask;
        };

        var signingOut = _account.SignOutAsync();
        await Task.Delay(300);
        Assert.False(signingOut.IsCompleted); // held: the browser hasn't asked for the file yet
        Assert.Empty(_nav.Went);

        Assert.NotNull(_registry.TakeDownload(ticket!.Id, _space.UserKey)); // the browser's request arrives
        await signingOut.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.Equal(["/signout (full load)"], _nav.Went);
    }

    [Fact]
    public async Task A_download_the_browser_never_asks_for_holds_sign_out_only_for_the_limit_and_another_connections_not_at_all()
    {
        await _space.EnsureAsync(default);
        var file = Path.Combine(_root, "x.pdf");
        await File.WriteAllTextAsync(file, "%PDF-1.7");
        _registry.CreateDownload(_space.UserKey, "another-connection", file, "x.pdf", TimeSpan.FromMinutes(5), deleteAfter: false);
        Assert.True(await _registry.WaitForDownloadsAsync(_space.ConnectionId, TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(10)));

        _registry.CreateDownload(_space.UserKey, _space.ConnectionId, file, "x.pdf", TimeSpan.FromMinutes(5), deleteAfter: false);
        var watch = System.Diagnostics.Stopwatch.StartNew();
        Assert.False(await _registry.WaitForDownloadsAsync(_space.ConnectionId, TimeSpan.FromMilliseconds(400), TimeSpan.FromSeconds(10)));
        Assert.InRange(watch.ElapsedMilliseconds, 350, 3000);

        // One issued longer ago than "recent" (a download the browser blocked) is not waited for.
        await Task.Delay(250);
        Assert.True(await _registry.WaitForDownloadsAsync(_space.ConnectionId, TimeSpan.FromSeconds(5), TimeSpan.FromMilliseconds(200)));
    }
}
