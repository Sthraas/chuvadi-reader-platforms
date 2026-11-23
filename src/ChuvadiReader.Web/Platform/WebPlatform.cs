using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Files;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// <see cref="IPlatformInfo"/> for the portal (Foundation F-5: Web follows the browser). The form
/// factor comes from the browser's viewport, reported by <c>portal.js</c> at start and on resize;
/// ⌘ labels on a Mac browser. Chrome: no window buttons, an account menu, no title-bar drag.
/// Scoped: one per browser connection.
/// </summary>
public sealed class WebPlatformInfo : IPlatformInfo
{
    /// <summary>Below this CSS width the phone layout is used.</summary>
    public const int PhoneMaxWidth = 599;

    /// <summary>Touch-first screens up to this width use the tablet layout (12d: 1280 × 800 landscape).</summary>
    public const int TabletMaxWidth = 1366;

    public static readonly PlatformCapabilities WebCapabilities = new()
    {
        PickFolders = false,
        SaveInPlace = false,
        SavesAsDownload = true,
        WatchFolders = false,
        RevealInFolder = false,
        DropFiles = true, // D-89 A: the Ui's drop catcher hands dropped files to WebDroppedFiles
        Share = false,
        MultipleWindows = true,
        ServerSide = true,
    };

    public static readonly ShellChrome WebChrome = new(WindowButtons.None, NativeMenuBar: false, AccountMenu: true, TitleBarDrag: false, CornerRadiusPx: 0);

    private FormFactor _formFactor = FormFactor.Desktop;
    private InputKinds _input = InputKinds.Mouse | InputKinds.Keyboard;
    private IKeyLabels _keys = new CtrlKeyLabels();

    public PlatformKind Kind => PlatformKind.Web;

    public FormFactor FormFactor => _formFactor;

    public event Action? FormFactorChanged;

    public InputKinds Input => _input;

    public ShellChrome Chrome => WebChrome;

    public PlatformCapabilities Capabilities => WebCapabilities;

    public IKeyLabels Keys => _keys;

    /// <summary>Called by the browser bridge with what the browser reports.</summary>
    public void Update(int viewportWidth, bool coarsePointer, bool isMac)
    {
        _keys = isMac ? new MacKeyLabels() : new CtrlKeyLabels();
        _input = coarsePointer ? InputKinds.Touch : InputKinds.Mouse | InputKinds.Keyboard;
        var next = Classify(viewportWidth, coarsePointer);
        if (next != _formFactor)
        {
            _formFactor = next;
            FormFactorChanged?.Invoke();
        }
    }

    public static FormFactor Classify(int viewportWidth, bool coarsePointer)
    {
        if (viewportWidth <= 0)
        {
            return FormFactor.Desktop;
        }

        if (viewportWidth <= PhoneMaxWidth)
        {
            return FormFactor.Phone;
        }

        return coarsePointer && viewportWidth <= TabletMaxWidth ? FormFactor.Tablet : FormFactor.Desktop;
    }
}

/// <summary>Receives viewport reports from <c>portal.js</c> and forwards them to <see cref="WebPlatformInfo"/>.</summary>
public sealed class ViewportReporter : IAsyncDisposable
{
    private readonly WebPlatformInfo _platform;
    private readonly IJSRuntime _js;
    private DotNetObjectReference<ViewportReporter>? _self;

    public ViewportReporter(WebPlatformInfo platform, IJSRuntime js)
    {
        _platform = platform;
        _js = js;
    }

    public async Task StartAsync()
    {
        _self ??= DotNetObjectReference.Create(this);
        await _js.InvokeVoidAsync("chvdPortal.watchViewport", _self).ConfigureAwait(false);
    }

    [JSInvokable]
    public void Report(int width, bool coarsePointer, bool isMac) => _platform.Update(width, coarsePointer, isMac);

    public ValueTask DisposeAsync()
    {
        _self?.Dispose();
        return ValueTask.CompletedTask;
    }
}

/// <summary>Folders for one browser session (<see cref="IAppPaths"/>): app data and scratch inside the
/// session folder, deleted with it. No visible file system, so no default save folder (Group C3 then
/// saves under the working folder, and every save is delivered as a download).</summary>
public sealed class SessionAppPaths : IAppPaths
{
    private readonly SessionSpace _space;

    public SessionAppPaths(SessionSpace space) => _space = space;

    public string AppDataFolder => Ensure(Path.Combine(_space.Root, "appdata"));

    public string WorkingFolder => Ensure(Path.Combine(_space.Root, "work"));

    public string? DefaultSaveFolder => null;

    private static string Ensure(string dir)
    {
        SpaceLayout.CreatePrivateDirectory(dir);
        return dir;
    }
}

