using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>Typed calls into <c>wwwroot/js/portal.js</c> (<c>window.chvdPortal</c>). Scoped: one per circuit.</summary>
public sealed class BrowserBridge
{
    private readonly IJSRuntime _js;

    public BrowserBridge(IJSRuntime js) => _js = js;

    public sealed record PickRequest(string Ticket, string Accept, bool Multiple, int ChunkBytes, string Base, string Title);

    /// <summary>Opens the browser's file chooser and uploads the chosen files. Returns the server's
    /// file ids, or null/empty when the person cancelled.</summary>
    public ValueTask<string[]?> PickAndUploadAsync(PickRequest request, TimeSpan timeout, CancellationToken ct)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeout);
        return _js.InvokeAsync<string[]?>("chvdPortal.pick", cts.Token, request);
    }

    /// <summary>Hands a file to the browser as a download.</summary>
    public ValueTask DownloadAsync(string url, string fileName, CancellationToken ct)
        => _js.InvokeVoidAsync("chvdPortal.download", ct, url, fileName);

    /// <summary>Loads the print document in a hidden frame and opens the browser's print dialog.
    /// Returns false when the browser couldn't load it.</summary>
    public ValueTask<bool> PrintAsync(string url, CancellationToken ct)
        => _js.InvokeAsync<bool>("chvdPortal.print", ct, url);

    /// <summary>Puts a PNG on the clipboard. Returns false when the browser refused.</summary>
    public ValueTask<bool> CopyImageAsync(byte[] png, CancellationToken ct)
    {
        var stream = new DotNetStreamReference(new MemoryStream(png, writable: false));
        return _js.InvokeAsync<bool>("chvdPortal.copyImage", ct, stream);
    }

    /// <summary>Sends the browser to another address of the portal (sign-out, expiry).</summary>
    public async Task LeaveAsync(string path, TimeSpan timeout)
    {
        using var cts = new CancellationTokenSource(timeout);
        await _js.InvokeVoidAsync("chvdPortal.leave", cts.Token, path).ConfigureAwait(false);
    }

    /// <summary>Puts text on the clipboard. Returns false when the browser refused.</summary>
    public ValueTask<bool> CopyTextAsync(string text, CancellationToken ct)
        => _js.InvokeAsync<bool>("chvdPortal.copyText", ct, text);

    /// <summary>Opens a link in a new browser tab, without giving it a handle back to the portal.</summary>
    public ValueTask<bool> OpenLinkAsync(string url) => _js.InvokeAsync<bool>("chvdPortal.openLink", url);
}
