using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace ChuvadiReader.Mac.Platform;

/// <summary>Takes what a person was reading out of a log message (D-132).</summary>
internal sealed partial class LogScrubber(byte[] salt)
{
    internal const int MaxMessage = 400;
    private const string Extensions = "pdf|docx?|xlsx?|pptx?|md|markdown|txt|log|html?|json|png|jpe?g|bmp|gif|tiff?|webp|pfx|p12|csv|rtf|odt|zip";

    public static byte[] LoadOrCreateSalt(string path)
    {
        try
        {
            if (File.Exists(path) && File.ReadAllBytes(path) is { Length: 16 } existing)
            {
                return existing;
            }

            var salt = RandomNumberGenerator.GetBytes(16);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllBytes(path, salt);
            return salt;
        }
        catch
        {
            return RandomNumberGenerator.GetBytes(16); // hashes then only match within this run
        }
    }

    public string Clean(string? text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return string.Empty;
        }

        var s = text.Replace('\r', ' ').Replace('\n', ' ');
        s = Quoted().Replace(s, m => Token(m.Groups["v"].Value, quoted: true));
        s = Url().Replace(s, m => $"<{m.Groups["scheme"].Value}://{m.Groups["host"].Value} #{Hash(m.Value)}>");
        s = FilePath().Replace(s, m => Token(m.Value, quoted: false));
        s = FileName().Replace(s, m => Token(m.Value, quoted: false));
        return s.Length > MaxMessage ? s[..MaxMessage] + "…" : s;
    }

    /// <summary>Stack frames name code, not documents; only file paths in them are replaced.</summary>
    public string CleanStack(string stack)
    {
        var s = FilePath().Replace(stack.Replace('\r', ' ').Replace("\n", " ⏎ "), m => Token(m.Value, quoted: false));
        return s.Length > 4000 ? s[..4000] + "…" : s;
    }

    private string Token(string value, bool quoted)
    {
        var name = value.Trim();
        var ext = Path.GetExtension(name.Split('?', '#')[0]).TrimStart('.').ToLowerInvariant();
        var looksLikeFile = ext.Length is > 0 and <= 8 && ext.All(char.IsAsciiLetterOrDigit)
            && (name.Contains('/') || Regex.IsMatch(ext, $"^({Extensions})$"));
        if (looksLikeFile)
        {
            return $"<.{ext} #{Hash(name)}>";
        }

        if (!quoted)
        {
            return $"<path #{Hash(name)}>";
        }

        return name.Length == 0 ? "''" : $"<text #{Hash(name)}>";
    }

    private string Hash(string value)
    {
        var mac = HMACSHA256.HashData(salt, Encoding.UTF8.GetBytes(value));
        return Convert.ToHexString(mac, 0, 4).ToLowerInvariant();
    }

    [GeneratedRegex("""(?<!\w)(?<q>['"‘“])(?<v>[^'"’”]{0,2000})['"’”](?!\w)""")]
    private static partial Regex Quoted();

    [GeneratedRegex(@"(?<scheme>[a-zA-Z][a-zA-Z0-9+.-]{1,15})://(?<host>[^/\s<>'""?#]*)[^\s<>'""]*")]
    private static partial Regex Url();

    [GeneratedRegex(@"(?<![\w<#])(?:~|/(?:Users|Volumes|private|var|tmp|Applications|Library|System|opt|home)\b|\.{1,2})/[^\s<>'"":|]*")]
    private static partial Regex FilePath();

    [GeneratedRegex(@"(?<![\w<#./])[\w][\w\-. ]{0,120}\.(?:" + Extensions + @")\b(?!\.\w)", RegexOptions.IgnoreCase)]
    private static partial Regex FileName();
}
