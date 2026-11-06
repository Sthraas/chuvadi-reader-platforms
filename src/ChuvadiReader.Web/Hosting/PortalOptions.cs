namespace ChuvadiReader.Web.Hosting;

/// <summary>How the portal runs (D-24).</summary>
public enum PortalMode
{
    /// <summary>One process does everything: development, tests, CI.</summary>
    Single,

    /// <summary>Production: TLS, Sangam sign-in, session expiry and static files here; each signed-in
    /// person's Reader runs in their own worker process, reached over a Unix socket.</summary>
    Gateway,

    /// <summary>One person's Reader, started by the gateway only (never configured by hand).</summary>
    Worker,
}

/// <summary>Portal settings (section <c>Portal</c> in appsettings or environment variables
/// <c>Portal__…</c>). The public address is configuration, never code: the domain is not bought yet.</summary>
public sealed class PortalOptions
{
    public const string Section = "Portal";

    /// <summary><see cref="PortalMode.Gateway"/> in production (D-24); <see cref="PortalMode.Single"/> by default.</summary>
    public PortalMode Mode { get; set; } = PortalMode.Single;

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

    /// <summary>"Download the desktop app" / "Get the desktop app" (12a, 12b; D-35).</summary>
    public string DesktopAppUrl { get; set; } = ChuvadiReader.Ui.Components.Platform.Portal.PortalLinks.PlaceholderDesktopAppUrl;

    /// <summary>"Terms of use" under the sign-in card: the licences page every host has (Foundation,
    /// third combined patch). Empty hides the line.</summary>
    public string? TermsUrl { get; set; } = "/licence";

    /// <summary>"Account settings" in the account menu: Sangam's own self-service page (D-35). Empty hides the item.</summary>
    public string? AccountSettingsUrl { get; set; }

    /// <summary>A session ends after this long with nothing done (D-30).</summary>
    public TimeSpan IdleTimeout { get; set; } = TimeSpan.FromMinutes(30);

    /// <summary>How long before the end the warning shows (D-30).</summary>
    public TimeSpan ExpiryWarning { get; set; } = TimeSpan.FromMinutes(5);

    /// <summary>How often expiry is checked.</summary>
    public TimeSpan ExpiryCheckInterval { get; set; } = TimeSpan.FromSeconds(15);

    /// <summary>File announcing a planned restart in every open tab (line 1: ISO 8601 time with offset;
    /// optional line 2: the text). Empty: no announcements. Production: <c>/var/lib/chuvadi/maintenance</c>.</summary>
    public string? MaintenanceNoticeFile { get; set; }

    /// <summary>Where working copies may live (D-28).</summary>
    public StorageOptions Storage { get; set; } = new();

    /// <summary>Per-person worker processes (gateway mode).</summary>
    public WorkerOptions Workers { get; set; } = new();

    /// <summary>Worker mode only, set by the gateway: the Unix socket to listen on.</summary>
    public string? WorkerSocket { get; set; }

    /// <summary>Worker mode only, set by the gateway: the user key of the one person this worker serves.</summary>
    public string? WorkerOwner { get; set; }
}

/// <summary>Per-person worker processes (section <c>Portal:Workers</c>).</summary>
public sealed class WorkerOptions
{
    /// <summary>What starts a worker: the portal's own app host or <c>ChuvadiReader.Web.dll</c> (run with
    /// <c>dotnet</c>). Empty: this same program.</summary>
    public string? Command { get; set; }

    /// <summary>Folder for the workers' Unix sockets (short path: socket paths are limited to 107 bytes).
    /// Empty: a private folder under the system temp folder.</summary>
    public string? SocketFolder { get; set; }

    /// <summary>Hard memory cap of one worker's managed heap, in MB (<c>DOTNET_GCHeapHardLimit</c>).</summary>
    public int MemoryLimitMB { get; set; } = 1536;

    /// <summary>Most people signed in at once; more get a "the portal is full" page.</summary>
    public int MaxWorkers { get; set; } = 40;

    /// <summary>How long a worker may take to start.</summary>
    public TimeSpan StartTimeout { get; set; } = TimeSpan.FromSeconds(30);

    /// <summary>A worker with no open tab and no request for this long is stopped (its files go with it).</summary>
    public TimeSpan IdleStop { get; set; } = TimeSpan.FromMinutes(2);

    /// <summary>How often the gateway checks its workers.</summary>
    public TimeSpan CheckInterval { get; set; } = TimeSpan.FromSeconds(30);
}
