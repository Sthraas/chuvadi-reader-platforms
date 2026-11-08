using ChuvadiReader.Platform;
using ChuvadiReader.Ui.Components.Platform;
using Xunit;

namespace ChuvadiReader.WebUi.Tests;

/// <summary>Upload wording (coordinator 9 Nov 01:42) and Q-3's "this session" wording (D-119 c).</summary>
public class PortalWordingTests
{
    private sealed class Platform(PlatformKind kind) : IPlatformInfo
    {
        public PlatformKind Kind => kind;

        public FormFactor FormFactor => FormFactor.Desktop;

        public event Action? FormFactorChanged { add { } remove { } }

        public InputKinds Input => InputKinds.Mouse | InputKinds.Keyboard;

        public ShellChrome Chrome => new(ChuvadiReader.Platform.WindowButtons.None, false, true, false, 0);

        public PlatformCapabilities Capabilities => new();

        public IKeyLabels Keys => null!;
    }

    [Theory]
    [InlineData(PlatformKind.Windows)]
    [InlineData(PlatformKind.MacOS)]
    [InlineData(PlatformKind.Linux)]
    [InlineData(PlatformKind.Android)]
    public void Other_platforms_keep_their_fetch_wording_character_for_character(PlatformKind kind) =>
        Assert.Equal("Fetch a PDF to start.", PlatformText.FetchOrUpload(new Platform(kind), "Fetch a PDF to start.", "Upload a PDF to start."));

    [Fact]
    public void The_portal_says_upload() =>
        Assert.Equal("Upload a file", PlatformText.FetchOrUpload(new Platform(PlatformKind.Web), "Fetch a file", "Upload a file"));

    [Fact]
    public void Home_on_the_portal_speaks_of_this_session_only()
    {
        Assert.Equal("Files in this session", PlatformText.HomeStorageMapTitle);
        Assert.Equal("Nothing shelved this session — open the Library", PlatformText.HomeShelvesEmpty);
    }
}
