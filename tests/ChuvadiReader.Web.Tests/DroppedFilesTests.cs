using System.Security.Claims;
using ChuvadiReader.Core.Lifecycle;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-89 A: files dropped on the portal get the upload's checks and open in the Reader.</summary>
[System.Runtime.Versioning.UnsupportedOSPlatform("windows")]
public class DroppedFilesTests
{
    private sealed class SignedIn : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync()
            => Task.FromResult(new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", "drop-user")], "test"))));
    }

    private readonly string _root = SpaceLayoutTests.NewTempDir();
    private readonly OpenDocumentService _open = new();
    private readonly SessionSpace _space;
    private readonly WebDroppedFiles _drops;

    public DroppedFilesTests()
    {
        var options = Options.Create(new PortalOptions { DataRoot = _root, MaxUploadBytes = 64 * 1024 });
        _space = new SessionSpace(new SignedIn(), options, NullLogger<SessionSpace>.Instance);
        var ready = new AppReadySignal();
        ready.SignalReady();
        var incoming = new IncomingFiles(new BenchDropService(), _open, ready, new NoAppInstance());
        _drops = new WebDroppedFiles(_space, incoming, options, NullLogger<WebDroppedFiles>.Instance);
    }

    private static readonly byte[] Pdf = "%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"u8.ToArray();

    private static DroppedFile File(string name, byte[] bytes, long? announced = null)
        => new(name, announced ?? bytes.Length, _ => new MemoryStream(bytes));

    private List<PendingOpen> Opened()
    {
        var list = new List<PendingOpen>();
        while (_open.TryTake(out var o))
        {
            list.Add(o);
        }

        return list;
    }

    [Fact]
    public async Task Dropped_documents_are_stored_privately_and_open_one_tab_each()
    {
        Assert.True(_drops.IsAvailable);
        Assert.Equal(64 * 1024, _drops.MaxFileBytes);

        var problems = await _drops.ReceiveAsync([File("report.pdf", Pdf), File("report.pdf", Pdf)]);
        Assert.Empty(problems);

        var opened = Opened();
        Assert.Equal(2, opened.Count);
        Assert.NotEqual(opened[0].Path, opened[1].Path); // same names never overwrite
        foreach (var o in opened)
        {
            Assert.True(_space.Contains(o.Path));
            Assert.Equal(Pdf, System.IO.File.ReadAllBytes(o.Path));
            Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite, System.IO.File.GetUnixFileMode(o.Path));
            Assert.Equal("report.pdf", Path.GetFileName(o.Path));
        }
    }

    [Fact]
    public async Task What_the_upload_refuses_is_refused_with_one_message_each_and_nothing_kept()
    {
        var problems = await _drops.ReceiveAsync(
        [
            File("setup.exe", [0x4D, 0x5A, 0x90, 0x00]),                 // not a document type
            File("fake.pdf", "just text, not a PDF"u8.ToArray()),       // content doesn't match
            File("huge.pdf", Pdf, announced: 1024 * 1024),               // over the limit
            File("empty.pdf", [], announced: 0),
            File("short.pdf", Pdf, announced: Pdf.Length + 100),         // the browser sent less than it said
            File("../../etc/passwd.pdf", Pdf),                            // folders stripped from the name
        ]);

        Assert.Equal(5, problems.Count);
        Assert.Contains(problems, p => p.StartsWith("setup.exe", StringComparison.Ordinal));
        Assert.Contains(problems, p => p.Contains("fake.pdf isn't a valid PDF", StringComparison.Ordinal));
        Assert.Contains(problems, p => p.Contains("huge.pdf is larger than", StringComparison.Ordinal));
        Assert.Contains(problems, p => p.Contains("empty.pdf is empty", StringComparison.Ordinal));
        Assert.Contains(problems, p => p.Contains("short.pdf didn't arrive completely", StringComparison.Ordinal));

        var opened = Assert.Single(Opened());                             // only the cleaned-name PDF
        Assert.True(_space.Contains(opened.Path));
        Assert.DoesNotContain("..", opened.Path);
        var kept = Directory.EnumerateFiles(_space.Uploads, "*", SearchOption.AllDirectories).ToList();
        Assert.Equal([opened.Path], kept);                                // refused files leave nothing behind
    }
}
