using ChuvadiReader.Platform;
using Foundation;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// The macOS menu bar (handout › Platforms: File, Edit, View, Document, Window, Help, ⌘ shortcuts),
/// built natively with UIKit's main-menu builder from <see cref="IAppCommands"/> — the Ui's own
/// command list, filled host-side by the Foundation kit. Nothing is duplicated: every item runs
/// through <see cref="IAppCommands.InvokeAsync"/>. Edit and Window stay the standard macOS menus.
/// </summary>
internal static class MacMenuBar
{
    /// <summary>Selector every Chuvadi menu item sends; AppDelegate handles it.</summary>
    public const string ActionSelector = "chvdMenuCommand:";

    /// <summary>Pseudo-id for "Find or do anything…" (the ⌘K command bar).</summary>
    public const string CommandBarId = "chvd.commandbar";

    /// <summary>Immersive full screen: macOS's own full-screen shortcut, ⌃⌘F (decision 6 Nov).</summary>
    private const string ImmersiveId = "r.immersive";

    // Ids that live under File on a Mac rather than in the Document menu.
    private static readonly string[] FileIds =
    {
        "file.open", "tab.close", "doc.close", "m.save", "m.saveas", "doc.print", "r.print",
        "doc.reveal", "doc.copypath", "a.session",
    };

    // Shortcuts macOS itself owns (Edit, app and window menus) — never claimed by Chuvadi items.
    private static readonly HashSet<string> Reserved = new(StringComparer.Ordinal)
    {
        "c", "v", "x", "a", "z", "q", "h", "m", ",", "`",
    };

    /// <summary>The Ui's Settings page command (MainLayout "Go to" group).</summary>
    private const string SettingsId = "go.settings";

    private static string _signature = string.Empty;
    private static int _builds;

    /// <summary>Rebuilds the menu bar whenever the set of commands changes. Enabled state is not part of
    /// the signature — it is checked each time a menu opens (AppDelegate.ValidateCommand).</summary>
    public static void Watch(IAppCommands commands)
    {
        // AppKit adds its own "Enter Full Screen" (⌃⌘F) to any menu titled View; Chuvadi's Immersive
        // takes ⌃⌘F instead (decision 6 Nov, Mac Test M-01). This default is how a Mac app opts out.
        NSUserDefaults.StandardUserDefaults.SetBool(false, "NSFullScreenMenuItemEverywhere");

        commands.Changed += () =>
        {
            var sig = Signature(commands);
            if (sig == _signature)
            {
                return;
            }

            _signature = sig;
            RequestRebuild("commands-changed");
        };
    }

    /// <summary>Asks UIKit to call BuildMenu again (main thread).</summary>
    public static void RequestRebuild(string reason)
    {
        void Rebuild()
        {
            MacSmoke.Log("menu-rebuild " + reason);
            UIMenuSystem.MainSystem.SetNeedsRebuild();
        }

        if (NSThread.IsMain)
        {
            Rebuild();
        }
        else
        {
            UIApplication.SharedApplication.BeginInvokeOnMainThread(Rebuild);
        }
    }

    private static string Signature(IAppCommands commands)
        => string.Join('|', commands.DocumentMenu.Select(c => c.IsSeparator ? "-" : c.Id + ':' + c.Label))
           + '#' + string.Join('|', commands.Commands.Select(c => c.Id + ':' + c.Label).Order(StringComparer.Ordinal));

    /// <summary>Finds a command by id now, so its enabled state is current.</summary>
    public static AppCommandInfo? Find(IAppCommands commands, string id)
        => commands.DocumentMenu.FirstOrDefault(c => !c.IsSeparator && c.Id == id)
           ?? commands.Commands.FirstOrDefault(c => c.Id == id);

    public static void Build(IUIMenuBuilder builder, IAppCommands source)
    {
        _builds++;
        try
        {
            BuildCore(builder, source);
            MacSmoke.Log($"menu-built #{_builds} commands={source.Commands.Count} document={source.DocumentMenu.Count}");
        }
        catch (Exception ex)
        {
            // A failed rebuild must never take the app down; the log says why (CI smoke run).
            MacSmoke.Log($"menu-build-failed #{_builds}: {ex.GetType().Name}: {ex.Message}");
            Console.Error.WriteLine("Chuvadi: menu build failed: " + ex);
        }
    }

