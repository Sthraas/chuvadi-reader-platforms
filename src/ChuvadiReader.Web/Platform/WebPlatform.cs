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
        DropFiles = true,
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
    private bool _signedIn;

    public WebAccount(AuthenticationStateProvider auth, Microsoft.AspNetCore.Components.NavigationManager nav)
    {
        _auth = auth;
        _nav = nav;
    }

    public bool IsSignedIn => _signedIn;

    public string DisplayName => _name;

    public string? Email => _email;

    public event Action? Changed;

    /// <summary>Reads the person from the connection's sign-in. Called once when the session starts.</summary>
    public async Task LoadAsync()
    {
        var user = (await _auth.GetAuthenticationStateAsync().ConfigureAwait(false)).User;
        _signedIn = user.Identity?.IsAuthenticated == true;
        _name = user.FindFirst("name")?.Value ?? string.Empty;
        _email = user.FindFirst("email")?.Value;
        Changed?.Invoke();
    }

    /// <summary>Already signed in to reach the portal.</summary>
    public Task<bool> SignInAsync(CancellationToken ct = default) => Task.FromResult(_signedIn);

    public Task SignOutAsync(CancellationToken ct = default)
    {
        _nav.NavigateTo("/signout", forceLoad: true);
        return Task.CompletedTask;
    }
}
