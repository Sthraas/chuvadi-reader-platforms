using System.Security.Claims;
using ChuvadiReader.Web.Files;
using Microsoft.Extensions.Logging.Abstractions;

namespace ChuvadiReader.Web.Tests;

public class SpaceLayoutTests
{
    [Theory]
    [InlineData("report.pdf", "report.pdf")]
    [InlineData("../../etc/passwd", "passwd")]
    [InlineData("..\\..\\boot.ini", "boot.ini")]
    [InlineData("a\u0000b\u001F.pdf", "ab.pdf")]
    [InlineData("   ", "document")]
    [InlineData("...", "document")]
    [InlineData("CON.pdf", "_CON.pdf")]
    [InlineData("com1.txt", "_com1.txt")]
    [InlineData("we<i>rd:na|me?.pdf", "weirdname.pdf")]
    public void SafeFileName_strips_folders_and_unsafe_characters(string input, string expected)
        => Assert.Equal(expected, SpaceLayout.SafeFileName(input, "document"));

    [Fact]
    public void SafeFileName_caps_length_and_keeps_extension()
    {
        var name = SpaceLayout.SafeFileName(new string('x', 300) + ".pdf", "d");
        Assert.Equal(120, name.Length);
        Assert.EndsWith(".pdf", name, StringComparison.Ordinal);
    }

    [Fact]
    public void IsInside_refuses_traversal_and_siblings()
    {
        var root = Path.Combine(Path.GetTempPath(), "chvd-root");
        Assert.True(SpaceLayout.IsInside(root, Path.Combine(root, "a", "b.pdf")));
        Assert.False(SpaceLayout.IsInside(root, Path.Combine(root, "..", "chvd-root-evil", "x")));
        Assert.False(SpaceLayout.IsInside(root, root + "-sibling/x"));
        Assert.False(SpaceLayout.IsInside(root, root));
    }

    [Fact]
    public void UserFolder_accepts_only_user_keys()
    {
        Assert.Throws<ArgumentException>(() => SpaceLayout.UserFolder("/data", "../../x"));
        Assert.Throws<InvalidOperationException>(() => SpaceLayout.UserFolder(" ", new string('a', 32)));
        Assert.EndsWith(Path.Combine("users", new string('a', 32)), SpaceLayout.UserFolder("/data", new string('a', 32)), StringComparison.Ordinal);
    }

    [Fact]
    public void UserKey_hashes_the_subject_and_needs_a_signed_in_person()
    {
        var a = Principal("person-a");
        var b = Principal("person-b");
        var keyA = UserKey.From(a)!;
        Assert.Equal(32, keyA.Length);
        Assert.True(keyA.All(char.IsAsciiHexDigitLower));
        Assert.Equal(keyA, UserKey.From(Principal("person-a")));
        Assert.NotEqual(keyA, UserKey.From(b));
        Assert.Null(UserKey.From(new ClaimsPrincipal(new ClaimsIdentity())));
        Assert.Null(UserKey.From(null));
    }

    [Fact]
    public void Sweep_removes_every_session_left_by_a_previous_run()
    {
        var root = NewTempDir();
        var s1 = Path.Combine(SpaceLayout.UserFolder(root, new string('a', 32)), "sessions", "s1", "uploads");
        var s2 = Path.Combine(SpaceLayout.UserFolder(root, new string('b', 32)), "sessions", "s2");
        Directory.CreateDirectory(s1);
        Directory.CreateDirectory(s2);
        File.WriteAllText(Path.Combine(s1, "x.pdf"), "x");

        var removed = SpaceLayout.SweepStaleSessions(root, TimeSpan.Zero, NullLogger.Instance);

        Assert.Equal(2, removed);
        Assert.Empty(Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories));
    }

    internal static ClaimsPrincipal Principal(string sub)
        => new(new ClaimsIdentity([new Claim("sub", sub)], "test"));

    internal static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "chvd-web-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }
}
