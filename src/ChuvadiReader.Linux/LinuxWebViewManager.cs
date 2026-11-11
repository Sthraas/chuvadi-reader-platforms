using ChuvadiReader.Core.Reader;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebView;
using Microsoft.Extensions.FileProviders;

namespace ChuvadiReader.Linux;

/// <summary>
/// Microsoft's <see cref="WebViewManager"/> wired to the WebKitGTK view. The manager does all
/// of Blazor's work (rendering, the IPC protocol, serving <c>_framework/blazor.webview.js</c>
/// and every <c>_content/…</c> static web asset); this class only moves bytes and messages
/// between it and the native shim.
/// </summary>
internal sealed class LinuxWebViewManager : WebViewManager
{
    public static readonly Uri AppBase = new("app://localhost/");

    public LinuxWebViewManager(IServiceProvider services, IFileProvider fileProvider)
        : base(services, Dispatcher.CreateDefault(), AppBase, fileProvider, new JSComponentConfigurationStore(), "index.html")
    {
    }

    /// <summary>Main thread (from the native scheme handler). App assets are immutable for a
    /// given build, so everything but the host page and drawn page images may be cached by the web view.</summary>
    public bool TryGetAsset(string uri, out int status, out string contentType, out byte[] body, out string? cacheControl)
    {
        status = 404;
        contentType = "text/plain";
        body = Array.Empty<byte>();
        cacheControl = null;

        if (!AppBase.IsBaseOf(new Uri(uri)))
        {
            return false;
        }

        // A page image's address is only ever the image (D-158): unknown, freed or another owner's token is "not
        // found", never the host page that other unknown addresses fall back to.
        var isPageImage = new Uri(uri).AbsolutePath.TrimStart('/').StartsWith(PageImages.PathPrefix, StringComparison.Ordinal);
        if (!TryGetResponseContent(uri, allowFallbackOnHostPage: !isPageImage, out status, out _, out var content, out var headers))
        {
            status = 404;
            return isPageImage; // answered "not found" here rather than left to the native fallback
        }

        using (content)
        {
            if (content is MemoryStream ms && ms.TryGetBuffer(out var seg) && seg.Offset == 0 && seg.Count == seg.Array!.Length)
            {
                body = seg.Array;
            }
            else
            {
                using var copy = new MemoryStream(content.CanSeek ? (int)Math.Max(0, content.Length) : 0);
                content.CopyTo(copy);
                body = copy.ToArray();
            }
        }

        contentType = headers.TryGetValue("Content-Type", out var ct) ? ct : "application/octet-stream";
        var path = new Uri(uri).AbsolutePath;
        var isHostPage = path == "/" || path.EndsWith(".html", StringComparison.OrdinalIgnoreCase);
        // A drawn page image (D-158) is large and freed with its page: never kept in the web view's cache.
        cacheControl = isPageImage ? "private, no-store" : isHostPage ? "no-cache" : "max-age=31536000, immutable";
        if (isHostPage)
        {
            body = Platform.HostPageTheme.Apply(body, StartTheme);
        }

        return true;
    }

    /// <summary>The saved theme ("dark", "palm", …), set before the first navigation. The host page is served with
    /// it already on its root element, so its first paint is in that theme: without it the page painted light
    /// parchment between the window's own pre-paint colour and the app's first render (a light flash in dark).</summary>
    public string? StartTheme { get; set; }

    /// <summary>Main thread (from the script message handler).</summary>
    public void Receive(string message) => MessageReceived(AppBase, message);

    protected override void NavigateCore(Uri absoluteUri)
    {
        var target = absoluteUri.ToString();
        GtkHost.Post(() => Native.Navigate(target));
    }

    protected override void SendMessage(string message) => GtkHost.SendToPage(message);
}
