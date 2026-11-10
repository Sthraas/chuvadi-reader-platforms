using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Primitives;

namespace ChuvadiReader.Hosting;

/// <summary>
/// D-158: serves drawn page images (<c>_chvd/pages/&lt;token&gt;.png</c>) to a BlazorWebView from memory, and passes
/// every other path to the host's own provider. It runs in the app's process through the WebView's file-provider
/// hook: no localhost server, nothing leaves the device. A token that is unknown, freed or someone else's answers
/// "not found", the same as a file that doesn't exist.
/// <code>
/// // WPF, WinForms, MAUI (Mac, Android) BlazorWebView subclass:
/// public override IFileProvider CreateFileProvider(string contentRootDir) =>
///     new PageImageFileProvider(base.CreateFileProvider(contentRootDir), Services);
/// // A WebViewManager (Linux): pass new PageImageFileProvider(yourProvider, services) as its file provider.
/// </code>
/// </summary>
public sealed class PageImageFileProvider : IFileProvider
{
    private readonly IFileProvider _inner;
    private readonly IServiceProvider _services;
    private PageImages? _images;
    private IPageImageOwner? _owner;

    /// <param name="inner">The host's own provider (the app's wwwroot and static web assets).</param>
    /// <param name="services">The app's services; the store and owner are read from them on first use.</param>
    public PageImageFileProvider(IFileProvider inner, IServiceProvider services)
    {
        ArgumentNullException.ThrowIfNull(inner);
        ArgumentNullException.ThrowIfNull(services);
        _inner = inner;
        _services = services;
    }

    public IFileInfo GetFileInfo(string subpath)
    {
        if (!(subpath ?? string.Empty).TrimStart('/').StartsWith(PageImages.PathPrefix, StringComparison.Ordinal))
        {
            return _inner.GetFileInfo(subpath!);
        }

        _images ??= (PageImages?)_services.GetService(typeof(PageImages));
        _owner ??= (IPageImageOwner?)_services.GetService(typeof(IPageImageOwner));
        return PageImages.TryParseAddress(subpath, out var token) && _images is not null && _owner is not null
            && _images.TryGet(token, _owner.Current, out var png)
            ? new PngFile(token, png)
            : new NotFoundFileInfo(subpath!);
    }

    public IDirectoryContents GetDirectoryContents(string subpath) => _inner.GetDirectoryContents(subpath);

    public IChangeToken Watch(string filter) => _inner.Watch(filter);

    /// <summary>One page image, read from memory (no copy).</summary>
    private sealed class PngFile(string token, ReadOnlyMemory<byte> png) : IFileInfo
    {
        public bool Exists => true;

        public long Length => png.Length;

        public string? PhysicalPath => null;

        public string Name => token + ".png";

        public DateTimeOffset LastModified { get; } = DateTimeOffset.UtcNow;

        public bool IsDirectory => false;

        public Stream CreateReadStream() =>
            System.Runtime.InteropServices.MemoryMarshal.TryGetArray(png, out var segment)
                ? new MemoryStream(segment.Array!, segment.Offset, segment.Count, writable: false)
                : new MemoryStream(png.ToArray(), writable: false);
    }
}
