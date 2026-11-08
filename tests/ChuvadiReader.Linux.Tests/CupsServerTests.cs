using ChuvadiReader.Linux.Platform;
using Xunit;

namespace ChuvadiReader.Linux.Tests;

/// <summary>Which CUPS server Print asks for printers: read as lpstat and GTK's dialog read it (B-20 follow-up).</summary>
public sealed class CupsServerTests : IDisposable
{
    private readonly string _dir = Directory.CreateTempSubdirectory("chvd-cups-").FullName;

    public void Dispose() => Directory.Delete(_dir, recursive: true);

    private string Conf(string name, string text)
    {
        var path = Path.Combine(_dir, name);
        File.WriteAllText(path, text);
        return path;
    }

    private string Missing => Path.Combine(_dir, "missing.conf");

    [Theory]
    [InlineData("printserver", "ipp://printserver:631/")]
    [InlineData("printserver.example.in:8631", "ipp://printserver.example.in:8631/")]
    [InlineData("192.168.1.20", "ipp://192.168.1.20:631/")]
    [InlineData("[fd00::20]:632", "ipp://[fd00::20]:632/")]
    [InlineData("[fd00::20]", "ipp://[fd00::20]:631/")]
    [InlineData("printserver/version=1.1", "ipp://printserver:631/")]
    [InlineData(" printserver ", "ipp://printserver:631/")]
    public void ServerNames_become_ipp_addresses(string name, string expected) =>
        Assert.Equal(expected, CupsServer.ToUri(name));

    [Theory]
    [InlineData("/run/cups/cups.sock")] // a local socket: the computer's own CUPS
    [InlineData("~/.cups/cups.sock")]
    [InlineData("")]
    [InlineData("host:notaport")]
    [InlineData("host:70000")]
    [InlineData("[fd00::20")]
    public void Local_sockets_and_bad_names_mean_the_local_server(string name) =>
        Assert.Null(CupsServer.ToUri(name));

    [Fact]
    public void Nothing_configured_means_the_local_server() =>
        Assert.Null(CupsServer.Resolve(null, Missing, Missing));

    [Fact]
    public void The_system_client_conf_names_the_server()
    {
        var system = Conf("system.conf", "# CUPS client configuration\n\n  ServerName   printserver:8631  \nEncryption IfRequested\n");
        Assert.Equal("ipp://printserver:8631/", CupsServer.Resolve(null, Missing, system));
    }

    [Fact]
    public void The_users_client_conf_wins_over_the_systems()
    {
        var user = Conf("user.conf", "ServerName mine\n");
        var system = Conf("system.conf", "ServerName office\n");
        Assert.Equal("ipp://mine:631/", CupsServer.Resolve(null, user, system));
    }

    [Fact]
    public void CUPS_SERVER_wins_over_both_files()
    {
        var user = Conf("user.conf", "ServerName mine\n");
        var system = Conf("system.conf", "ServerName office\n");
        Assert.Equal("ipp://lab:631/", CupsServer.Resolve("lab", user, system));
    }

    [Fact]
    public void A_client_conf_without_ServerName_or_commented_out_is_ignored()
    {
        var user = Conf("user.conf", "#ServerName mine\nEncryption Never\n");
        var system = Conf("system.conf", "servername office\n"); // CUPS' directive names are case-insensitive
        Assert.Equal("ipp://office:631/", CupsServer.Resolve(" ", user, system));
    }

    [Fact]
    public void A_socket_ServerName_means_the_local_server()
    {
        var system = Conf("system.conf", "ServerName /run/cups/cups.sock\n");
        Assert.Null(CupsServer.Resolve(null, Missing, system));
    }
}
