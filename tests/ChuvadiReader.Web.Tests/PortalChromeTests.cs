using System.Text.Json.Nodes;
using ChuvadiReader.Ui.Components.Platform.Portal;
using ChuvadiReader.Web.Auth;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>What the host gives the portal chrome components from the combined patch (12a, 12b; D-35).</summary>
public class PortalChromeTests(PortalFixture portal) : IClassFixture<PortalFixture>
{
    [Fact]
    public void Portal_links_come_from_configuration_with_empty_values_hidden()
    {
        var links = portal.App.Services.GetRequiredService<PortalLinks>();
        Assert.Equal("https://chuvadi.in/download", links.DesktopAppUrl);
        Assert.Null(links.AccountSettingsUrl);
    }

    [Fact]
    public void Unit_is_the_name_of_sangams_current_organisation_claim()
    {
        var asObject = new JsonObject { ["id"] = Guid.NewGuid().ToString("D"), ["name"] = " Records ", ["path"] = "/apulki/records" };
        Assert.Equal("Records", SangamSignIn.OrganisationName(asObject));
        Assert.Equal("Records", SangamSignIn.OrganisationName(JsonValue.Create(asObject.ToJsonString())));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("not json")]
    [InlineData("[\"Records\"]")]
    [InlineData("{\"name\": 7}")]
    [InlineData("{\"name\": \"   \"}")]
    public void Malformed_organisation_claims_give_no_unit(string? text)
    {
        Assert.Null(SangamSignIn.OrganisationName(text is null ? null : JsonValue.Create(text)));
    }
}
