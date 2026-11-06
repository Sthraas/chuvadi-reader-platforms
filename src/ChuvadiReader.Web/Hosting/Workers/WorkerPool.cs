using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Net.Http.Json;
using System.Net.Sockets;
using System.Security.Claims;
using System.Security.Cryptography;
using ChuvadiReader.Web.Auth;
using ChuvadiReader.Web.Files;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting.Workers;

/// <summary>Every worker slot is taken.</summary>
public sealed class WorkerPoolFullException : Exception
{
    public WorkerPoolFullException()
        : base("The portal is serving as many people as it can.")
    {
    }
}

/// <summary>One person's worker process (D-24).</summary>
public sealed class WorkerProcess : IAsyncDisposable
{
    private long _lastUsedTicks;
    private int _failedChecks;
    private volatile bool _stopped;

    internal WorkerProcess(string key, string sub, Process process, string socket, string folder, string secret, HttpClient client)
    {
        Key = key;
        Sub = sub;
        Process = process;
        Socket = socket;
        Folder = folder;
        Secret = secret;
        Client = client;
        Touch();
    }

    public string Key { get; }
    public string Sub { get; }
    public Process Process { get; }
    public string Socket { get; }
    public string Folder { get; }
    internal string Secret { get; }
    public HttpClient Client { get; }
    public int Id => Process.Id;
    public bool HasExited
    {
        get
        {
            if (_stopped)
            {
                return true;
            }

            try
            {
                return Process.HasExited;
            }
            catch (InvalidOperationException)
            {
                return true;
            }
        }
    }

    public DateTimeOffset LastUsed => new(Interlocked.Read(ref _lastUsedTicks), TimeSpan.Zero);

    public void Touch() => Interlocked.Exchange(ref _lastUsedTicks, DateTimeOffset.UtcNow.UtcTicks);

    internal int FailedChecks { get => _failedChecks; set => _failedChecks = value; }

    /// <summary>The headers that make a request this worker's: the secret and the person.</summary>
    internal void Sign(HttpRequestMessage request, ClaimsPrincipal? user)
    {
        request.Headers.TryAddWithoutValidation(GatewayHeaders.Secret, Secret);
        if (user is null)
        {
            request.Headers.TryAddWithoutValidation(GatewayHeaders.Sub, GatewayHeaders.Encode(Sub));
            return;
        }

        foreach (var (claim, header) in GatewayHeaders.Identity)
        {
            if (user.FindFirst(claim)?.Value is { Length: > 0 } value)
            {
                request.Headers.TryAddWithoutValidation(header, GatewayHeaders.Encode(value));
            }
        }
    }

    public async ValueTask DisposeAsync()
    {
        Client.Dispose();
        try
        {
            Process.StandardInput.Close(); // the worker's lifeline: it stops on end of input
        }
        catch (Exception ex) when (ex is IOException or InvalidOperationException)
        {
        }

        using (var wait = new CancellationTokenSource(TimeSpan.FromSeconds(10)))
        {
            try
            {
                await Process.WaitForExitAsync(wait.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                try
                {
                    Process.Kill(entireProcessTree: true);
                }
                catch (InvalidOperationException)
                {
                }
            }
        }

        _stopped = true;
        Process.Dispose();
    }
}

/// <summary>
/// The gateway's per-person worker processes (D-24): started on a person's first request, each with
/// its own HOME, temp folder and data folder inside <c>{DataRoot}/workers/{key}</c> (owner-only), a hard
/// memory cap, and a Unix socket in an owner-only folder. A worker is stopped when its person has had no
/// open tab for a while, when the sign-in ends, or when the gateway stops; its folder is then deleted.
/// Also the gateway's <see cref="ITabControl"/>: tab endings and expiry warnings go to the worker. Singleton.
/// </summary>
public sealed class WorkerPool : ITabControl, IAsyncDisposable
{
    private readonly ConcurrentDictionary<string, Lazy<Task<WorkerProcess>>> _workers = new(StringComparer.Ordinal);
    private readonly PortalOptions _portal;
    private readonly WorkerOptions _options;
    private readonly IHostEnvironment _env;
    private readonly ILogger<WorkerPool> _log;
    private readonly ILoggerFactory _logs;
    private readonly string _socketFolder;
    private bool _disposed;

