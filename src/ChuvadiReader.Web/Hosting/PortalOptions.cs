namespace ChuvadiReader.Web.Hosting;

/// <summary>Portal settings (section <c>Portal</c> in appsettings or environment variables
/// <c>Portal__…</c>). The public address is configuration, never code: the domain is not bought yet.</summary>
public sealed class PortalOptions
{
    public const string Section = "Portal";

    /// <summary>The address people use, e.g. <c>https://reader.example.in</c>. Used to check the
    /// <c>Origin</c> of upload and print requests. Required outside Development.</summary>
    public string PublicOrigin { get; set; } = string.Empty;

    /// <summary>Folder for session files. Each signed-in person gets a sub-folder named by a hash of
    /// their Sangam id, and each browser session a folder inside it that is deleted when the session
    /// ends (no server storage in this release). Must be on the encrypted volume in production.</summary>
    public string DataRoot { get; set; } = string.Empty;

    /// <summary>Largest single file a person may upload.</summary>
    public long MaxUploadBytes { get; set; } = 200L * 1024 * 1024;

    /// <summary>Most files in one pick (Merge, Bench, images).</summary>
    public int MaxFilesPerPick { get; set; } = 50;

    /// <summary>Size of one upload chunk sent by the browser.</summary>
    public int UploadChunkBytes { get; set; } = 4 * 1024 * 1024;

    /// <summary>How long a person has to choose files once the browser's file chooser is open.</summary>
    public TimeSpan PickTimeout { get; set; } = TimeSpan.FromMinutes(30);

    /// <summary>How long a download link stays valid.</summary>
    public TimeSpan DownloadLinkLifetime { get; set; } = TimeSpan.FromMinutes(10);

    /// <summary>How long to wait for the Reader to finish writing a file it was asked to save.</summary>
    public TimeSpan SaveWaitLimit { get; set; } = TimeSpan.FromMinutes(30);

    /// <summary>Signing certificates (.pfx/.p12) carry a private key. Off until Arun decides (W-08).</summary>
    public bool AllowCertificateUpload { get; set; }
}
