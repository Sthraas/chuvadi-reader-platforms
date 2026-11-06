using ChuvadiReader.Core.Reader;
using ChuvadiReader.Mac.Platform;
using ChuvadiReader.Platform;
using Foundation;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac;

[Register("AppDelegate")]
public sealed class AppDelegate : MauiUIApplicationDelegate
{
    private IAppCommands? _commands;
    private ShellService? _shell;

    protected override MauiApp CreateMauiApp()
    {
        var app = MauiProgram.CreateMauiApp();
        _commands = app.Services.GetRequiredService<IAppCommands>();
        _shell = app.Services.GetRequiredService<ShellService>();
        MacMenuBar.Watch(_commands);
        return app;
    }

    /// <summary>The macOS menu bar, built from the Ui's commands (IAppCommands).</summary>
    public override void BuildMenu(IUIMenuBuilder builder)
    {
        base.BuildMenu(builder);
        if (builder.System == UIMenuSystem.MainSystem && _commands is not null)
        {
            MacMenuBar.Build(builder, _commands);
        }
    }

    /// <summary>Greys out an item whose command can't run now (checked each time a menu opens).</summary>
    public override void ValidateCommand(UICommand command)
    {
        base.ValidateCommand(command);
        if (command.Action == new Selector(MacMenuBar.ActionSelector)
            && _commands is not null
            && command.PropertyList is NSString id
            && id.ToString() != MacMenuBar.CommandBarId)
        {
            var c = MacMenuBar.Find(_commands, id.ToString());
            command.Attributes = c is { IsEnabled: true } ? 0 : UIMenuElementAttributes.Disabled;
        }
    }

    /// <summary>Runs a Chuvadi menu item on the Blazor dispatcher, exactly as the same click in the Ui.</summary>
    [Export(MacMenuBar.ActionSelector)]
    public void OnChuvadiMenuCommand(UICommand sender)
    {
        if (_commands is null || sender.PropertyList is not NSString nsId)
        {
            return;
        }

        var id = nsId.ToString();
        if (id == MacMenuBar.CommandBarId)
        {
            var shell = _shell;
            MainPage.Dispatch(() =>
            {
                shell?.OpenCommandBar();
                return Task.CompletedTask;
            });
            return;
        }

        var commands = _commands;
        MainPage.Dispatch(() => commands.InvokeAsync(id));
    }
}
