using System.Security.Claims;
using Chuvadi.Pdf.Authoring;
using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Graphics;
using Path = System.IO.Path;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using ChuvadiReader.Web.Platform;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Microsoft.JSInterop;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>Browser printing respects the file's own permissions (L-8).</summary>
public class WebPrintTests
{
    private sealed class SignedIn : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync()
            => Task.FromResult(new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", "print-user")], "test"))));
    }

    /// <summary>Records what the portal asks of the browser.</summary>
    private sealed class RecordingJs : IJSRuntime
    {
        public List<string> Calls { get; } = new();

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, object?[]? args)
        {
            Calls.Add(identifier);
            return ValueTask.FromResult((TValue)(object)(typeof(TValue) == typeof(string) ? "dialog" : true));
        }

        public ValueTask<TValue> InvokeAsync<TValue>(string identifier, CancellationToken cancellationToken, object?[]? args)
            => InvokeAsync<TValue>(identifier, args);
    }

    private readonly string _root = SpaceLayoutTests.NewTempDir();

    private (WebPrintService Service, RecordingJs Js, TransferRegistry Registry, SessionSpace Space) Make()
    {
        var space = new SessionSpace(new SignedIn(), Options.Create(new PortalOptions { DataRoot = _root }), NullLogger<SessionSpace>.Instance);
        var js = new RecordingJs();
        var registry = new TransferRegistry(TimeProvider.System);
        return (new WebPrintService(space, registry, new BrowserBridge(js)), js, registry, space);
    }

    /// <summary>A one-page PDF, encrypted with an open password, with printing allowed or not.</summary>
    private string Pdf(bool allowPrint)
    {
        var plain = Path.Combine(_root, "plain.pdf");
        var builder = PdfDocumentBuilder.Create();
        builder.AddPage(new PageSize(300, 120));
        File.WriteAllBytes(plain, builder.ToByteArray());

        var locked = Path.Combine(_root, (allowPrint ? "may" : "no") + "-print.pdf");
        using (var doc = PdfDocument.Open(plain))
        {
            var enc = Chuvadi.Pdf.IO.EncryptionOptions.Aes256("pw", "owner-" + Guid.NewGuid().ToString("N"));
            // The Reader's own mask builder (bit 3 is printing, PDF 32000-1 table 22); chuvadi-pdf
            // doesn't set permissions publicly yet, so the test sets the property as the Reader's tests do.
            var mask = ChuvadiReader.Core.Documents.PasswordService.BuildPermissionMask(
                new ChuvadiReader.Core.Documents.PasswordProtectOptions { OpenPassword = "pw", AllowPrint = allowPrint });
            typeof(Chuvadi.Pdf.IO.EncryptionOptions).GetProperty("Permissions")!.SetValue(enc, mask);
            using var fs = File.Create(locked);
            doc.Save(fs, enc);
        }

        return locked;
    }

    [Fact]
    public async Task A_file_that_forbids_printing_never_reaches_the_browser()
    {
        var (service, js, _, space) = Make();
        var file = Pdf(allowPrint: false);
        using (var doc = PdfDocument.Open(file, "pw"))
        {
            Assert.False(PrintPermission.Allows(doc));
        }

        foreach (var range in new[] { "", "1" })
        {
            var result = await service.PrintAsync(file, new PrintRequest { Password = "pw", PageRange = range });
            Assert.Equal(PrintOutcome.Failed, result.Outcome);
            Assert.Equal(PrintPermission.Refused, result.Message);
        }

        Assert.DoesNotContain("chvdPortal.print", js.Calls);
        Assert.Empty(Directory.EnumerateFiles(space.Print, "*", SearchOption.AllDirectories)); // no unprotected copy made
    }

    [Fact]
    public async Task A_protected_file_that_allows_printing_still_prints()
    {
        var (service, js, _, _) = Make();
        var result = await service.PrintAsync(Pdf(allowPrint: true), new PrintRequest { Password = "pw" });
        Assert.Equal(PrintOutcome.Printed, result.Outcome);
        Assert.Contains("chvdPortal.print", js.Calls);
    }
}