/// <summary>The signed-in Sangam person (<see cref="IAccount"/>). Sign-in happens before the portal
/// loads; signing out goes through the portal's sign-out address, which ends the session everywhere.</summary>
public sealed class WebAccount : IAccount
{
    private readonly AuthenticationStateProvider _auth;
    private readonly Microsoft.AspNetCore.Components.NavigationManager _nav;
    private string _name = string.Empty;
    private string? _email;
    private string? _unit;
    private bool _signedIn;

    private readonly IServiceProvider? _services;

    /// <param name="services">The connection's services, read at sign-out (the Ui's unsaved-work question, the
    /// connection's downloads, the browser); null in tests that don't sign out.</param>
    public WebAccount(AuthenticationStateProvider auth, Microsoft.AspNetCore.Components.NavigationManager nav, IServiceProvider? services = null)
    {
        _auth = auth;
        _nav = nav;
        _services = services;
    }

    public bool IsSignedIn => _signedIn;

    public string DisplayName => _name;

    public string? Email => _email;

    /// <summary>The organisation unit of this sign-in (Sangam's <c>sangam_org</c>), shown after the Sangam ID.</summary>
    public string? Unit => _unit;

    public event Action? Changed;

    /// <summary>Reads the person from the connection's sign-in. Called once when the session starts.</summary>
    public async Task LoadAsync()
    {
        var user = (await _auth.GetAuthenticationStateAsync().ConfigureAwait(false)).User;
        _signedIn = user.Identity?.IsAuthenticated == true;
        _name = user.FindFirst("name")?.Value ?? string.Empty;
        _email = user.FindFirst("email")?.Value;
        _unit = user.FindFirst(ChuvadiReader.Web.Auth.SangamSignIn.UnitClaim)?.Value;
        Changed?.Invoke();
    }

    /// <summary>Already signed in to reach the portal.</summary>
    public Task<bool> SignInAsync(CancellationToken ct = default) => Task.FromResult(_signedIn);

    /// <summary>How long Sign out waits for the browser to ask for a download the card has just handed it.</summary>
    internal static readonly TimeSpan DownloadWait = TimeSpan.FromSeconds(10);

    /// <summary>How long Sign out waits, after the card, for the Ui's own move to Home (when it makes one).</summary>
    internal static readonly TimeSpan UiSettle = TimeSpan.FromSeconds(1);

    /// <summary>
    /// Sign out. D-194: with unsaved work (marks on a PDF, desks arranged and not saved) the Ui's card asks
    /// first — on the portal Save as (a download), Discard or Cancel — and Cancel keeps the person signed in.
    /// After "Save as" the sign-out waits until the browser has asked for the download, because signing out
    /// deletes the session's files. The browser's own "Leave site?" is then taken off: the person has answered.
    /// </summary>
    public async Task SignOutAsync(CancellationToken ct = default)
    {
        if (_services?.GetService<IUnsavedWork>() is { HasUnsavedWork: true } work)
        {
            // After Save as or Discard the Ui closes the documents and goes Home. That navigation must be over
            // before the browser is sent to /signout: started after it, it interrupts the sign-out's page load
            // (seen in Chrome and WebKit), and a sign-out cut off in the browser may not reach the server.
            var moved = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            void Moved(object? sender, Microsoft.AspNetCore.Components.Routing.LocationChangedEventArgs e) => moved.TrySetResult();
            _nav.LocationChanged += Moved;
            try
            {
                if (!await work.ConfirmCloseAsync()) // stays on the connection's own thread: the navigation below needs it
                {
                    return; // Cancel, or the question is already on screen
                }

                await Task.WhenAny(moved.Task, Task.Delay(UiSettle, ct));
            }
            finally
            {
                _nav.LocationChanged -= Moved;
            }
        }

        if (_services?.GetService<SessionSpace>() is { } space && _services.GetService<TransferRegistry>() is { } registry)
        {
            await registry.WaitForDownloadsAsync(space.ConnectionId, DownloadWait, DownloadWait, ct);
        }

        // WT-31: the browser goes to /signout only once the page has stopped moving (the Ui's move Home,
        // a download link) and makes no move after it, so the sign-out's page load is never cancelled.
        if (_services?.GetService<BrowserBridge>() is { } browser)
        {
            try
            {
                if (await browser.LeaveWhenSettledAsync("/signout", SettledQuiet, SettledAtMost))
                {
                    return;
                }
            }
            catch (Exception ex) when (ex is Microsoft.JSInterop.JSException or Microsoft.JSInterop.JSDisconnectedException or OperationCanceledException or InvalidOperationException)
            {
                // The page couldn't be asked (gone, or an older page): the plain way below.
            }
        }

        _nav.NavigateTo("/signout", forceLoad: true);
    }

    /// <summary>How long the page must have made no move before Sign out sends it on (WT-31).</summary>
    internal static readonly TimeSpan SettledQuiet = TimeSpan.FromMilliseconds(400);

    /// <summary>The longest Sign out waits for the page to stop moving.</summary>
    internal static readonly TimeSpan SettledAtMost = TimeSpan.FromSeconds(3);
}
