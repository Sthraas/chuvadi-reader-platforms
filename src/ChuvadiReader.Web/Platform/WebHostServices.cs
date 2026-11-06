using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>Copies an image to the person's clipboard through the browser's Clipboard API.</summary>
public sealed class WebImageClipboard : IImageClipboard
{
    private readonly BrowserBridge _browser;

    public WebImageClipboard(BrowserBridge browser) => _browser = browser;

    public async Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return;
        }

        // Unlike the desktop (which ignores a locked clipboard), a refusal is reported: the Reader
        // shows the message instead of "Copied to clipboard", which would be untrue here.
        bool ok;
        try
        {
            ok = await _browser.CopyImageAsync(pngBytes, ct).ConfigureAwait(false);
        }
        catch (JSException ex)
        {
            throw new InvalidOperationException("The browser didn't allow copying the image.", ex);
        }

        if (!ok)
        {
            throw new InvalidOperationException("The browser didn't allow copying the image.");
        }
    }
}

/// <summary>Opens http, https and mailto links in a new browser tab (no opener).</summary>
public sealed class WebExternalLinks : IExternalLinks
{
    private readonly BrowserBridge _browser;

    public WebExternalLinks(BrowserBridge browser) => _browser = browser;

    public bool IsAvailable => true;

    public async Task<bool> OpenAsync(string url)
    {
        if (!IExternalLinks.IsAllowed(url))
        {
            return false;
        }

        try
        {
            return await _browser.OpenLinkAsync(url).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is JSException or JSDisconnectedException)
        {
            return false;
        }
    }
}
