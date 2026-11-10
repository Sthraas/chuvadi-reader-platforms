using ChuvadiReader.Core.Reader;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>Mac Test M-01 / M-11: the shell's own commands (Open, Settings, Go to …) reach IAppCommands.</summary>
public class GlobalCommandsTests
{
    private static ShellCommand Cmd(string id, string label, string? keys = null, Func<Task>? run = null, string? disabled = null)
        => new(id, label, "Go to", "home", keys, run ?? (() => Task.CompletedTask), disabled);

    [Fact]
    public void Publishing_the_same_commands_again_does_not_raise_Changed()
    {
        var shell = new ShellService();
        var raised = 0;
        shell.Changed += () => raised++;

        shell.SetGlobalCommands([Cmd("go.settings", "Settings"), Cmd("file.open", "Open a file…", "Ctrl O")]);
        shell.SetGlobalCommands([Cmd("go.settings", "Settings"), Cmd("file.open", "Open a file…", "Ctrl O")]);
        Assert.Equal(1, raised);

        shell.SetGlobalCommands([Cmd("go.settings", "Settings")]);
        Assert.Equal(2, raised);
        shell.SetGlobalCommands([Cmd("go.settings", "Settings", disabled: "busy")]);
        Assert.Equal(3, raised);
    }

    [Fact]
    public async Task IAppCommands_lists_the_shell_commands_first_and_runs_them()
    {
        var shell = new ShellService();
        var opened = 0;
        shell.RegisterCommands(this, [Cmd("r.print", "Print", "Ctrl P")]);
        shell.SetGlobalCommands([Cmd("go.settings", "Settings"), Cmd("file.open", "Open a file…", "Ctrl O", () => { opened++; return Task.CompletedTask; })]);

        var commands = new ShellAppCommands(shell);
        Assert.Equal(["go.settings", "file.open", "r.print"], commands.Commands.Select(c => c.Id));
        Assert.Equal("Ctrl O", commands.Commands.Single(c => c.Id == "file.open").Keys);

        Assert.True(await commands.InvokeAsync("file.open"));
        Assert.Equal(1, opened);
    }

    [Fact]
    public async Task A_disabled_shell_command_is_reported_and_not_run()
    {
        var shell = new ShellService();
        var ran = false;
        shell.SetGlobalCommands([Cmd("tools.ocr", "OCR", run: () => { ran = true; return Task.CompletedTask; }, disabled: "Coming soon")]);
        var commands = new ShellAppCommands(shell);

        var info = commands.Commands.Single();
        Assert.False(info.IsEnabled);
        Assert.False(await commands.InvokeAsync("tools.ocr"));
        Assert.False(ran);
    }
}