    public WorkerPool(IOptions<PortalOptions> portal, IHostEnvironment env, ILoggerFactory logs)
    {
        _portal = portal.Value;
        _options = _portal.Workers;
        _env = env;
        _logs = logs;
        _log = logs.CreateLogger<WorkerPool>();
        _socketFolder = string.IsNullOrWhiteSpace(_options.SocketFolder)
            ? Path.Combine(Path.GetTempPath(), "chvd-gw-" + Environment.ProcessId.ToString(CultureInfo.InvariantCulture))
            : _options.SocketFolder;
        SpaceLayout.CreatePrivateDirectory(_socketFolder);
        SpaceLayout.CreatePrivateDirectory(WorkersRoot);
    }

    public string WorkersRoot => Path.Combine(_portal.DataRoot, "workers");

    public int Count => _workers.Count;

    /// <summary>The running workers (for supervision and tests).</summary>
    public IReadOnlyList<WorkerProcess> Running
        => _workers.Values.Where(l => l.IsValueCreated && l.Value.IsCompletedSuccessfully).Select(l => l.Value.Result).ToList();

    /// <summary>The signed-in person's worker, started if needed.</summary>
    public async Task<WorkerProcess> GetAsync(ClaimsPrincipal user, CancellationToken ct)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        var sub = user.FindFirst("sub")?.Value ?? throw new UnauthorizedAccessException("Sign in to use the portal.");
        var key = UserKey.FromSub(sub);
        while (true)
        {
            if (!_workers.ContainsKey(key) && _workers.Count >= _options.MaxWorkers)
            {
                throw new WorkerPoolFullException();
            }

            var lazy = _workers.GetOrAdd(key, k => new Lazy<Task<WorkerProcess>>(() => StartAsync(k, sub)));
            WorkerProcess worker;
            try
            {
                worker = await lazy.Value.WaitAsync(ct).ConfigureAwait(false);
            }
            catch (Exception) when (!ct.IsCancellationRequested)
            {
                _workers.TryRemove(new KeyValuePair<string, Lazy<Task<WorkerProcess>>>(key, lazy));
                throw;
            }

            if (!worker.HasExited)
            {
                worker.Touch();
                return worker;
            }

            // It died between requests; its exit handler cleans up. Start a fresh one.
            _workers.TryRemove(new KeyValuePair<string, Lazy<Task<WorkerProcess>>>(key, lazy));
        }
    }

    private async Task<WorkerProcess> StartAsync(string key, string sub)
    {
        var folder = Path.Combine(WorkersRoot, key);
        if (Directory.Exists(folder))
        {
            Directory.Delete(folder, recursive: true); // left by a worker that died
        }

        foreach (var sub2 in new[] { folder, Path.Combine(folder, "home"), Path.Combine(folder, "tmp"), Path.Combine(folder, "data") })
        {
            SpaceLayout.CreatePrivateDirectory(sub2);
        }

        var socket = Path.Combine(_socketFolder, key[..16] + ".sock");
        File.Delete(socket);
        var secret = Acme.AcmeJws.Base64Url(RandomNumberGenerator.GetBytes(32));

        var psi = StartInfo(folder, socket, key);
        var process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        var started = Stopwatch.StartNew();
        process.Start();
        var log = _logs.CreateLogger("ChuvadiReader.Web.Worker." + key[..8]);
        process.OutputDataReceived += (_, e) => { if (e.Data is { Length: > 0 } line) log.LogInformation("{Line}", line); };
        process.ErrorDataReceived += (_, e) => { if (e.Data is { Length: > 0 } line) log.LogWarning("{Line}", line); };
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.StandardInput.WriteLineAsync(secret).ConfigureAwait(false);
        await process.StandardInput.FlushAsync().ConfigureAwait(false);

        var handler = new SocketsHttpHandler
        {
            ConnectCallback = async (_, token) =>
            {
                var s = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
                try
                {
                    await s.ConnectAsync(new UnixDomainSocketEndPoint(socket), token).ConfigureAwait(false);
                    return new NetworkStream(s, ownsSocket: true);
                }
                catch
                {
                    s.Dispose();
                    throw;
                }
            },
            AllowAutoRedirect = false,
            UseCookies = false,
            UseProxy = false,
            AutomaticDecompression = System.Net.DecompressionMethods.None,
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(1),
        };
        var client = new HttpClient(handler) { BaseAddress = new Uri("http://worker/"), Timeout = Timeout.InfiniteTimeSpan };
        var worker = new WorkerProcess(key, sub, process, socket, folder, secret, client);
        process.Exited += (_, _) => _ = OnExitedAsync(worker);

        // Ready when its control endpoint answers.
        using var timeout = new CancellationTokenSource(_options.StartTimeout);
        while (true)
        {
            if (process.HasExited)
            {
                await OnExitedAsync(worker).ConfigureAwait(false);
                throw new InvalidOperationException($"The worker stopped while starting (exit code {process.ExitCode}).");
            }

            try
            {
                using var req = new HttpRequestMessage(HttpMethod.Get, WorkerHost.ControlPrefix + "/health");
                worker.Sign(req, null);
                using var resp = await client.SendAsync(req, timeout.Token).ConfigureAwait(false);
                if (resp.IsSuccessStatusCode)
                {
                    break;
                }
            }
            catch (HttpRequestException)
            {
            }
            catch (OperationCanceledException)
            {
                await worker.DisposeAsync().ConfigureAwait(false);
                await OnExitedAsync(worker).ConfigureAwait(false);
                throw new TimeoutException("The worker didn't start in time.");
            }

            await Task.Delay(50, timeout.Token).ContinueWith(_ => { }, TaskScheduler.Default).ConfigureAwait(false);
        }

        _log.LogInformation("Worker {Key} started (pid {Pid}) in {Ms} ms", key[..8], process.Id, started.ElapsedMilliseconds);
        return worker;
    }

