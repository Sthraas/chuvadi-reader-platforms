using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Interface size on Android: the host does not zoom the WebView, so the UI's own CSS-zoom
/// path (PreferencesInterop / theme.js) applies 100 / 125 / 150 %. Same visual result as
/// Windows, no host-side zoom code.
/// </summary>
public sealed class AndroidUiScale : IUiScale
{
    public bool IsSupported => false;

    public void SetScale(int percent)
    {
    }
}

/// <summary>Opens http, https and mailto links in the user's browser or mail app.</summary>
public sealed class AndroidExternalLinks : IExternalLinks
{
    public bool IsAvailable => true;

    public async Task<bool> OpenAsync(string url)
    {
        if (!IExternalLinks.IsAllowed(url))
        {
            return false;
        }

        try
        {
            return await MainThread.InvokeOnMainThreadAsync(() => Launcher.Default.OpenAsync(new Uri(url))).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is FeatureNotSupportedException or InvalidOperationException)
        {
            return false;
        }
    }
}

/// <summary>
/// Android owns the window: there is no minimise, maximise, close or drag. The app always fills
/// its window (or its split-screen half), so it reports itself as maximised and the controls do
/// nothing. The title-bar buttons are hidden by the host stylesheet (A-03).
/// </summary>
public sealed class AndroidWindowControls : IWindowControls
{
    public bool IsMaximized => true;

#pragma warning disable CS0067 // never raised: an Android window has no maximise/restore state
    public event Action? StateChanged;
#pragma warning restore CS0067

    public void Minimize()
    {
    }

    public void ToggleMaximize()
    {
    }

    public void Close()
    {
    }

    public void BeginDrag()
    {
    }
}

/// <summary>
/// Printing on Android is not wired yet: its design (Chuvadi.Print.Ipp to network printers vs
/// Android's own print framework, or both) is waiting on Arun — A-04 in docs/android/DECISIONS.md.
/// IsAvailable = false greys out the Print card with the UI's normal "not available" state.
/// </summary>
public sealed class AndroidPrintService : IPrintService
{
    public bool IsAvailable => false;

    public Task<PrintResult> PrintAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
        => Task.FromResult(new PrintResult(PrintOutcome.Unavailable, 0, "Printing is not available on Android yet."));
}
