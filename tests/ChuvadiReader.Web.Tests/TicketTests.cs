using ChuvadiReader.Web.Files;

namespace ChuvadiReader.Web.Tests;

public class TicketTests
{
    private sealed class ManualTime : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = new(2026, 11, 6, 0, 0, 0, TimeSpan.Zero);

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private static readonly string A = new('a', 32);
    private static readonly string B = new('b', 32);

    [Fact]
    public void A_download_works_once_and_only_for_its_owner()
    {
        var reg = new TransferRegistry(TimeProvider.System);
        var d = reg.CreateDownload(A, "s1", "/x/y.pdf", "y.pdf", TimeSpan.FromMinutes(1), deleteAfter: false);
        Assert.Null(reg.TakeDownload(d.Id, B));
        Assert.NotNull(reg.TakeDownload(d.Id, A));
        Assert.Null(reg.TakeDownload(d.Id, A));
    }

    [Fact]
    public void Expired_tickets_are_refused_and_pruned()
    {
        var time = new ManualTime();
        var reg = new TransferRegistry(time);
        var d = reg.CreateDownload(A, "s1", "/x", "x", TimeSpan.FromMinutes(1), false);
        var u = reg.CreateUpload(A, "s1", SpaceLayoutTests.NewTempDir(), PickKind.Pdf, false, 1, 10, TimeSpan.FromMinutes(1));
        var p = reg.CreatePrint(A, "s1", "/x.pdf", "x", TimeSpan.FromMinutes(1));
        time.Now += TimeSpan.FromMinutes(2);
        Assert.Null(reg.FindUpload(u.Id, A));
        Assert.Null(reg.FindPrint(p.Id, A));
        Assert.Null(reg.TakeDownload(d.Id, A));
        Assert.Equal(2, reg.Prune()); // the expired download was already dropped by the take
        Assert.Equal(0, reg.Count);
    }

    [Fact]
    public void Ending_a_session_forgets_only_its_tickets()
    {
        var reg = new TransferRegistry(TimeProvider.System);
        reg.CreateDownload(A, "s1", "/x", "x", TimeSpan.FromMinutes(1), false);
        reg.CreatePrint(A, "s1", "/x.pdf", "x", TimeSpan.FromMinutes(1));
        var keep = reg.CreateDownload(A, "s2", "/y", "y", TimeSpan.FromMinutes(1), false);
        reg.ForgetSession("s1");
        Assert.Equal(1, reg.Count);
        Assert.NotNull(reg.TakeDownload(keep.Id, A));
    }

    [Fact]
    public void Tokens_are_unguessable_and_url_safe()
    {
        var tokens = Enumerable.Range(0, 1000).Select(_ => TransferRegistry.NewToken()).ToList();
        Assert.Equal(1000, tokens.Distinct(StringComparer.Ordinal).Count());
        Assert.All(tokens, t => Assert.Matches("^[A-Za-z0-9_-]{32}$", t));
    }
}
