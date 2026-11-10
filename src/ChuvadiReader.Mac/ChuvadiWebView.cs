using ChuvadiReader.Hosting;
using Microsoft.AspNetCore.Components.WebView.Maui;
using Microsoft.Extensions.FileProviders;

namespace ChuvadiReader.Mac;

/// <summary>
/// The Mac's BlazorWebView with Foundation's page-image hook (D-158, docs/foundation/PAGE-IMAGES.md): drawn raster
/// pages are served from memory at <c>_chvd/pages/&lt;token&gt;.png</c> instead of riding inline as base64. In process,
/// through WKWebView's own app:// scheme handler — no server, nothing leaves the Mac. Default owner ("local").
/// </summary>
internal sealed class ChuvadiWebView(IServiceProvider services) : BlazorWebView
{
    public override IFileProvider CreateFileProvider(string contentRootDir) =>
        new PageImageFileProvider(base.CreateFileProvider(contentRootDir), services);
}
