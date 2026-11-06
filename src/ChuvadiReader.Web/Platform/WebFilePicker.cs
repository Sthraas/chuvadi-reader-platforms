using ChuvadiReader.Core.Reader;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.Options;
using Microsoft.JSInterop;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// The Reader's file dialogs on the portal. "Open" opens the browser's file chooser and uploads the
/// chosen files into this session's folder, returning their server paths — so the unchanged Reader
/// opens them exactly as on the desktop. "Save" and "choose a folder" return a path in the session's
/// outbox; whatever the Reader writes there is downloaded by the browser (<see cref="OutboxDelivery"/>).
/// Nothing outlives the session.
/// </summary>
public sealed class WebFilePicker : IFilePicker
{
    private readonly SessionSpace _space;
    private readonly TransferRegistry _registry;
    private readonly BrowserBridge _browser;
    private readonly OutboxDelivery _outbox;
    private readonly PortalOptions _options;
    private readonly ILogger<WebFilePicker> _log;

    public WebFilePicker(SessionSpace space, TransferRegistry registry, BrowserBridge browser, OutboxDelivery outbox,
        IOptions<PortalOptions> options, ILogger<WebFilePicker> log)
    {
        _space = space;
        _registry = registry;
        _browser = browser;
        _outbox = outbox;
        _options = options.Value;
        _log = log;
    }

    public async Task<string?> PickDocumentAsync(CancellationToken ct = default)
        => (await PickAsync(PickKind.Document, multiple: false, "Open a document", ct).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickDocumentsAsync(CancellationToken ct = default)
        => PickAsync(PickKind.Pdf, multiple: true, "Add PDFs", ct);

    public async Task<string?> PickOpenSessionAsync(CancellationToken ct = default)
        => (await PickAsync(PickKind.Session, multiple: false, "Open a session", ct).ConfigureAwait(false)).FirstOrDefault();

    public Task<IReadOnlyList<string>> PickImagesAsync(CancellationToken ct = default)
        => PickAsync(PickKind.Image, multiple: true, "Fetch images", ct);

    public async Task<string?> PickCertificateAsync(CancellationToken ct = default)
    {
        if (!_options.AllowCertificateUpload)
        {
            return null;
        }

        return (await PickAsync(PickKind.Certificate, multiple: false, "Choose a certificate", ct).ConfigureAwait(false)).FirstOrDefault();
    }

    public Task<string?> PickSavePdfAsync(string suggestedName, CancellationToken ct = default)
        => SaveAsync(suggestedName, ".pdf", "document", ct);

    public Task<string?> PickSaveSessionAsync(string suggestedName, CancellationToken ct = default)
        => SaveAsync(suggestedName, ".json", "session", ct);

    public Task<string?> PickSaveImageAsync(string suggestedName, CancellationToken ct = default)
        => SaveAsync(suggestedName, ".png", "image", ct);

    /// <summary>A fresh outbox folder; every file the Reader writes into it is downloaded.</summary>
    public async Task<string?> PickFolderAsync(CancellationToken ct = default)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        return _outbox.NewFolder();
    }

    private async Task<string?> SaveAsync(string suggestedName, string extension, string fallback, CancellationToken ct)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        var name = SpaceLayout.SafeFileName(suggestedName, fallback);
        if (!name.EndsWith(extension, StringComparison.OrdinalIgnoreCase))
        {
            name += extension;
        }

        var folder = _outbox.NewFolder();
        return Path.Combine(folder, name);
    }

    private async Task<IReadOnlyList<string>> PickAsync(PickKind kind, bool multiple, string title, CancellationToken ct)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        var ticket = _registry.CreateUpload(_space.UserKey, _space.SessionId, _space.Uploads, kind, multiple,
            _options.MaxFilesPerPick, _options.MaxUploadBytes, _options.PickTimeout + TimeSpan.FromMinutes(5));
        try
        {
            var ids = await _browser.PickAndUploadAsync(
                new BrowserBridge.PickRequest(ticket.Id, FileKinds.Accept(kind), multiple, _options.UploadChunkBytes, FileEndpoints.Prefix, title),
                _options.PickTimeout, ct).ConfigureAwait(false);
            if (ids is null || ids.Length == 0)
            {
                return Array.Empty<string>();
            }

            return ticket.Completed(ids).Select(f => f.Path).ToList();
        }
        catch (Exception ex) when (ex is JSDisconnectedException or TaskCanceledException or OperationCanceledException)
        {
            return Array.Empty<string>();
        }
        catch (JSException ex)
        {
            _log.LogWarning("File pick failed in the browser: {Message}", ex.Message);
            return Array.Empty<string>();
        }
        finally
        {
            ticket.DiscardIncomplete();
            _registry.RemoveUpload(ticket.Id);
        }
    }
}
