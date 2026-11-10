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
        MacQuit.Install();
        WebKitPrewarm.Start(); // M-06: WebKit's content process starts while MAUI builds
        var app = MauiProgram.CreateMauiApp();
        _commands = app.Services.GetRequiredService<IAppCommands>();
        _shell = app.Services.GetRequiredService<ShellService>();
        MacMenuBar.Watch(_commands);
        return app;
    }

    /// <summary>Quit (⌘Q, Dock, logout): detach the page before MAUI and AppKit finish (Mac Test M-03).</summary>
    // M-21: Esc leaves Immersive even when the WebView does not have the keyboard (MacImmersive).
    // M-08 / M-23: ⌃Tab, ⌃⇧Tab and ⌘1…⌘9 reach the page (MacPageKeys).
    public override UIKeyCommand[] KeyCommands => new[] { MacImmersive.EscapeCommand() }.Concat(MacPageKeys.Commands()).ToArray();

    public override bool CanPerform(Selector action, NSObject? withSender) => action.Name switch
    {
        MacImmersive.EscapeSelector => MacImmersive.IsOn,
        MacPageKeys.Selector => MacPageKeys.Available,
        _ => base.CanPerform(action, withSender),
    };

    [Export(MacPageKeys.Selector)]
    public void OnPageKey(UIKeyCommand sender) => MacPageKeys.Handle(sender);

    [Export(MacImmersive.EscapeSelector)]
    public void OnImmersiveEscape(UIKeyCommand sender) => MacImmersive.SendEscapeToPage();

    public override void WillTerminate(UIApplication application)
    {
        MacQuit.Begin("will-terminate");
        base.WillTerminate(application);
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
        MacSmoke.Log("menu-command " + id);
        MainPage.Dispatch(async () => MacSmoke.Log($"menu-command {id} ran={await commands.InvokeAsync(id)}"));
    }
}
