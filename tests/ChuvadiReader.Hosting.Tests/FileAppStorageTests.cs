using ChuvadiReader.Hosting.Desktop;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>B-16: a settings folder that can't be created or written never stops the app.</summary>
public sealed class FileAppStorageTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "chvd-storage-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }

    [Fact]
    public async Task A_folder_that_cant_be_created_keeps_settings_in_memory()
    {
        // A regular file where a folder should be: CreateDirectory fails for every user, root included
        // (chmod alone doesn't stop root, which CI and containers often are).
        var blocker = Path.Combine(TempDir(), "not-a-folder");
        await File.WriteAllTextAsync(blocker, "x");

        var storage = new FileAppStorage(Path.Combine(blocker, "Chuvadi")); // no exception (B-16)
        Assert.False(storage.CanSave);
        Assert.False(string.IsNullOrEmpty(storage.CannotSaveReason));

        Assert.Null(storage.GetSync("theme"));
        await storage.SetAsync("theme", "Palm");
        Assert.Equal("Palm", await storage.GetAsync("theme"));
        Assert.Equal("Palm", storage.GetSync("theme"));
    }

    [Fact]
    public async Task A_save_that_fails_is_reported_once_and_the_session_keeps_its_values()
    {
        var dir = TempDir();
        Directory.CreateDirectory(Path.Combine(dir, "settings.json")); // a folder in the file's place: every write fails
        var storage = new FileAppStorage(dir);
        var reasons = new List<string>();
        storage.CannotSave += reasons.Add;

        await storage.SetAsync("theme", "Indigo");
        await storage.SetAsync("recents", "[]");

        Assert.Single(reasons);
        Assert.False(storage.CanSave);
        Assert.Equal("Indigo", await storage.GetAsync("theme"));
        Assert.Equal("[]", await storage.GetAsync("recents"));
    }

    [Fact]
    public async Task A_writable_folder_still_saves_to_disk()
    {
        var dir = TempDir();
        var storage = new FileAppStorage(dir);
        var reasons = new List<string>();
        storage.CannotSave += reasons.Add;

        await storage.SetAsync("theme", "Palm");

        Assert.True(storage.CanSave);
        Assert.Empty(reasons);
        Assert.Equal("Palm", new FileAppStorage(dir).GetSync("theme"));
    }

    [Fact]
    public void Settings_are_written_byte_for_byte_as_before_and_read_back_unchanged()
    {
        // AT-03: generated JSON instead of reflection. Same bytes, so every existing settings.json reads the same.
        var values = new Dictionary<string, string>
        {
            ["theme"] = "Palm",
            ["name"] = "Dr.  Arun  S. ",
            ["ta"] = "தமிழ் உரை",
            ["quote"] = "He said \"hi\" <b> & </b>",
            ["lines"] = "one\ntwo\ttab",
            ["emoji"] = "📄 ok",
            ["json"] = "[{\"Path\":\"C:\\\\x.pdf\"}]",
        };

#pragma warning disable IL2026, IL3050 // the old reflection path, kept here only to compare against
        var before = System.Text.Json.JsonSerializer.Serialize(values);
#pragma warning restore IL2026, IL3050
        var now = System.Text.Json.JsonSerializer.Serialize(values, SettingsJson.Default.DictionaryStringString);

        Assert.Equal(before, now);
        Assert.Equal(values, System.Text.Json.JsonSerializer.Deserialize(now, SettingsJson.Default.DictionaryStringString));
    }
}
