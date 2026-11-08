namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Which CUPS server to ask for printers (B-20 follow-up). Read the way CUPS' own tools (lpstat, GTK's print
/// dialog) read it: the <c>CUPS_SERVER</c> variable, then <c>ServerName</c> in <c>~/.cups/client.conf</c>, then in
/// <c>/etc/cups/client.conf</c>. Nothing set, or a local socket path, means the computer's own CUPS, which also
/// shows the network printers it browses (<c>CupsQueues.List()</c> as before).
/// </summary>
public static class CupsServer
{
    /// <summary>The server's IPP address (<c>ipp://host:port/</c>), or null for the local CUPS.</summary>
    public static string? Configured() => Resolve(
        Environment.GetEnvironmentVariable("CUPS_SERVER"),
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".cups", "client.conf"),
        "/etc/cups/client.conf");

    public static string? Resolve(string? variable, string userConf, string systemConf)
    {
        if (!string.IsNullOrWhiteSpace(variable))
        {
            return ToUri(variable);
        }

        foreach (var conf in new[] { userConf, systemConf })
        {
            if (ServerName(conf) is { } name)
            {
                return ToUri(name);
            }
        }

        return null;
    }

    /// <summary>The first <c>ServerName</c> in a client.conf, or null (no file, unreadable, or not set).</summary>
    public static string? ServerName(string path)
    {
        try
        {
            foreach (var raw in File.ReadLines(path))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line[0] == '#')
                {
                    continue;
                }

                var space = line.IndexOfAny([' ', '\t']);
                if (space > 0 && line[..space].Equals("ServerName", StringComparison.OrdinalIgnoreCase))
                {
                    var value = line[(space + 1)..].Trim();
                    return value.Length == 0 ? null : value;
                }
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // No client.conf, or it can't be read: CUPS' tools then use the local server too.
        }

        return null;
    }

    /// <summary><c>host</c>, <c>host:port</c>, <c>[v6]:port</c> or <c>host/version=1.1</c> → <c>ipp://host:port/</c>;
    /// a socket path (<c>/run/cups/cups.sock</c>) → null, the local server.</summary>
    public static string? ToUri(string serverName)
    {
        var name = serverName.Trim();
        if (name.Length == 0 || name[0] == '/' || name[0] == '~')
        {
            return null;
        }

        var slash = name.IndexOf('/');
        if (slash >= 0)
        {
            name = name[..slash]; // "/version=1.1" and the like: options for libcups, not part of the address
        }

        string host;
        var port = 631;
        if (name.StartsWith('['))
        {
            var close = name.IndexOf(']');
            if (close < 0)
            {
                return null;
            }

            host = name[..(close + 1)];
            if (close + 1 < name.Length && name[close + 1] == ':' && !int.TryParse(name[(close + 2)..], out port))
            {
                return null;
            }
        }
        else
        {
            var colon = name.LastIndexOf(':');
            host = colon >= 0 ? name[..colon] : name;
            if (colon >= 0 && !int.TryParse(name[(colon + 1)..], out port))
            {
                return null;
            }
        }

        return host.Length == 0 || port is < 1 or > 65535 ? null : $"ipp://{host}:{port}/";
    }
}
