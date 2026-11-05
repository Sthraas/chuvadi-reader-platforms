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
    /// given build, so everything but the host page may be cached by the web view.</summary>
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

        if (!TryGetResponseContent(uri, allowFallbackOnHostPage: true, out status, out _, out var content, out var headers))
        {
            return false;
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
        cacheControl = isHostPage ? "no-cache" : "max-age=31536000, immutable";
        return true;
    }

    /// <summary>Main thread (from the script message handler).</summary>
    public void Receive(string message) => MessageReceived(AppBase, message);

    protected override void NavigateCore(Uri absoluteUri)
    {
        var target = absoluteUri.ToString();
        GtkHost.Post(() => Native.Navigate(target));
    }

    protected override void SendMessage(string message) => GtkHost.SendToPage(message);
}
