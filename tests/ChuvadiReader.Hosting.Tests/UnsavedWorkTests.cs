using ChuvadiReader.Core.Documents;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>D-190: what a host reads before its window closes is the tabs' own state, through the kit.</summary>
public sealed class UnsavedWorkTests
{
    private sealed class Marks : ITabMarks
    {
        public int Count { get; private set; } = 1;
        public bool HasUnsaved => Count > 0;
        public void Discard() => Count = 0;
    }

    private sealed class MemoryStorage : IAppStorage
    {
        private readonly Dictionary<string, string> _d = new();

        public Task<string?> GetAsync(string key, CancellationToken ct = default) =>
            Task.FromResult(_d.TryGetValue(key, out var v) ? v : null);

        public Task SetAsync(string key, string value, CancellationToken ct = default)
        {
            _d[key] = value;
            return Task.CompletedTask;
        }
    }

    [Fact]
    public async Task The_kit_registers_it_and_it_follows_the_tabs()
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(AppStateLifetime.Process);
        services.AddSingleton<IAppStorage>(new MemoryStorage());
        using var provider = services.BuildServiceProvider();
        var work = provider.GetRequiredService<IUnsavedWork>();
        var tabs = provider.GetRequiredService<TabsService>();

        var path = Path.Combine(Path.GetTempPath(), $"chvd-unsaved-{Guid.NewGuid():N}.txt");
        File.WriteAllText(path, "x");
        try
        {
            var tab = await tabs.OpenAsync(path, "x.txt", DocumentFormat.Text);
            Assert.False(work.HasUnsavedWork);
            Assert.True(await work.ConfirmCloseAsync());        // nothing unsaved: close at once, nothing asked

            tab.Marks = new Marks();
            Assert.True(work.HasUnsavedWork);
            Assert.True(await work.ConfirmCloseAsync());        // no Ui to ask (it is not up): never trap the person

            tabs.CloseGuard = _ => Task.FromResult(false);      // the Ui is up and the person chose Cancel
            Assert.False(await work.ConfirmCloseAsync());
            tabs.CloseGuard = unsaved => { unsaved[0].Marks!.Discard(); return Task.FromResult(true); };
            Assert.True(await work.ConfirmCloseAsync());
            Assert.False(work.HasUnsavedWork);
        }
        finally { File.Delete(path); }
    }
}
