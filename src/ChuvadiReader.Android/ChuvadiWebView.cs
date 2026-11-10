using ChuvadiReader.Hosting;
using Microsoft.AspNetCore.Components.WebView.Maui;
using Microsoft.Extensions.FileProviders;

namespace ChuvadiReader.Android;

/// <summary>
/// The app's BlazorWebView, with drawn page images (<c>_chvd/pages/&lt;token&gt;.png</c>) served from memory by
/// address, in process, through the WebView's own file-provider hook (D-158, Foundation's PAGE-IMAGES.md). Every
/// other path is served exactly as before.
/// </summary>
public sealed class ChuvadiWebView : BlazorWebView
{
    public override IFileProvider CreateFileProvider(string contentRootDir) =>
        new PageImageFileProvider(base.CreateFileProvider(contentRootDir),
            Handler?.MauiContext?.Services ?? IPlatformApplication.Current!.Services);
}
