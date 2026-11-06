using ChuvadiReader.Core.Reader;
using ChuvadiReader.Core.Window;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Files;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// Text and image copy through the browser's Clipboard API (needs HTTPS, which production has).
/// Serves both <see cref="IClipboard"/> and <see cref="IImageClipboard"/> (Foundation F-6 keeps both).
/// Unlike the desktop, which ignores a locked clipboard, a refusal is reported: the Reader then shows
/// the message instead of "Copied to clipboard", which would be untrue here.
/// </summary>
public sealed class WebClipboard : IClipboard, IImageClipboard
{
    private readonly BrowserBridge _browser;

    public WebClipboard(BrowserBridge browser) => _browser = browser;

    public bool CanCopyText => true;

    public bool CanCopyImage => true;

    public async Task SetTextAsync(string text, CancellationToken ct = default)
    {
        bool ok;
        try
        {
            ok = await _browser.CopyTextAsync(text ?? string.Empty, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is JSException or JSDisconnectedException)
        {
            throw new InvalidOperationException("The browser didn't allow copying.", ex);
        }

        if (!ok)
        {
            throw new InvalidOperationException("The browser didn't allow copying.");
        }
    }

    public async Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return;
        }

        bool ok;
        try
        {
            ok = await _browser.CopyImageAsync(pngBytes, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is JSException or JSDisconnectedException)
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

/// <summary>
/// Foundation F-1 write-back on the portal: Save and Save as become a browser download. A file is
/// delivered at once; a folder (from a folder pick) delivers every file in it.
/// </summary>
public sealed class WebFileWriteBack : IFileWriteBack
{
    private readonly OutboxDelivery _delivery;
    private readonly SessionSpace _space;

    public WebFileWriteBack(OutboxDelivery delivery, SessionSpace space)
    {
        _delivery = delivery;
        _space = space;
    }

    public bool IsNeeded => true;

    public async Task<WriteBackResult> CommitAsync(string localPath, CancellationToken ct = default)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        if (!_space.Contains(localPath))
        {
            // Only this session's own files can be handed out.
            return new WriteBackResult(WriteBackOutcome.Failed, "That file isn't part of this session.");
        }

        return await _delivery.DeliverAsync(localPath, ct).ConfigureAwait(false);
    }
}
