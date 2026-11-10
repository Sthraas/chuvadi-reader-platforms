using System.IO.Compression;
using System.Security.Claims;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Microsoft.JSInterop;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-129 (O-3, WT-16): a save that writes several files reaches the browser as one .zip.</summary>
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public sealed class ZipSaveTests : IAsyncDisposable
{
    private sealed class SignedIn : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync()
            => Task.FromResult(new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", "zip-user")], "test"))));
    }

    /// <summary>Records what the page is asked to download.</summary>
    private sealed class RecordingJs : IJSRuntime
    {
        public List<(string Url, string Name)> Downloads { get; } = new();

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, object?[]? args) => InvokeAsync<TValue>(identifier, CancellationToken.None, args);

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, CancellationToken cancellationToken, object?[]? args)
        {
            Assert.Equal("chvdPortal.download", identifier);
            Downloads.Add(((string)args![0]!, (string)args[1]!));
            return ValueTask.FromResult(default(TValue)!);
        }
    }

    private readonly RecordingJs _js = new();
    private readonly TransferRegistry _registry = new(TimeProvider.System);
    private readonly SessionSpace _space;
    private readonly OutboxDelivery _outbox;

    public ZipSaveTests()
    {
        var options = Options.Create(new PortalOptions { DataRoot = SpaceLayoutTests.NewTempDir() });
        _space = TestSessions.Space(new SignedIn(), options);
        _outbox = new OutboxDelivery(_space, _registry, new BrowserBridge(_js), options, TimeProvider.System, NullLogger<OutboxDelivery>.Instance);
    }

    public ValueTask DisposeAsync() => _outbox.DisposeAsync();

    private DownloadTicket Ticket(int i)
        => _registry.TakeDownload(_js.Downloads[i].Url[(_js.Downloads[i].Url.LastIndexOf('/') + 1)..], _space.UserKey)!;

    private async Task<string> FolderWithAsync(params (string Name, string Text)[] files)
    {
        await _space.EnsureAsync();
        var folder = _outbox.NewFolder(collect: true);
        foreach (var (name, text) in files)
        {
            var path = Path.Combine(folder, name);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            await File.WriteAllTextAsync(path, text);
        }

        return folder;
    }

    [Fact]
    public async Task Several_files_go_out_as_one_zip_that_holds_them_exactly()
    {
        var folder = await FolderWithAsync(("report-p1.pdf", "page one"), ("report-p2.pdf", "page two"), ("report-p3.pdf", "  double  spaces  "), ("images/report-p3.png", "png"));

        var result = await _outbox.DeliverAsync(folder);
        Assert.Equal(ChuvadiReader.Platform.WriteBackOutcome.Done, result.Outcome);
        var (_, name) = Assert.Single(_js.Downloads);
        Assert.Equal("report.zip", name);

        var zip = Ticket(0).Path;
        Assert.True(_space.Contains(zip));
        Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite, File.GetUnixFileMode(zip));

        // Read back with .NET's own reader (a test-only check that other tools open it), byte for byte.
        using (var archive = ZipFile.OpenRead(zip))
        {
            Assert.Equal(["images/report-p3.png", "report-p1.pdf", "report-p2.pdf", "report-p3.pdf"], archive.Entries.Select(e => e.FullName).Order(StringComparer.Ordinal));
            using var reader = new StreamReader(archive.GetEntry("report-p3.pdf")!.Open());
            Assert.Equal("  double  spaces  ", await reader.ReadToEndAsync());
        }

        // Committing the same folder again sends nothing new.
        await _outbox.DeliverAsync(folder);
        Assert.Single(_js.Downloads);
    }

    [Fact]
    public async Task One_file_goes_out_as_itself_and_a_later_single_addition_too()
    {
        var folder = await FolderWithAsync(("only.pdf", "one"));
        await _outbox.DeliverAsync(folder);
        Assert.Equal("only.pdf", Assert.Single(_js.Downloads).Name);

        await File.WriteAllTextAsync(Path.Combine(folder, "later.pdf"), "two");
        await _outbox.DeliverAsync(folder); // only the new file is new
        Assert.Equal("later.pdf", _js.Downloads[1].Name);
    }

    [Fact]
    public async Task A_picked_folder_isnt_sent_file_by_file_while_the_save_is_still_writing()
    {
        var folder = await FolderWithAsync(("a.pdf", "a"), ("b.pdf", "b"));
        await _outbox.ScanOnceAsync();
        await _outbox.ScanOnceAsync(); // a watched folder would have delivered both by now
        Assert.Empty(_js.Downloads);

        await _outbox.DeliverAsync(folder);
        Assert.Equal("Chuvadi files.zip", Assert.Single(_js.Downloads).Name);
    }

    [Fact]
    public async Task A_save_folder_still_downloads_each_finished_file()
    {
        await _space.EnsureAsync();
        var folder = _outbox.NewFolder(); // Save as: one file, watched
        await File.WriteAllTextAsync(Path.Combine(folder, "saved.pdf"), "x");
        await _outbox.ScanOnceAsync();
        await _outbox.ScanOnceAsync();
        Assert.Equal("saved.pdf", Assert.Single(_js.Downloads).Name);
    }

    [Theory]
    [InlineData("report.zip", "report-p1.pdf", "report-p2.pdf")]
    [InlineData("Scan 2026.zip", "Scan 2026 (1).png", "Scan 2026 (2).png")]
    [InlineData("Chuvadi files.zip", "a.pdf", "b.pdf")]
    [InlineData("ചുവടി.zip", "ചുവടി-1.pdf", "ചുവടി-2.pdf")]
    public void The_zip_is_named_after_what_the_files_share(string expected, params string[] names)
        => Assert.Equal(expected, ZipBundle.NameFor(names.Select(n => "/x/" + n).ToList()));
}
