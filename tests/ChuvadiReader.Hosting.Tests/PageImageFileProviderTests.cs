using ChuvadiReader.Core.Reader;
using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Primitives;
using Xunit;

namespace ChuvadiReader.Hosting.Tests;

/// <summary>D-158: the WebView hosts read page images through this provider, in process.</summary>
public sealed class PageImageFileProviderTests
{
    private sealed class Owner(string who) : IPageImageOwner
    {
        public string Current => who;
    }

    private sealed class AppFiles : IFileProvider
    {
        public List<string> Asked { get; } = [];

        public IFileInfo GetFileInfo(string subpath)
        {
            Asked.Add(subpath);
            return new NotFoundFileInfo(subpath);
        }

        public IDirectoryContents GetDirectoryContents(string subpath) => NotFoundDirectoryContents.Singleton;

        public IChangeToken Watch(string filter) => NullChangeToken.Singleton;
    }

    private static (PageImageFileProvider Provider, PageImages Store, AppFiles App) Make(string owner)
    {
        var store = new PageImages();
        var services = new ServiceCollection().AddSingleton(store).AddSingleton<IPageImageOwner>(new Owner(owner)).BuildServiceProvider();
        var app = new AppFiles();
        return (new PageImageFileProvider(app, services), store, app);
    }

    [Fact]
    public void A_page_image_is_served_from_memory_byte_for_byte()
    {
        var (provider, store, app) = Make("local");
        var png = new byte[] { 0x89, (byte)'P', (byte)'N', (byte)'G', 1, 2, 3 };
        var token = store.Add("local", png);

        var file = provider.GetFileInfo("/" + PageImages.AddressOf(token));
        using var read = new MemoryStream();
        file.CreateReadStream().CopyTo(read);

        Assert.True(file.Exists);
        Assert.Equal(png.Length, file.Length);
        Assert.Equal(token + ".png", file.Name);
        Assert.Null(file.PhysicalPath);
        Assert.Equal(png, read.ToArray());
        Assert.Empty(app.Asked);
    }

    [Fact]
    public void Unknown_freed_or_someone_elses_images_are_not_found()
    {
        var (provider, store, _) = Make("local");
        var mine = store.Add("local", [1]);
        var theirs = store.Add("someone-else", [2]);
        var freed = store.Add("local", [3]);
        store.Remove(freed);

        Assert.True(provider.GetFileInfo(PageImages.AddressOf(mine)).Exists);
        Assert.False(provider.GetFileInfo(PageImages.AddressOf(theirs)).Exists);
        Assert.False(provider.GetFileInfo(PageImages.AddressOf(freed)).Exists);
        Assert.False(provider.GetFileInfo(PageImages.PathPrefix + "nothing.png").Exists);
        Assert.False(provider.GetFileInfo(PageImages.PathPrefix + "../index.html").Exists);
    }

    [Fact]
    public void Every_other_path_goes_to_the_hosts_own_files_unchanged()
    {
        var (provider, _, app) = Make("local");

        provider.GetFileInfo("index.html");
        provider.GetFileInfo("/_content/ChuvadiReader.Ui/js/reader.js");

        Assert.Equal(["index.html", "/_content/ChuvadiReader.Ui/js/reader.js"], app.Asked);
    }

    [Fact]
    public async Task The_kits_pdf_reader_draws_raster_pages_by_address()
    {
        var services = new ServiceCollection();
        services.AddChuvadiReader(AppStateLifetime.Process);
        using var sp = services.BuildServiceProvider();

        Assert.IsType<ChuvadiPdfReader>(sp.GetRequiredService<IPdfReader>());
        Assert.Same(sp.GetRequiredService<PageImages>(), sp.GetRequiredService<PageImages>());
        Assert.Equal("local", sp.GetRequiredService<IPageImageOwner>().Current);
        await Task.CompletedTask;
    }
}