    private ProcessStartInfo StartInfo(string folder, string socket, string key)
    {
        var (file, args, dir) = ResolveCommand();
        var psi = new ProcessStartInfo(file)
        {
            WorkingDirectory = dir,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        foreach (var a in args)
        {
            psi.ArgumentList.Add(a);
        }

        // Nothing of the gateway's own settings and secrets (Sangam client secret, TLS) reaches a worker.
        var env = psi.Environment;
        foreach (var name in env.Keys.ToList())
        {
            if (name.StartsWith("Sangam__", StringComparison.OrdinalIgnoreCase) || name.StartsWith("Portal__", StringComparison.OrdinalIgnoreCase)
                || name.StartsWith("Kestrel__", StringComparison.OrdinalIgnoreCase) || name.StartsWith("ConnectionStrings__", StringComparison.OrdinalIgnoreCase)
                || name is "ASPNETCORE_URLS" or "ASPNETCORE_HTTP_PORTS" or "ASPNETCORE_HTTPS_PORTS" or "DOTNET_URLS" or "DOTNET_HTTP_PORTS" or "DOTNET_HTTPS_PORTS")
            {
                env.Remove(name);
            }
        }

        var home = Path.Combine(folder, "home");
        env["ASPNETCORE_ENVIRONMENT"] = _env.EnvironmentName;
        env["HOME"] = home;
        env["TMPDIR"] = Path.Combine(folder, "tmp");
        env["XDG_CONFIG_HOME"] = Path.Combine(home, ".config");
        env["XDG_DATA_HOME"] = Path.Combine(home, ".local", "share");
        env["XDG_CACHE_HOME"] = Path.Combine(home, ".cache");
        env["DOTNET_GCHeapHardLimit"] = "0x" + ((long)_options.MemoryLimitMB * 1024 * 1024).ToString("X", CultureInfo.InvariantCulture);
        env["DOTNET_gcServer"] = "0";
        env["DOTNET_DbgEnableMiniDump"] = "0"; // a crash must not write this person's memory to disk
        env["DOTNET_EnableCrashReport"] = "0";
        if (DotnetHost() is { } muxer && !env.ContainsKey("DOTNET_ROOT"))
        {
            env["DOTNET_ROOT"] = Path.GetDirectoryName(muxer); // so an app host finds the same runtime
        }
        env["Logging__Console__FormatterOptions__SingleLine"] = "true"; // one gateway log line per worker log entry
        env["Portal__Mode"] = nameof(PortalMode.Worker);
        env["Portal__WorkerSocket"] = socket;
        env["Portal__WorkerOwner"] = key;
        env["Portal__DataRoot"] = Path.Combine(folder, "data");
        env["Portal__PublicOrigin"] = _portal.PublicOrigin;
        env["Portal__MaxUploadBytes"] = _portal.MaxUploadBytes.ToString(CultureInfo.InvariantCulture);
        env["Portal__MaxFilesPerPick"] = _portal.MaxFilesPerPick.ToString(CultureInfo.InvariantCulture);
        env["Portal__UploadChunkBytes"] = _portal.UploadChunkBytes.ToString(CultureInfo.InvariantCulture);
        env["Portal__PickTimeout"] = _portal.PickTimeout.ToString("c", CultureInfo.InvariantCulture);
        env["Portal__DownloadLinkLifetime"] = _portal.DownloadLinkLifetime.ToString("c", CultureInfo.InvariantCulture);
        env["Portal__SaveWaitLimit"] = _portal.SaveWaitLimit.ToString("c", CultureInfo.InvariantCulture);
        env["Portal__AllowCertificateUpload"] = _portal.AllowCertificateUpload ? "true" : "false";
        env["Portal__DesktopAppUrl"] = _portal.DesktopAppUrl;
        env["Portal__AccountSettingsUrl"] = _portal.AccountSettingsUrl ?? string.Empty;
        env["Portal__ForgotPasswordUrl"] = _portal.ForgotPasswordUrl ?? string.Empty;
        return psi;
    }

    /// <summary>The program to run: <c>Workers:Command</c>, else this same program, started the way the
    /// gateway itself was (through <c>dotnet</c>, or through the app host).</summary>
    private (string File, string[] Args, string Dir) ResolveCommand()
    {
        var command = Path.GetFullPath(string.IsNullOrWhiteSpace(_options.Command) ? typeof(Program).Assembly.Location : _options.Command);
        var dir = Path.GetDirectoryName(command)!;
        if (!command.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
        {
            return (command, [], dir); // an app host named in the settings
        }

        if (DotnetHost() is { } dotnet)
        {
            return (dotnet, [command], dir);
        }

        var apphost = Path.ChangeExtension(command, OperatingSystem.IsWindows() ? ".exe" : null);
        return File.Exists(apphost) ? (apphost, [], dir) : ("dotnet", [command], dir);
    }

    /// <summary>The <c>dotnet</c> host running this gateway, or the one the SDK names (tests); null when
    /// the gateway runs through its app host.</summary>
    private static string? DotnetHost()
    {
        if (Environment.ProcessPath is { } self && Path.GetFileNameWithoutExtension(self).Equals("dotnet", StringComparison.OrdinalIgnoreCase))
        {
            return self;
        }

        return Environment.GetEnvironmentVariable("DOTNET_HOST_PATH") is { Length: > 0 } host && File.Exists(host) ? host : null;
    }

    private Task OnExitedAsync(WorkerProcess worker)
    {
        if (_workers.TryGetValue(worker.Key, out var lazy) && lazy.IsValueCreated && lazy.Value.IsCompletedSuccessfully && ReferenceEquals(lazy.Value.Result, worker))
        {
            _workers.TryRemove(new KeyValuePair<string, Lazy<Task<WorkerProcess>>>(worker.Key, lazy));
            int? code = null;
            try
            {
                code = worker.Process.ExitCode;
            }
            catch (InvalidOperationException)
            {
            }

            _log.Log(code == 0 ? LogLevel.Information : LogLevel.Warning, "Worker {Key} (pid {Pid}) ended with code {Code}", worker.Key[..8], worker.Id, code);
        }

        Clean(worker.Folder, worker.Socket);
        return Task.CompletedTask;
    }

    private void Clean(string folder, string socket)
    {
        try
        {
            if (Directory.Exists(folder))
            {
                Directory.Delete(folder, recursive: true);
            }

            File.Delete(socket);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _log.LogWarning("Couldn't remove a worker's files yet: {Message}", ex.Message);
        }
    }

    /// <summary>Stops a person's worker (sign-in ended, idle) and deletes its folder.</summary>
    public async Task StopAsync(string key)
    {
        if (!_workers.TryRemove(key, out var lazy) || !lazy.IsValueCreated)
        {
            return;
        }

        WorkerProcess worker;
        try
        {
            worker = await lazy.Value.ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            return;
        }

        await worker.DisposeAsync().ConfigureAwait(false);
        Clean(worker.Folder, worker.Socket);
        _log.LogInformation("Worker {Key} stopped", key[..8]);
    }

    /// <summary>One supervision pass: stop workers nobody uses, end ones that stopped answering. Workers
    /// are checked and stopped in parallel, so many people leaving at once are cleaned up together.</summary>
    public Task SuperviseAsync(CancellationToken ct)
        => Task.WhenAll(Running.Select(w => SuperviseOneAsync(w, ct)));

    private async Task SuperviseOneAsync(WorkerProcess worker, CancellationToken ct)
    {
        Health? health;
        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Get, WorkerHost.ControlPrefix + "/health");
            worker.Sign(req, null);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(10));
            using var resp = await worker.Client.SendAsync(req, timeout.Token).ConfigureAwait(false);
            health = await resp.Content.ReadFromJsonAsync<Health>(timeout.Token).ConfigureAwait(false);
            worker.FailedChecks = 0;
        }
        catch (Exception ex) when (ex is HttpRequestException or OperationCanceledException or System.Text.Json.JsonException && !ct.IsCancellationRequested)
        {
            if (++worker.FailedChecks >= 3)
            {
                _log.LogWarning("Worker {Key} stopped answering; ending it", worker.Key[..8]);
                await StopAsync(worker.Key).ConfigureAwait(false);
            }

            return;
        }

