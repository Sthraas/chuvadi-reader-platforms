namespace ChuvadiReader.Android.Platform;

/// <summary>
/// The third-party notices of the .NET runtime and .NET for Android that this app bundles, packed as
/// assets from the exact runtime packs of the build (see the ChuvadiRuntimeNotices target). Supplied
/// to the Licences page through Foundation's host-notices contract once it lands (coordinator
/// decision (a), 7 Nov). Read on demand only — never at startup.
/// </summary>
public static class RuntimeNotices
{
    private static readonly (string Asset, string Title)[] Parts =
    {
        ("notices/dotnet-runtime.txt", ".NET runtime and libraries"),
        ("notices/dotnet-android.txt", ".NET for Android"),
    };

    /// <summary>Both notices, each under its own heading; empty when the assets are missing.</summary>
    public static string Read()
    {
        var assets = global::Android.App.Application.Context.Assets;
        if (assets is null)
        {
            return string.Empty;
        }

        var text = new System.Text.StringBuilder();
        foreach (var (asset, title) in Parts)
        {
            try
            {
                using var stream = assets.Open(asset);
                using var reader = new StreamReader(stream);
                if (text.Length > 0)
                {
                    text.Append("\n\n");
                }

                text.Append(title).Append('\n').Append(new string('=', title.Length)).Append("\n\n").Append(reader.ReadToEnd());
            }
            catch (Java.IO.FileNotFoundException)
            {
                // Missing asset: the build target fails before this can ship.
            }
        }

        return text.ToString();
    }
}
