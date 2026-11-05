using ChuvadiReader.Core.Reader;
using ChuvadiReader.Mac.Platform;
using Foundation;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac;

[Register("AppDelegate")]
public sealed class AppDelegate : MauiUIApplicationDelegate
{
    private ShellService? _shell;

    protected override MauiApp CreateMauiApp()
    {
        var app = MauiProgram.CreateMauiApp();
        _shell = app.Services.GetRequiredService<ShellService>();
        MacMenuBar.Watch(_shell);
        return app;
    }

    /// <summary>The macOS menu bar, built from the commands the Ui publishes.</summary>
    public override void BuildMenu(IUIMenuBuilder builder)
    {
        base.BuildMenu(builder);
        if (builder.System == UIMenuSystem.MainSystem && _shell is not null)
        {
            MacMenuBar.Build(builder, _shell);
        }
    }

    /// <summary>Greys out an item when its command reports a reason it can't run now.</summary>
    public override void ValidateCommand(UICommand command)
    {
        base.ValidateCommand(command);
        if (command.Action == new Selector(MacMenuBar.ActionSelector)
            && _shell is not null
            && command.PropertyList is NSString id
            && id.ToString() != MacMenuBar.CommandBarId)
        {
            var c = MacMenuBar.Find(_shell, id.ToString());
            command.Attributes = c is { IsEnabled: true } ? 0 : UIMenuElementAttributes.Disabled;
        }
    }

    /// <summary>Runs a Chuvadi menu item on the Blazor dispatcher, exactly as a click in the Ui would.</summary>
    [Export(MacMenuBar.ActionSelector)]
    public void OnChuvadiMenuCommand(UICommand sender)
    {
        if (_shell is null || sender.PropertyList is not NSString nsId)
        {
            return;
        }

        var id = nsId.ToString();
        if (id == MacMenuBar.CommandBarId)
        {
            MainPage.Dispatch(() =>
            {
                _shell.OpenCommandBar();
                return Task.CompletedTask;
            });
            return;
        }

        if (MacMenuBar.Find(_shell, id) is { IsEnabled: true } command)
        {
            MainPage.Dispatch(command.Run);
        }
    }
}
