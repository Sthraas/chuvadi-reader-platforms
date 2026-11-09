using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>Mac Test M-08 / M-10: macOS conventions in shared Ui files, checked in the source that ships.</summary>
public class MacConventionsTests
{
    private static string Repo(params string[] parts)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "Directory.Build.props")))
        {
            dir = dir.Parent;
        }

        Assert.NotNull(dir);
        return File.ReadAllText(Path.Combine([dir!.FullName, .. parts]));
    }

    [Fact]
    public void Tab_cycling_accepts_control_tab_so_it_works_on_a_mac_M08()
    {
        var js = Repo("src", "ChuvadiReader.Ui", "wwwroot", "js", "reader.js");
        Assert.Contains("e.key === 'Tab' && e.ctrlKey === true && e.metaKey !== true", js);
    }

    [Fact]
    public void Mac_green_light_is_zoom_in_both_states_M10()
    {
        var razor = Repo("src", "ChuvadiReader.Ui", "Components", "Platform", "WindowButtons.razor");
        Assert.DoesNotContain("Exit full screen", razor);
        Assert.Contains("class=\"tl tl-max\" @onclick=\"() => Win.ToggleMaximize()\" aria-label=\"Zoom\"", razor);
    }
}
