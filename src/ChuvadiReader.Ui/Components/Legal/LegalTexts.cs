using System.Reflection;

namespace ChuvadiReader.Ui.Components.Legal;

/// <summary>
/// The licence texts shipped with every host, embedded from the repository's <c>LICENSE</c> and
/// <c>legal/</c> folder (one source; nothing is read until the Licences page opens).
/// </summary>
public static class LegalTexts
{
    private static readonly Lazy<string> EulaText = new(() => Read("Chuvadi.Legal.EULA.txt"));
    private static readonly Lazy<string> NoticesText = new(() => Read("Chuvadi.Legal.THIRD-PARTY-NOTICES.txt"));
    private static readonly Lazy<string> LicenceText = new(() => Read("Chuvadi.Legal.LICENSE.txt"));

    /// <summary>End user licence agreement (legal/EULA.txt).</summary>
    public static string Eula => EulaText.Value;

    /// <summary>Third-party notices (legal/THIRD-PARTY-NOTICES.txt).</summary>
    public static string Notices => NoticesText.Value;

    /// <summary>The software licence (LICENSE).</summary>
    public static string Licence => LicenceText.Value;

    private static string Read(string name)
    {
        using var stream = typeof(LegalTexts).Assembly.GetManifestResourceStream(name)
            ?? throw new InvalidOperationException($"Missing embedded resource {name}.");
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }
}
