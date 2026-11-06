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

    private static string _signature = string.Empty;

    /// <summary>Rebuilds the menu bar when the set of commands changes. Enabled state is not part of
    /// the signature — it is checked each time a menu opens (AppDelegate.ValidateCommand).</summary>
    public static void Watch(IAppCommands commands)
    {
        commands.Changed += () =>
        {
            var sig = Signature(commands);
            if (sig == _signature)
            {
                return;
            }

            _signature = sig;
            UIApplication.SharedApplication.BeginInvokeOnMainThread(() => UIMenuSystem.MainSystem.SetNeedsRebuild());
        };
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
