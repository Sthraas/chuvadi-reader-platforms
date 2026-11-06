using ChuvadiReader.Ui.Components.Legal;
using Xunit;

namespace ChuvadiReader.WebUi.Tests;

/// <summary>The Licences page shows exactly the files that ship beside the app.</summary>
public class LicenceTextTests
{
    private static string Repo(params string[] parts)
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d is not null && !File.Exists(Path.Combine(d.FullName, "LICENSE")))
        {
            d = d.Parent;
        }

        return Path.Combine([d!.FullName, .. parts]);
    }

    [Fact]
    public void Embedded_texts_match_the_shipped_files()
    {
        Assert.Equal(File.ReadAllText(Repo("legal", "EULA.txt")), LegalTexts.Eula);
        Assert.Equal(File.ReadAllText(Repo("legal", "THIRD-PARTY-NOTICES.txt")), LegalTexts.Notices);
        Assert.Equal(File.ReadAllText(Repo("LICENSE")), LegalTexts.Licence);
    }

    [Fact]
    public void Licence_is_proprietary_and_still_marked_for_legal_review()
    {
        Assert.Contains("Sthraas Intelligence Pvt Ltd", LegalTexts.Licence);
        Assert.Contains("not open-source software", LegalTexts.Licence);
        Assert.StartsWith("DRAFT FOR LEGAL REVIEW", LegalTexts.Eula);
    }
}
