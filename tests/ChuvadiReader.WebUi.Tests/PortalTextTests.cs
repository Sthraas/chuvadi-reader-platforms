using ChuvadiReader.Ui.Components.Platform.Portal;
using Xunit;

namespace ChuvadiReader.WebUi.Tests;

public class AccountTextTests
{
    [Theory]
    [InlineData("Arun S.", "AS")]
    [InlineData("arun shiva balasubramanian", "AB")]
    [InlineData("Arun", "A")]
    [InlineData("  Arun   S.  ", "AS")]
    [InlineData("", "?")]
    [InlineData(null, "?")]
    [InlineData("(Records) Arun", "A")]
    public void Initials(string? name, string expected) => Assert.Equal(expected, AccountText.Initials(name));

    [Theory]
    [InlineData("Arun S.", "Arun")]
    [InlineData("Arun", "Arun")]
    [InlineData("   ", "")]
    [InlineData(null, "")]
    public void FirstName(string? name, string expected) => Assert.Equal(expected, AccountText.FirstName(name));
}

public class PortalCredentialsTests
{
    [Fact]
    public void ToString_never_contains_the_password()
    {
        var c = new PortalCredentials("arun.s@smh.sangam", "hunter2-secret");
        Assert.DoesNotContain("hunter2-secret", c.ToString());
        Assert.Contains("arun.s@smh.sangam", c.ToString());
    }

    [Fact]
    public void Sangam_id_is_passed_as_typed()
    {
        var c = new PortalCredentials("  Arun.S@SMH.sangam ", "x");
        Assert.Equal("  Arun.S@SMH.sangam ", c.SangamId);
    }
}

public class GatingRowsTests
{
    [Fact]
    public void Release1_list_has_no_sharing_row()
    {
        Assert.DoesNotContain(SangamGatingRow.Release1, r => r.Text.Contains("Share", StringComparison.OrdinalIgnoreCase));
        Assert.Equal(7, SangamGatingRow.Release1.Count);
    }
}
