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

    [Fact]
    public async Task It_covers_Arrange_too_asks_about_it_first_and_says_when_the_answer_changes()
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(AppStateLifetime.Process);
        services.AddSingleton<IAppStorage>(new MemoryStorage());
        var data = Path.Combine(Path.GetTempPath(), $"chvd-unsaved-data-{Guid.NewGuid():N}");
        services.AddSingleton<IAppPaths>(new TempPaths(data));   // never the real app data: no kept desks from elsewhere
        using var provider = services.BuildServiceProvider();
        var work = provider.GetRequiredService<IUnsavedWork>();
        var tabs = provider.GetRequiredService<TabsService>();
        var bench = provider.GetRequiredService<BenchService>();
        int told = 0;
        work.Changed += () => told++;

        bench.EnsureDesk();
        await bench.EnsureRestoredAsync();                       // D-203: Arrange opened in this run
        bench.AddBlankToDesk(bench.Desks[0].Id);                 // arranging not kept for the next start yet
        Assert.True(work.HasUnsavedWork);
        Assert.Equal(1, told);

        var path = Path.Combine(Path.GetTempPath(), $"chvd-unsaved-{Guid.NewGuid():N}.txt");
        File.WriteAllText(path, "x");
        try
        {
            var tab = await tabs.OpenAsync(path, "x.txt", DocumentFormat.Text);
            tab.Marks = new Marks();
            tabs.NoteUnsavedMarksChanged();
            Assert.Equal(1, told);                                // already unsaved: nothing new to tell a host

            var order = new List<string>();
            bench.CloseGuard = () => { order.Add("arrange"); return Task.FromResult(true); };
            tabs.CloseGuard = _ => { order.Add("files"); return Task.FromResult(false); };
            Assert.False(await work.ConfirmCloseAsync());         // Cancel on a file, after Arrange said go ahead
            Assert.Equal(new[] { "arrange", "files" }, order);    // files last: their Discard is the one that destroys

            bench.MarkAllKept();
            Assert.True(work.HasUnsavedWork);                     // the marks are still unsaved
            Assert.Equal(1, told);
            tab.Marks.Discard();
            tabs.NoteUnsavedMarksChanged();
            Assert.False(work.HasUnsavedWork);
            Assert.Equal(2, told);                                // told once more: nothing is unsaved now
        }
        finally
        {
            File.Delete(path);
            try { Directory.Delete(data, true); } catch (IOException) { }
        }
    }

    private sealed class TempPaths(string root) : IAppPaths
    {
        public string AppDataFolder => root;
        public string WorkingFolder => Path.Combine(root, "work");
        public string? DefaultSaveFolder => null;
    }
}
