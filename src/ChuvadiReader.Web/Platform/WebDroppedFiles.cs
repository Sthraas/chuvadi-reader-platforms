using ChuvadiReader.Hosting;
using ChuvadiReader.Platform;
using ChuvadiReader.Web.Files;
using ChuvadiReader.Web.Hosting;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// Files dropped on the portal window (D-89 A; the Ui's <c>PortalDropCatcher</c> catches the drop). Each
/// file streams from the browser into the session's private uploads folder through the same
/// <see cref="UploadTicket"/> the upload endpoint uses, so drops get exactly the upload's checks and
/// messages: allowed document types, the size limit, content matching the extension, owner-only folder.
/// Accepted files open through the kit's <see cref="IncomingFiles"/> (one tab each, or the Bench shelf
/// when it's open). Per session (scoped).
/// </summary>
public sealed class WebDroppedFiles : IDroppedFiles
{
    /// <summary>Most files in one drop (the Ui also stops at 64).</summary>
    public const int MaxFilesPerDrop = 64;

    private readonly SessionSpace _space;
    private readonly IncomingFiles _incoming;
    private readonly PortalOptions _options;
    private readonly ILogger<WebDroppedFiles> _log;

    public WebDroppedFiles(SessionSpace space, IncomingFiles incoming, IOptions<PortalOptions> options, ILogger<WebDroppedFiles> log)
    {
        _space = space;
        _incoming = incoming;
        _options = options.Value;
        _log = log;
    }

    public bool IsAvailable => true;

    public long MaxFileBytes => _options.MaxUploadBytes;

    public async Task<IReadOnlyList<string>> ReceiveAsync(IReadOnlyList<DroppedFile> files, CancellationToken ct = default)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        var ticket = new UploadTicket("drop", _space.UserKey, _space.ConnectionId, _space.Uploads, PickKind.Document,
            MaxFilesPerDrop, MaxFileBytes, DateTimeOffset.MaxValue);
        var problems = new List<string>();
        var stored = new List<string>();
        foreach (var file in files)
        {
            var (upload, error) = ticket.Begin(file.Name, file.Size);
            if (upload is null)
            {
                problems.Add(error!);
                continue;
            }

            try
            {
                // Read once, here: the browser stream can't be reopened later.
                await using var stream = file.OpenRead(ct);
                if (await upload.AppendAsync(0, stream, MaxFileBytes, ct).ConfigureAwait(false) is { } refused)
                {
                    problems.Add(refused == "More bytes than announced." ? $"{upload.Name} changed while it was uploading." : refused);
                }
                else if (!upload.IsComplete)
                {
                    problems.Add($"{upload.Name} didn't arrive completely.");
                }
                else
                {
                    stored.Add(upload.Path);
                }
            }
            catch (IOException ex)
            {
                // Blazor's InputFile reports a file over the limit, or a broken connection, as an IOException.
                _log.LogInformation("A dropped file didn't arrive: {Message}", ex.Message);
                problems.Add($"{upload.Name} couldn't be uploaded.");
            }
        }

        ticket.DiscardIncomplete();
        if (stored.Count > 0)
        {
            _incoming.Receive(stored);
        }

        return problems;
    }
}
