using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>D-101: <see cref="IPlatformInfo.ChromeChanged"/> — the live window-button layout (Linux).</summary>
public sealed class ChromeChangedTests
{
    /// <summary>A host whose chrome changes at run time, as the Linux host does when GTK's setting changes.</summary>
    private sealed class LiveChrome : IPlatformInfo
    {
        public PlatformKind Kind => PlatformKind.Linux;

        public FormFactor FormFactor => FormFactor.Desktop;

        public event Action? FormFactorChanged { add { } remove { } }

        public InputKinds Input => InputKinds.Mouse | InputKinds.Keyboard;

        public ShellChrome Chrome { get; private set; } = new(WindowButtons.Right, false, false, true, 12)
        {
            ButtonLayout = new([], [WindowButton.Minimize, WindowButton.Maximize, WindowButton.Close]),
        };

        public event Action? ChromeChanged;

        public PlatformCapabilities Capabilities => FixedPlatformInfo.DesktopCapabilities;

        public IKeyLabels Keys { get; } = new CtrlKeyLabels();

        public void Set(WindowButtonLayout layout)
        {
            Chrome = Chrome with { ButtonLayout = layout };
            ChromeChanged?.Invoke();
        }
    }

    [Fact]
    public void A_host_that_never_changes_its_chrome_needs_no_code_and_never_raises_it()
    {
        IPlatformInfo fixedInfo = new FixedPlatformInfo(PlatformKind.Windows, InputKinds.Mouse | InputKinds.Keyboard,
            new ShellChrome(WindowButtons.Right, false, false, true, 0), FixedPlatformInfo.DesktopCapabilities, new CtrlKeyLabels());
        var raised = 0;
        void Handler() => raised++;

        fixedInfo.ChromeChanged += Handler; // the interface's default: does nothing
        fixedInfo.ChromeChanged -= Handler;

        Assert.Equal(0, raised);
    }

    [Fact]
    public void Listeners_see_the_new_layout_when_it_is_raised_and_stop_after_unsubscribing()
    {
        var host = new LiveChrome();
        IPlatformInfo info = host;
        var seen = new List<WindowButtonLayout?>();
        void Handler() => seen.Add(info.Chrome.ButtonLayout);
        info.ChromeChanged += Handler;

        host.Set(new([WindowButton.Close], [])); // GNOME Tweaks: "close:" (close only, on the left)
        info.ChromeChanged -= Handler;
        host.Set(new([], [WindowButton.Close]));

        var only = Assert.Single(seen);
        Assert.Equal([WindowButton.Close], only!.Left);
        Assert.Empty(only.Right);
    }
}