        if (health is { Circuits: 0 } && DateTimeOffset.UtcNow - worker.LastUsed > _options.IdleStop)
        {
            await StopAsync(worker.Key).ConfigureAwait(false);
        }
    }

    private sealed record Health(int Tabs, int Circuits);

    // ── ITabControl: tabs live in the worker ──────────────────────────────────────────

    public async Task<int> EndAsync(string? sub, string? sid)
    {
        if (sub is null)
        {
            // A sid alone: ask every worker (a person's sid is in one of them).
            var total = 0;
            foreach (var w in Running)
            {
                total += await EndInAsync(w, null, sid).ConfigureAwait(false);
            }

            return total;
        }

        return Find(sub) is { } worker ? await EndInAsync(worker, sub, sid).ConfigureAwait(false) : 0;
    }

    public async Task NoticeAsync(string sub, string? sid, ExpiryNotice? notice)
    {
        if (Find(sub) is not { } worker)
        {
            return;
        }

        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Post, WorkerHost.ControlPrefix + "/notice")
            {
                Content = JsonContent.Create(new WorkerHost.NoticeRequest(sub, sid, notice?.EndsAt, notice?.Reason ?? ExpiryReason.Idle)),
            };
            worker.Sign(req, null);
            using var resp = await worker.Client.SendAsync(req).ConfigureAwait(false);
        }
        catch (HttpRequestException ex)
        {
            _log.LogDebug("Couldn't reach worker {Key}: {Message}", worker.Key[..8], ex.Message);
        }
    }

    private async Task<int> EndInAsync(WorkerProcess worker, string? sub, string? sid)
    {
        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Post, WorkerHost.ControlPrefix + "/end")
            {
                Content = JsonContent.Create(new WorkerHost.EndRequest(sub, sid)),
            };
            worker.Sign(req, null);
            using var resp = await worker.Client.SendAsync(req).ConfigureAwait(false);
            var result = await resp.Content.ReadFromJsonAsync<EndResult>().ConfigureAwait(false);
            return result?.Ended ?? 0;
        }
        catch (Exception ex) when (ex is HttpRequestException or System.Text.Json.JsonException)
        {
            _log.LogDebug("Couldn't reach worker {Key}: {Message}", worker.Key[..8], ex.Message);
            return 0;
        }
    }

    private sealed record EndResult(int Ended);

    private WorkerProcess? Find(string sub)
        => _workers.TryGetValue(UserKey.FromSub(sub), out var lazy) && lazy.IsValueCreated && lazy.Value.IsCompletedSuccessfully && !lazy.Value.Result.HasExited
            ? lazy.Value.Result
            : null;

    /// <summary>Workers and folders left by a previous gateway run (killed without a clean stop).</summary>
    public int SweepLeftovers()
    {
        var removed = 0;
        foreach (var dir in Directory.EnumerateDirectories(WorkersRoot))
        {
            if (!_workers.ContainsKey(Path.GetFileName(dir)))
            {
                Directory.Delete(dir, recursive: true);
                removed++;
            }
        }

        return removed;
    }

    public async ValueTask DisposeAsync()
    {
        _disposed = true;
        await Task.WhenAll(_workers.Keys.ToList().Select(StopAsync)).ConfigureAwait(false);
        try
        {
            Directory.Delete(_socketFolder, recursive: true);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
        }
    }
}

/// <summary>Runs <see cref="WorkerPool.SuperviseAsync"/> on a timer and stops every worker when the gateway stops.</summary>
public sealed class WorkerSupervisor : BackgroundService
{
    private readonly WorkerPool _pool;
    private readonly WorkerOptions _options;
    private readonly ILogger<WorkerSupervisor> _log;

    public WorkerSupervisor(WorkerPool pool, IOptions<PortalOptions> options, ILogger<WorkerSupervisor> log)
    {
        _pool = pool;
        _options = options.Value.Workers;
        _log = log;
    }

    public override Task StartAsync(CancellationToken cancellationToken)
    {
        var removed = _pool.SweepLeftovers();
        if (removed > 0)
        {
            _log.LogInformation("Removed {Count} worker folder(s) left by a previous run", removed);
        }

        return base.StartAsync(cancellationToken);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(_options.CheckInterval);
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken).ConfigureAwait(false))
            {
                await _pool.SuperviseAsync(stoppingToken).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        await base.StopAsync(cancellationToken).ConfigureAwait(false);
        await _pool.DisposeAsync().ConfigureAwait(false);
    }
}
