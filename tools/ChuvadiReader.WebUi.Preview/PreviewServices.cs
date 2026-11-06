using System.Collections.Concurrent;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;

namespace ChuvadiReader.WebUi.Preview;

/// <summary>In-memory settings, one set per browser connection.</summary>
internal sealed class MemoryStorage : IAppStorage
{
    private readonly ConcurrentDictionary<string, string> _values = new();

    public Task<string?> GetAsync(string key, CancellationToken ct = default) =>
        Task.FromResult(_values.TryGetValue(key, out var v) ? v : null);

    public Task SetAsync(string key, string value, CancellationToken ct = default)
    {
        _values[key] = value;
        return Task.CompletedTask;
    }
}

/// <summary>No pickers in the preview: every pick is cancelled.</summary>
internal sealed class NoPicker : IFilePicker
{
    public Task<string?> PickDocumentAsync(CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default) => Task.FromResult<IReadOnlyList<string>>([]);
    public Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<string?> PickOpenSessionAsync(CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<string?> PickFolderAsync(CancellationToken ct = default) => Task.FromResult<string?>(null);
    public Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default) => Task.FromResult<IReadOnlyList<string>>([]);
}

internal sealed class NoClipboard : IImageClipboard, IClipboard
{
    public bool CanCopyText => false;
    public bool CanCopyImage => false;
    public Task SetTextAsync(string text, CancellationToken ct = default) => Task.CompletedTask;
    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default) => Task.CompletedTask;
}

/// <summary>A signed-in Sangam person, as in the handout (12b).</summary>
internal sealed class FakeSangamAccount : IAccount
{
    public bool IsSignedIn { get; private set; } = true;
    public string DisplayName => IsSignedIn ? "Arun S." : "";
    public string? Email => IsSignedIn ? "arun.s@smh.sangam" : null;
    public string? Unit => IsSignedIn ? "Records" : null;
    public event Action? Changed;

    public Task<bool> SignInAsync(CancellationToken ct = default)
    {
        IsSignedIn = true;
        Changed?.Invoke();
        return Task.FromResult(true);
    }

    public Task SignOutAsync(CancellationToken ct = default)
    {
        IsSignedIn = false;
        Changed?.Invoke();
        return Task.CompletedTask;
    }
}

/// <summary>Preview platform: any kind at any form factor (the real Web host classifies by browser width).</summary>
internal sealed class PreviewPlatformInfo(PlatformKind kind, FormFactor formFactor, InputKinds input, ShellChrome chrome,
    PlatformCapabilities capabilities, IKeyLabels keys) : IPlatformInfo
{
    public PlatformKind Kind => kind;
    public FormFactor FormFactor => formFactor;
    public event Action? FormFactorChanged { add { } remove { } }
    public InputKinds Input => input;
    public ShellChrome Chrome => chrome;
    public PlatformCapabilities Capabilities => capabilities;
    public IKeyLabels Keys => keys;
}

internal static class PreviewPlatforms
{
    /// <summary>PREVIEW_PLATFORM = web | windows | macos | linux; PREVIEW_FORMFACTOR = desktop | tablet | phone (web only).</summary>
    public static IPlatformInfo From(string? name, string? formFactor)
    {
        var ff = (formFactor ?? "desktop").ToLowerInvariant() switch
        {
            "tablet" => FormFactor.Tablet,
            "phone" => FormFactor.Phone,
            _ => FormFactor.Desktop,
        };
        var touch = ff == FormFactor.Desktop ? InputKinds.Mouse | InputKinds.Keyboard : InputKinds.Touch;
        return (name ?? "web").ToLowerInvariant() switch
        {
            "windows" => new FixedPlatformInfo(PlatformKind.Windows, InputKinds.Mouse | InputKinds.Keyboard,
                new ShellChrome(WindowButtons.Right, false, false, true, 0), FixedPlatformInfo.DesktopCapabilities, new CtrlKeyLabels()),
            "macos" => new FixedPlatformInfo(PlatformKind.MacOS, InputKinds.Mouse | InputKinds.Keyboard,
                new ShellChrome(WindowButtons.Left, true, false, true, 0), FixedPlatformInfo.DesktopCapabilities, new MacKeyLabels()),
            "linux" => new FixedPlatformInfo(PlatformKind.Linux, InputKinds.Mouse | InputKinds.Keyboard,
                new ShellChrome(WindowButtons.Right, false, false, true, 12), FixedPlatformInfo.DesktopCapabilities, new CtrlKeyLabels()),
            // Same values as the Web chat's WebPlatform.WebChrome and capabilities.
            _ => new PreviewPlatformInfo(PlatformKind.Web, ff, touch,
                new ShellChrome(WindowButtons.None, NativeMenuBar: false, AccountMenu: true, TitleBarDrag: false, CornerRadiusPx: 0),
                new PlatformCapabilities { SaveInPlace = false, SavesAsDownload = true, DropFiles = true, ServerSide = true }, new CtrlKeyLabels()),
        };
    }
}
