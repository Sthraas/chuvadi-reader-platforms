using System.Text.RegularExpressions;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

public sealed class HostingTests
{
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

    private static ServiceProvider Build(AppStateLifetime lifetime)
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(lifetime);
        services.AddSingleton<IAppStorage, MemoryStorage>();
        return services.BuildServiceProvider(new ServiceProviderOptions { ValidateOnBuild = true, ValidateScopes = true });
    }

    [Theory]
    [InlineData(AppStateLifetime.Process)]
    [InlineData(AppStateLifetime.PerConnection)]
    public void Every_registered_service_resolves(AppStateLifetime lifetime)
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(lifetime);
        using var sp = Build(lifetime);
        using var scope = sp.CreateScope();
        foreach (var d in services)
        {
            Assert.NotNull(scope.ServiceProvider.GetService(d.ServiceType));
        }
    }

    [Fact]
    public void PerConnection_gives_each_connection_its_own_state()
    {
        using var sp = Build(AppStateLifetime.PerConnection);
        using var a = sp.CreateScope();
        using var b = sp.CreateScope();
        Assert.NotSame(a.ServiceProvider.GetRequiredService<TabsService>(), b.ServiceProvider.GetRequiredService<TabsService>());
        Assert.Same(a.ServiceProvider.GetRequiredService<TabsService>(), a.ServiceProvider.GetRequiredService<TabsService>());
    }

    [Fact]
    public void Host_registration_after_AddChuvadiReader_wins()
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(AppStateLifetime.Process);
        services.AddSingleton<IFileWriteBack, TestWriteBack>();
        services.AddSingleton<IAppStorage, MemoryStorage>();
        using var sp = services.BuildServiceProvider();
        Assert.IsType<TestWriteBack>(sp.GetRequiredService<IFileWriteBack>());
    }

    private sealed class TestWriteBack : IFileWriteBack
    {
        public bool IsNeeded => true;

        public Task<WriteBackResult> CommitAsync(string localPath, CancellationToken ct = default) =>
            Task.FromResult(new WriteBackResult(WriteBackOutcome.Done));
    }

    /// <summary>Drift guard: every Core service the Windows host registers is registered by the kit too.</summary>
    [Fact]
    public void Kit_registers_everything_the_Windows_host_registers()
    {
        var text = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "WindowsApp.xaml.cs.txt"));
        var windows = Regex.Matches(text, @"AddSingleton<([\w\.]+)(?:,\s*[\w\.]+)?>\(")
            .Select(m => m.Groups[1].Value.Split('.').Last())
            .ToHashSet();

        // Host-only seams the Windows host implements itself (not part of the shared kit's Core list).
        string[] hostSeams = ["IAppStorage", "IUiScale", "IExternalLinks", "IPrintService", "IFilePicker", "IImageClipboard"];

        var services = new ServiceCollection();
        services.AddChuvadiReader(AppStateLifetime.Process);
        var kit = services.Select(d => d.ServiceType.Name).ToHashSet();

        var missing = windows.Except(hostSeams).Except(kit).ToList();
        Assert.True(missing.Count == 0, "Registered by Windows but not by the kit: " + string.Join(", ", missing));
    }

    [Theory]
    [InlineData("Ctrl P", "⌘P")]
    [InlineData("Ctrl Shift S", "⇧⌘S")]
    [InlineData("Ctrl Alt W", "⌥⌘W")]
    [InlineData("Ctrl 1 … 9", "⌘1 … 9")]
    [InlineData("F11", "F11")]
    public void Mac_key_labels(string canonical, string expected) =>
        Assert.Equal(expected, new MacKeyLabels().Format(canonical));

    [Fact]
    public async Task App_commands_route_to_the_publisher()
    {
        var cmds = new AppCommands();
        string? ran = null;
        var changed = 0;
        cmds.Changed += () => changed++;
        cmds.Publish([new AppCommandInfo("doc.print", "Print", "Document", "Ctrl P", true)], id => { ran = id; return Task.CompletedTask; });
        await cmds.InvokeAsync("doc.print");
        Assert.Equal("doc.print", ran);
        Assert.Equal(1, changed);
        Assert.Single(cmds.Current);
    }
}
