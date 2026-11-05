using ChuvadiReader.Core.Reader;
using Foundation;
using ObjCRuntime;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// The macOS menu bar (handout › Platforms: File, Edit, View, Document, Window, Help, with ⌘
/// shortcuts). Built natively with UIKit's main-menu builder, entirely from the commands the Ui
/// already publishes into Core's <see cref="ShellService"/> (ids, groups, labels, shortcuts,
/// actions, disabled reasons) — no Ui code is changed and no command logic is duplicated.
/// Edit and Window stay the standard macOS menus.
/// </summary>
internal static class MacMenuBar
{
    /// <summary>Selector every Chuvadi menu item sends; AppDelegate handles it.</summary>
    public const string ActionSelector = "chvdMenuCommand:";

    /// <summary>Pseudo-id for the ⌘K command bar (ShellService.OpenCommandBar).</summary>
    public const string CommandBarId = "chvd.commandbar";

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

    private static string _signature = string.Empty;

    /// <summary>Rebuilds the menu bar when the published command set changes. Enabled state is
    /// not part of the signature — it is checked each time a menu opens (ValidateCommand).</summary>
    public static void Watch(ShellService shell)
    {
        shell.Changed += () =>
        {
            var sig = Signature(shell);
            if (sig == _signature)
            {
                return;
            }

            _signature = sig;
            UIApplication.SharedApplication.BeginInvokeOnMainThread(() => UIMenuSystem.MainSystem.SetNeedsRebuild());
        };
    }

    private static string Signature(ShellService shell)
        => string.Join('|', shell.DocumentMenu.Select(c => c.Id + ':' + c.Label))
           + '#' + string.Join('|', shell.Commands.Select(c => c.Id + ':' + c.Label).Order(StringComparer.Ordinal));

    /// <summary>Finds a command by id at the moment it is used, so its action is current.</summary>
    public static ShellCommand? Find(ShellService shell, string id)
        => shell.DocumentMenu.FirstOrDefault(c => c.Id == id) ?? shell.Commands.FirstOrDefault(c => c.Id == id);

    public static void Build(IUIMenuBuilder builder, ShellService shell)
    {
        // Menus that don't fit Chuvadi: Format, and Edit's text tools. Edit › Find is removed so
        // ⌘F reaches Chuvadi's own Find, as Ctrl F does on Windows.
        foreach (var id in new[]
                 {
                     UIMenuIdentifier.Format, UIMenuIdentifier.Find, UIMenuIdentifier.Spelling,
                     UIMenuIdentifier.Substitutions, UIMenuIdentifier.Transformations,
                 })
        {
            builder.RemoveMenu(id.GetConstant()!);
        }

        var commands = shell.Commands;
        var docMenu = shell.DocumentMenu;
        var keys = new HashSet<string>(StringComparer.Ordinal);

        // File — open, close, save, print, file actions.
        var file = new List<UIMenuElement>();
        AddSection(file, FileIds.Select(id => Find(shell, id)).OfType<ShellCommand>(), keys);
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.File.GetConstant()!, _ => file.ToArray());

        // View — modes (1–4), view options, reading panels, places, ⌘K. The system's
        // Enter Full Screen item is kept.
        var view = new List<UIMenuElement>();
        AddSection(view, commands.Where(c => c.Group == "Modes"), keys);
        AddSection(view, commands.Where(c => c.Group == "View"), keys);
        AddSection(view, commands.Where(c => c.Group == "Read" && !FileIds.Contains(c.Id)), keys);
        AddSection(view, commands.Where(c => c.Group == "Go to"), keys);
        view.Add(Inline(new[] { Item(CommandBarId, "Find or do anything…", "Ctrl K", isEnabled: true, keys) }));
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.View.GetConstant()!, old =>
            view.Concat(old.Where(IsFullscreen)).ToArray());

        // Document — the Document ▾ menu the active page publishes, then the current mode's
        // tools and the general tools as submenus.
        var doc = new List<UIMenuElement>();
        AddSection(doc, docMenu.Where(c => !c.Id.StartsWith("sep", StringComparison.Ordinal) && !FileIds.Contains(c.Id)), keys);
        foreach (var group in new[] { "Mark", "Protect", "Arrange", "Tools" })
        {
            var items = commands.Where(c => c.Group == group && !FileIds.Contains(c.Id) && docMenu.All(d => d.Id != c.Id)).ToList();
            if (items.Count > 0)
            {
                doc.Add(UIMenu.Create(group, null, UIMenuIdentifier.None, (UIMenuOptions)0,
                    items.Select(c => (UIMenuElement)Item(c, keys)).ToArray()));
            }
        }

        var document = UIMenu.Create("Document", null, UIMenuIdentifier.None, (UIMenuOptions)0, doc.ToArray());
        builder.InsertSiblingMenuAfter(document, UIMenuIdentifier.View.GetConstant()!);

        // Help keeps only macOS's own menu search field.
        builder.ReplaceChildrenOfMenu(UIMenuIdentifier.Help.GetConstant()!, _ => Array.Empty<UIMenuElement>());
    }

    private static bool IsFullscreen(UIMenuElement e)
        => e is UIMenu m && m.Identifier == UIMenuIdentifier.Fullscreen;

    private static void AddSection(List<UIMenuElement> target, IEnumerable<ShellCommand> commands, HashSet<string> keys)
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

    private static UICommand Item(ShellCommand c, HashSet<string> keys)
        => Item(c.Id, c.Label, c.Keys, c.IsEnabled, keys);

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

    /// <summary>"Ctrl P" → ⌘P, "Ctrl Shift S" → ⇧⌘S, "Ctrl ]" → ⌘]. Shortcuts without Ctrl
    /// (single keys like R or 1–4) stay with the page, so typing is never captured.</summary>
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

        var key = parts[^1];
        if (key.Length != 1)
        {
            return false;
        }

        input = key.ToLowerInvariant();
        return !(flags == UIKeyModifierFlags.Command && Reserved.Contains(input));
    }
}