    private static void BuildCore(IUIMenuBuilder builder, IAppCommands source)
    {
        // Menus that don't fit Chuvadi: Format, and Edit's text tools. Edit › Find is removed so
        // ⌘F reaches Chuvadi's own Find, as Ctrl F does on Windows.
        foreach (var id in new[]
                 {
                     UIMenuIdentifier.Format, UIMenuIdentifier.Find, UIMenuIdentifier.Spelling,
                     UIMenuIdentifier.Substitutions, UIMenuIdentifier.Transformations,
                     UIMenuIdentifier.Fullscreen, // its ⌃⌘F goes to Immersive
                 })
        {
            builder.RemoveMenu(id.GetConstant()!);
        }

        var commands = source.Commands;
        var docMenu = source.DocumentMenu;
        var keys = new HashSet<string>(StringComparer.Ordinal);

        // File — open, close, save, print, file actions.
        var file = new List<UIMenuElement>();
        AddSection(file, FileIds.Select(id => Find(source, id)).OfType<AppCommandInfo>(), keys);
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.File.GetConstant()!, _ => file.ToArray());

        // View — modes (1–4), view options, reading panels, places, ⌘K. The system's Enter Full
        // Screen item is replaced by Chuvadi's Immersive, which takes its ⌃⌘F (decision 6 Nov).
        var view = new List<UIMenuElement>();
        AddSection(view, commands.Where(c => c.Group == "Modes"), keys);
        AddSection(view, commands.Where(c => c.Group == "View"), keys);
        AddSection(view, commands.Where(c => c.Group == "Read" && !FileIds.Contains(c.Id)), keys);
        AddSection(view, commands.Where(c => c.Group == "Go to"), keys);
        view.Add(Inline(new UIMenuElement[] { Item(CommandBarId, "Find or do anything…", "Ctrl K", isEnabled: true, keys) }));
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.View.GetConstant()!, _ => view.ToArray());

        // Document — the active page's Document ▾ menu in its own order (separators become
        // sections), then the current mode's tools and the general tools as submenus.
        var doc = new List<UIMenuElement>();
        var section = new List<AppCommandInfo>();
        foreach (var c in docMenu.Append(new AppCommandInfo("sep.end", string.Empty, string.Empty, null, true, IsSeparator: true)))
        {
            if (c.IsSeparator)
            {
                AddSection(doc, section, keys);
                section = new List<AppCommandInfo>();
            }
            else if (!FileIds.Contains(c.Id))
            {
                section.Add(c);
            }
        }

        foreach (var group in new[] { "Mark", "Protect", "Arrange", "Tools" })
        {
            var items = commands
                .Where(c => c.Group == group && !FileIds.Contains(c.Id) && docMenu.All(d => d.Id != c.Id))
                .ToList();
            if (items.Count > 0)
            {
                doc.Add(UIMenu.Create(group, null, UIMenuIdentifier.None, (UIMenuOptions)0,
                    items.Select(c => (UIMenuElement)Item(c, keys)).ToArray()));
            }
        }

        var document = UIMenu.Create("Document", null, UIMenuIdentifier.None, (UIMenuOptions)0, doc.ToArray());
        builder.InsertSiblingMenuAfter(document, UIMenuIdentifier.View.GetConstant()!);

        // Chuvadi menu: Settings… ⌘, (Mac Test M-11), where every Mac app has it.
        if (Find(source, SettingsId) is not null)
        {
            var settings = UIKeyCommand.Create((NSString)"Settings…", null, new Selector(ActionSelector), (NSString)",",
                UIKeyModifierFlags.Command, new NSString(SettingsId));
            // Catalyst keeps a hidden, empty Preferences menu; an item put in it never showed (Mac Test run on
            // b41f25c). Remove it and put Settings… in its own section right after About Chuvadi, as macOS apps do.
            var hadPreferences = builder.GetMenu(UIMenuIdentifier.Preferences.GetConstant()!) is not null;
            if (hadPreferences)
            {
                builder.RemoveMenu(UIMenuIdentifier.Preferences.GetConstant()!);
            }

            // As its own inline section inside About's menu: a separate sibling menu needs an identifier of its own,
            // and one sharing "None" with the Document menu was silently dropped by the builder.
            var settingsSection = UIMenu.Create(string.Empty, null, UIMenuIdentifier.None, UIMenuOptions.DisplayInline, new UIMenuElement[] { settings });
            builder.ReplaceChildrenOfMenu(UIMenuIdentifier.About.GetConstant()!, children => children.Append(settingsSection).ToArray());
            MacSmoke.Log($"menu-settings inserted (system Preferences menu {(hadPreferences ? "removed" : "absent")})");
            if (MacSmoke.Enabled && builder.GetMenu(UIMenuIdentifier.Application.GetConstant()!) is { } appMenu)
            {
                // M-11 diagnosis: what UIKit's builder holds for the app menu, before AppKit turns it into NSMenu.
                static string Describe(UIMenuElement e) => e switch
                {
                    UIMenu m => $"[{m.Identifier} {m.Title}: {string.Join(", ", m.Children.Select(Describe))}]",
                    UICommand c => $"{c.Title}{(c is UIKeyCommand k ? " key=" + k.Input + "/" + k.ModifierFlags : string.Empty)}",
                    _ => e.Title,
                };
                MacSmoke.Log("menu-app-builder " + Describe(appMenu));
            }
        }

        // Help keeps only macOS's own menu search field.
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.Help.GetConstant()!, _ => Array.Empty<UIMenuElement>());
    }

    private static void AddSection(List<UIMenuElement> target, IEnumerable<AppCommandInfo> commands, HashSet<string> keys)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var items = commands
            .Where(c => seen.Add(c.Label)) // the same action can be registered by two owners
            .Select(c => (UIMenuElement)Item(c, keys))
            .ToArray();
        if (items.Length > 0)
        {
            target.Add(Inline(items));
        }
    }

    private static UIMenu Inline(UIMenuElement[] items)
        => UIMenu.Create(string.Empty, null, UIMenuIdentifier.None, UIMenuOptions.DisplayInline, items);

    private static UICommand Item(AppCommandInfo c, HashSet<string> keys)
        => Item(c.Id, c.Label, c.Id == ImmersiveId ? "Ctrl Control F" : c.Keys, c.IsEnabled, keys);

    private static UICommand Item(string id, string label, string? shortcut, bool isEnabled, HashSet<string> keys)
    {
        var sel = new Selector(ActionSelector);
        var payload = new NSString(id);
        UICommand command;
        if (TryMacKey(shortcut, out var input, out var flags) && keys.Add(input + (long)flags))
        {
            command = UIKeyCommand.Create((NSString)label, null, sel, (NSString)input, flags, payload);
        }
        else
        {
            command = UICommand.Create(label, null, sel, payload);
        }

        if (!isEnabled)
        {
            command.Attributes = UIMenuElementAttributes.Disabled;
        }

        return command;
    }

    /// <summary>"Ctrl P" → ⌘P, "Ctrl Shift S" → ⇧⌘S, "Ctrl ]" → ⌘]; "Control" adds ⌃. Shortcuts
    /// without Ctrl (single keys like R or 1–4) stay with the page, so typing is never captured.</summary>
    public static bool TryMacKey(string? keys, out string input, out UIKeyModifierFlags flags)
    {
        input = string.Empty;
        flags = 0;
        if (string.IsNullOrWhiteSpace(keys))
        {
            return false;
        }

        var parts = keys.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (!parts.Contains("Ctrl"))
        {
            return false;
        }

        flags = UIKeyModifierFlags.Command;
        if (parts.Contains("Shift"))
        {
            flags |= UIKeyModifierFlags.Shift;
        }

        if (parts.Contains("Alt"))
        {
            flags |= UIKeyModifierFlags.Alternate;
        }

        if (parts.Contains("Control"))
        {
            flags |= UIKeyModifierFlags.Control;
        }

        var key = parts[^1];
        if (key.Length != 1)
        {
            return false;
        }

        input = key.ToLowerInvariant();
        return !(flags == UIKeyModifierFlags.Command && Reserved.Contains(input));
    }
}
