using ChuvadiReader.Hosting;
using Microsoft.AspNetCore.Components.WebView.Wpf;
using Microsoft.Extensions.FileProviders;

namespace ChuvadiReader.Windows;

/// <summary>
/// The app's BlazorWebView, with drawn page images served from memory by address (D-158). Everything else is
/// served exactly as before.
/// </summary>
public sealed class ChuvadiWebView : BlazorWebView
{
    public override IFileProvider CreateFileProvider(string contentRootDir) =>
        new PageImageFileProvider(base.CreateFileProvider(contentRootDir), Services);
}
