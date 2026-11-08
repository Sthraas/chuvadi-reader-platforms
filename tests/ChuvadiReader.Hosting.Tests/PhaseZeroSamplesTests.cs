using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>H-12 (widened): the Phase 0 sample recents, pins and watched folder only on Windows.</summary>
public sealed class PhaseZeroSamplesTests
{
    private sealed class Empty : IAppStorage
    {
        public Task<string?> GetAsync(string key, CancellationToken ct = default) => Task.FromResult<string?>(null);

        public Task SetAsync(string key, string value, CancellationToken ct = default) => Task.CompletedTask;
    }

    private static IPlatformInfo On(PlatformKind kind) =>
        new FixedPlatformInfo(kind, InputKinds.Mouse | InputKinds.Keyboard,
            new ShellChrome(WindowButtons.None, false, false, false, 0), FixedPlatformInfo.DesktopCapabilities, new CtrlKeyLabels());

    [Theory]
    [InlineData(PlatformKind.Windows, true)]
    [InlineData(PlatformKind.MacOS, false)]
    [InlineData(PlatformKind.Linux, false)]
    [InlineData(PlatformKind.Android, false)]
    [InlineData(PlatformKind.Web, false)]
    public async Task A_fresh_install_shows_samples_only_on_Windows(PlatformKind kind, bool samples)
    {
        var platform = On(kind);
        var recents = new RecentFilesService(new Empty(), platform);
        var pins = new PinnedService(new Empty(), platform);
        var watched = new WatchedFolderService(new Empty(), platform);
        await recents.HydrateAsync();
        await pins.HydrateAsync();
        await watched.HydrateAsync();

        Assert.Equal(samples, recents.Items.Count > 0);
        Assert.Equal(samples, pins.Items.Count > 0);
        Assert.Equal(samples, watched.FolderPath is not null);
    }

    [Fact]
    public void Without_a_platform_nothing_changes() => Assert.True(PhaseZeroSamples.Shown(null));
}
