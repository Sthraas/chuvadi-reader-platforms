using System.Security.Claims;
using System.Text;
using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Microsoft.JSInterop;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>Builds the per-session pieces the way the portal does, for tests.</summary>
internal static class TestSessions
{
    public static SessionStates States(IOptions<PortalOptions> options, PageImages? images = null)
        => new(options, images ?? new PageImages(), TimeProvider.System, NullLogger<SessionStates>.Instance);

    public static SessionSpace Space(AuthenticationStateProvider auth, IOptions<PortalOptions> options)
        => new(auth, States(options), TimeProvider.System);
}

/// <summary>
/// D-174 (WT-22): open tabs and files belong to the signed-in session, not to a browser connection. A reload
/// gets the same tabs back; a connection that goes closes its own copies; session end frees and deletes
/// everything, whichever connection opened it.
/// </summary>
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public sealed class SessionKeepsTabsTests : IDisposable
{
    private sealed class As(string sub, string? sid) : AuthenticationStateProvider
    {
        public ClaimsPrincipal User { get; } = new(new ClaimsIdentity(
            sid is null ? [new Claim("sub", sub)] : [new Claim("sub", sub), new Claim("sid", sid)], "test"));

        public override Task<AuthenticationState> GetAuthenticationStateAsync() => Task.FromResult(new AuthenticationState(User));
    }

    private sealed class NoJs : IJSRuntime
    {
        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, object?[]? args) => ValueTask.FromResult(default(TValue)!);

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, CancellationToken cancellationToken, object?[]? args) => ValueTask.FromResult(default(TValue)!);
    }

    /// <summary>One browser connection: its own scoped services over the shared session.</summary>
    private sealed class Connection : IAsyncDisposable
    {
        private readonly OutboxDelivery _outbox;

        public Connection(SessionStates states, PageImages images, IOptions<PortalOptions> options, As who)
        {
            Space = new SessionSpace(who, states, TimeProvider.System);
            _outbox = new OutboxDelivery(Space, new TransferRegistry(TimeProvider.System), new BrowserBridge(new NoJs()), options,
                TimeProvider.System, NullLogger<OutboxDelivery>.Instance);
            Storage = new SessionAppStorage(Space, _outbox);
            Tabs = new TabsService(new ChuvadiPdfReader(images, new FixedOwner(PortalPageImageOwner.For(who.User)!)), Storage);
        }

        public SessionSpace Space { get; }

        public SessionAppStorage Storage { get; }

        public TabsService Tabs { get; }

        /// <summary>What the portal does when a connection closes (a reload, the tab closed).</summary>
        public async ValueTask DisposeAsync()
        {
            Tabs.Dispose(); // the shared Core closes the connection's documents and leaves the saved list alone
            Space.Dispose();
            await _outbox.DisposeAsync();
        }
    }

    private sealed class FixedOwner(string owner) : ChuvadiReader.Platform.IPageImageOwner
    {
        public string Current => owner;
    }

    private readonly IOptions<PortalOptions> _options = Options.Create(new PortalOptions { DataRoot = SpaceLayoutTests.NewTempDir() });
    private readonly PageImages _images = new();
    private readonly SessionStates _states;

    public SessionKeepsTabsTests() => _states = TestSessions.States(_options, _images);

    public void Dispose() => _states.Dispose();

    /// <summary>A small valid PDF: one page, one line of text.</summary>
    private static byte[] OnePagePdf(string text)
    {
        var content = $"BT /F1 24 Tf 72 700 Td ({text}) Tj ET";
        string[] objects =
        [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            $"<< /Length {content.Length} >>\nstream\n{content}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ];
        var sb = new StringBuilder("%PDF-1.7\n");
        var offsets = new List<int>();
        for (var i = 0; i < objects.Length; i++)
        {
            offsets.Add(sb.Length);
            sb.Append(i + 1).Append(" 0 obj\n").Append(objects[i]).Append("\nendobj\n");
        }

        var xref = sb.Length;
        sb.Append("xref\n0 ").Append(objects.Length + 1).Append("\n0000000000 65535 f \n");
        offsets.ForEach(o => sb.Append(o.ToString("D10", System.Globalization.CultureInfo.InvariantCulture)).Append(" 00000 n \n"));
        sb.Append("trailer\n<< /Size ").Append(objects.Length + 1).Append(" /Root 1 0 R >>\nstartxref\n").Append(xref).Append("\n%%EOF\n");
        return Encoding.ASCII.GetBytes(sb.ToString());
    }

    private static async Task<string> UploadAsync(Connection c, string name)
    {
        await c.Space.EnsureAsync();
        var path = Path.Combine(c.Space.Uploads, name);
        await File.WriteAllBytesAsync(path, OnePagePdf(name));
        return path;
    }

    [Fact]
    public async Task A_reload_gets_the_same_tabs_and_files_back_and_the_old_connection_lets_go()
    {
        var alice = new As("alice", "sid-1");
        var first = new Connection(_states, _images, _options, alice);
        var a = await UploadAsync(first, "a.pdf");
        var b = await UploadAsync(first, "b.pdf");
        await first.Tabs.OpenAsync(a, "a.pdf", DocumentFormat.Pdf);
        await first.Tabs.OpenAsync(b, "b.pdf", DocumentFormat.Pdf);
        Assert.NotNull(first.Tabs.Active?.Session); // really open
        var held = _images.Add(PortalPageImageOwner.For(alice.User)!, [1, 2, 3]); // a page image of this sign-in

        // The reload: a new connection of the same sign-in starts, the old one closes.
        var second = new Connection(_states, _images, _options, alice);
        await first.DisposeAsync();
        Assert.Empty(first.Tabs.Tabs); // WT-22: the old connection's documents are closed

        await second.Tabs.RestoreAsync(); // what the Dashboard and the Reader do when they start
        Assert.Equal(["a.pdf", "b.pdf"], second.Tabs.Tabs.Select(t => t.FileName));
        Assert.Equal([a, b], second.Tabs.Tabs.Select(t => t.Path));
        Assert.Equal("b.pdf", second.Tabs.Active?.FileName);
        Assert.NotNull(second.Tabs.Active?.Session); // the active document is open again, from the same working copy
        Assert.True(File.Exists(a) && File.Exists(b));
        Assert.Equal(first.Space.Root, second.Space.Root);

        // The session ends (expiry, sign-out): everything goes, whichever connection opened it.
        Assert.Equal(1, _states.Count);
        Assert.Equal(0, await new ChuvadiReader.Web.Auth.OpenTabs(_states).EndAsync("alice", "sid-1")); // no connection registered, and still:
        Assert.False(Directory.Exists(second.Space.Root));
        Assert.False(_images.TryGet(held, PortalPageImageOwner.For(alice.User)!, out _));
        Assert.Equal(0, _states.Count);
        await second.DisposeAsync();
    }

    [Fact]
    public async Task Another_sign_in_or_person_never_sees_these_tabs_or_files()
    {
        var mine = new Connection(_states, _images, _options, new As("alice", "sid-1"));
        await mine.Tabs.OpenAsync(await UploadAsync(mine, "mine.pdf"), "mine.pdf", DocumentFormat.Pdf);

        foreach (var who in new[] { new As("alice", "sid-2"), new As("bob", "sid-1"), new As("bob", null) })
        {
            var other = new Connection(_states, _images, _options, who);
            await other.Tabs.RestoreAsync();
            Assert.Empty(other.Tabs.Tabs);
            await other.Space.EnsureAsync();
            Assert.NotEqual(mine.Space.Root, other.Space.Root);
            Assert.False(other.Space.Contains(mine.Tabs.Tabs[0].Path));
            await other.DisposeAsync();
        }

        // Ending alice's other sign-in, or bob, leaves this session alone.
        _states.End("alice", "sid-2");
        _states.End("bob", null);
        Assert.True(File.Exists(mine.Tabs.Tabs[0].Path));
        await mine.DisposeAsync();
    }

    [Fact]
    public async Task Settings_are_the_sessions_but_each_connection_saves_into_its_own_folder()
    {
        var who = new As("alice", "sid-1");
        var one = new Connection(_states, _images, _options, who);
        var two = new Connection(_states, _images, _options, who);
        await one.Storage.SetAsync("theme", "dark");
        Assert.Equal("dark", await two.Storage.GetAsync("theme"));

        var saveOne = await one.Storage.GetAsync(SessionAppStorage.SaveFolderKey);
        var saveTwo = await two.Storage.GetAsync(SessionAppStorage.SaveFolderKey);
        Assert.NotEqual(saveOne, saveTwo); // a save downloads in the tab that made it, once
        Assert.All(new[] { saveOne!, saveTwo! }, f => Assert.True(SpaceLayout.IsInside(one.Space.Outbox, Path.Combine(f, "x")) && Directory.Exists(f)));
        Assert.EndsWith("Chuvadi Documents", saveOne);

        await one.Storage.SetAsync(SessionAppStorage.SaveFolderKey, "/etc"); // outside the session: ignored
        Assert.Equal(saveOne, await one.Storage.GetAsync(SessionAppStorage.SaveFolderKey));
        await one.DisposeAsync();
        await two.DisposeAsync();
    }

    [Fact]
    public async Task A_session_with_no_connection_stays_until_it_ends_and_a_forgotten_one_is_swept()
    {
        var who = new As("carol", "sid-9");
        var only = new Connection(_states, _images, _options, who);
        var path = await UploadAsync(only, "kept.pdf");
        var state = only.Space.State;
        Assert.Equal(1, state.Connections);
        await only.DisposeAsync(); // the browser tab is closed without signing out
        Assert.Equal(0, state.Connections);
        Assert.True(File.Exists(path)); // the session is still signed in: the person may come back
        Assert.Equal(1, _states.Count);

        Assert.Equal(0, _states.EndAbandoned(TimeSpan.FromMinutes(35))); // not yet
        Assert.Equal(1, _states.EndAbandoned(TimeSpan.Zero));            // the safety net behind the session clock
        Assert.False(File.Exists(path));

        // A new connection after the end starts a new, empty session.
        var again = new Connection(_states, _images, _options, who);
        await again.Space.EnsureAsync();
        Assert.NotEqual(state.Root, again.Space.Root);
        await again.Tabs.RestoreAsync();
        Assert.Empty(again.Tabs.Tabs);
        await again.DisposeAsync();
    }

    private sealed class UnsavedMarks : ITabMarks
    {
        public int Count => 1;

        public bool HasUnsaved => true;

        public void Discard()
        {
        }
    }

    [Fact]
    public async Task Session_end_closes_documents_with_unsaved_marks_without_the_question_a_tab_close_asks()
    {
        // D-190: closing a tab with unsaved marks asks first, and Cancel keeps it open. The end of the sign-in
        // cannot be held, so it closes without asking; otherwise the documents (and their memory) would stay.
        var c = new Connection(_states, _images, _options, new As("erin", "sid-4"));
        var path = await UploadAsync(c, "marked.pdf");
        var tab = await c.Tabs.OpenAsync(path, "marked.pdf", DocumentFormat.Pdf);
        tab.Marks = new UnsavedMarks();
        var asked = 0;
        c.Tabs.CloseGuard = _ =>
        {
            asked++;
            return Task.FromResult(false); // the person chose Cancel
        };

        await c.Tabs.CloseAsync(tab.Id);
        await c.Tabs.CloseAllAsync();
        Assert.Equal(2, asked);
        Assert.Single(c.Tabs.Tabs); // still open: the card's answer is respected for the Ui's own closes

        await ChuvadiReader.Web.Hosting.SessionEndClose.CloseDocumentsAsync(c.Tabs);
        Assert.Equal(2, asked);     // not asked again
        Assert.Empty(c.Tabs.Tabs);
        await c.DisposeAsync();
    }

    [Fact]
    public async Task A_browser_that_left_without_a_goodbye_does_not_keep_its_worker_once_the_session_has_ended()
    {
        // WT-25: the framework keeps a circuit whose browser is gone for minutes. While the session lives, the
        // session keeps the worker (D-174); once it has ended, only an attached browser does.
        var counter = new ChuvadiReader.Web.Hosting.Workers.CircuitCounter();
        var c = new Connection(_states, _images, _options, new As("frank", "sid-5"));
        var life = new SessionLifetime(c.Space, new TransferRegistry(TimeProvider.System), null!, counter, c.Tabs, NullLogger<SessionLifetime>.Instance);
        counter.Opened();
        await c.Space.EnsureAsync(default);             // as the circuit's opening does: the session exists
        await life.OnConnectionUpAsync(null!, default);
        await life.OnConnectionUpAsync(null!, default); // told twice: counted once
        Assert.Equal(1, counter.Connected);
        Assert.False(Stoppable(counter));               // a browser is attached

        await life.OnConnectionDownAsync(null!, default); // the browser is killed
        Assert.Equal((1, 0), (counter.Count, counter.Connected));
        Assert.False(Stoppable(counter));               // the session still holds its tabs: the person may come back

        await life.OnConnectionUpAsync(null!, default);   // ... and does (a reconnect)
        Assert.Equal(1, counter.Connected);
        await life.OnConnectionDownAsync(null!, default);

        _states.End("frank", "sid-5");                  // the session clock ends the session
        Assert.Equal(1, counter.Count);                 // the framework still keeps the circuit
        Assert.True(Stoppable(counter));                // and the worker can go all the same

        await life.OnConnectionUpAsync(null!, default);
        await life.OnCircuitClosedAsync(null!, default); // closed without a "down" first
        Assert.Equal((0, 0), (counter.Count, counter.Connected));
        await c.DisposeAsync();
    }

    private bool Stoppable(ChuvadiReader.Web.Hosting.Workers.CircuitCounter counter)
        => ChuvadiReader.Web.Hosting.Workers.WorkerPool.NobodyLeft(new(0, counter.Count, _states.Count, counter.Connected));

    [Fact]
    public async Task A_remembered_text_encoding_stays_inside_the_persons_session()
    {
        // D-191 on the portal: the choice lives with the file's Recents entry, and Recents is the session's.
        // A reload keeps it; another person, and the same person's other sign-in, never see it (nor the file's
        // name); the end of the session forgets it.
        var first = new Connection(_states, _images, _options, new As("gita", "sid-6"));
        var path = await UploadAsync(first, "notes.txt");
        var recents = new ChuvadiReader.Core.Documents.RecentFilesService(first.Storage);
        await recents.HydrateAsync();
        await recents.TouchAsync(new ChuvadiReader.Core.Documents.RecentItem("notes.txt", path, DocumentFormat.Text, DateTimeOffset.UtcNow, false));
        Assert.True(await recents.SetTextEncodingAsync(path, 1252));

        var reloaded = new Connection(_states, _images, _options, new As("gita", "sid-6"));
        var again = new ChuvadiReader.Core.Documents.RecentFilesService(reloaded.Storage);
        await again.HydrateAsync();
        Assert.Equal(1252, again.TextEncodingFor(path));

        foreach (var other in new[] { new As("hari", "sid-7"), new As("gita", "sid-8") })
        {
            var theirs = new Connection(_states, _images, _options, other);
            var seen = new ChuvadiReader.Core.Documents.RecentFilesService(theirs.Storage);
            await seen.HydrateAsync();
            Assert.Null(seen.TextEncodingFor(path));
            Assert.DoesNotContain(seen.Items, i => i.Path == path || i.FileName == "notes.txt");
            Assert.False(await seen.SetTextEncodingAsync(path, 1200)); // nor can they set one for a file that isn't theirs
            await theirs.DisposeAsync();
        }

        Assert.Equal(1252, again.TextEncodingFor(path)); // untouched by the others
        await first.DisposeAsync();
        await reloaded.DisposeAsync();
        _states.End("gita", "sid-6");
        var afterEnd = new Connection(_states, _images, _options, new As("gita", "sid-6"));
        var fresh = new ChuvadiReader.Core.Documents.RecentFilesService(afterEnd.Storage);
        await fresh.HydrateAsync();
        Assert.Null(fresh.TextEncodingFor(path));
        Assert.DoesNotContain(fresh.Items, i => i.Path == path);
        await afterEnd.DisposeAsync();
    }

    [Fact]
    public async Task Arranges_kept_desks_survive_a_reload_stay_with_the_session_and_end_with_it()
    {
        // D-203 on the portal: the Core keeps Arrange's desks in the platform's app-data folder, which on the
        // portal is the signed-in session's own folder.
        var first = new Connection(_states, _images, _options, new As("jaya", "sid-10"));
        await first.Space.EnsureAsync(default);
        var kept = Path.Combine(new SessionAppPaths(first.Space).AppDataFolder, "arrange-kept.json");
        await File.WriteAllTextAsync(kept, "{\"desks\":[]}");
        Assert.True(first.Space.Contains(kept));

        var reloaded = new Connection(_states, _images, _options, new As("jaya", "sid-10"));
        await reloaded.Space.EnsureAsync(default);
        Assert.Equal(kept, Path.Combine(new SessionAppPaths(reloaded.Space).AppDataFolder, "arrange-kept.json"));
        Assert.True(File.Exists(kept));

        foreach (var other in new[] { new As("kiran", "sid-11"), new As("jaya", "sid-12") })
        {
            var theirs = new Connection(_states, _images, _options, other);
            await theirs.Space.EnsureAsync(default);
            Assert.False(File.Exists(Path.Combine(new SessionAppPaths(theirs.Space).AppDataFolder, "arrange-kept.json")));
            await theirs.DisposeAsync();
        }

        await first.DisposeAsync();
        await reloaded.DisposeAsync();
        _states.End("jaya", "sid-10");
        Assert.False(File.Exists(kept));
    }

    [Fact]
    public async Task An_ended_session_keeps_nothing_a_stale_connection_writes()
    {
        var stale = new Connection(_states, _images, _options, new As("dave", "sid-3"));
        await stale.Storage.SetAsync("tabs", "[]");
        stale.Space.Delete(); // sign-out or expiry reached this connection
        await stale.Storage.SetAsync("tabs", "[{\"Path\":\"x\"}]");
        Assert.Null(await stale.Storage.GetAsync("tabs"));
        Assert.False(stale.Space.Contains(Path.Combine(stale.Space.Root, "uploads", "x.pdf")));
        await stale.DisposeAsync();
    }
}
