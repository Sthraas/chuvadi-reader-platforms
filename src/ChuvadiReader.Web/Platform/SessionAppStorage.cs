using System.Collections.Concurrent;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Web.Files;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// The Reader's settings store on the portal: in memory, for the signed-in session only (no server storage
/// in this release — Arun, 6 Nov). The values belong to the session (D-174), so a reload or a second browser
/// tab of the same sign-in finds the same open tabs, recents and preferences; they go when the session ends.
/// One value is kept per connection and differs from the desktop: the save folder (<c>save-folder</c>) is this
/// connection's own "Chuvadi Documents" folder inside the session's outbox, and every file the Reader saves
/// there is downloaded by this connection's browser tab (not by another tab of the same session).
/// </summary>
public sealed class SessionAppStorage : IAppStorage
{
    /// <summary>The key <see cref="ChuvadiReader.Core.Documents.SaveFolderService"/> reads.</summary>
    public const string SaveFolderKey = "save-folder";

    private readonly SessionSpace _space;
    private readonly OutboxDelivery _outbox;
    private string? _saveFolder;

    public SessionAppStorage(SessionSpace space, OutboxDelivery outbox)
    {
        _space = space;
        _outbox = outbox;
    }

    public async Task<string?> GetAsync(string key, CancellationToken ct = default)
    {
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        if (key == SaveFolderKey)
        {
            if (_saveFolder is null)
            {
                var folder = Path.Combine(_space.Outbox, _space.ConnectionId[..8], "Chuvadi Documents");
                SpaceLayout.CreatePrivateDirectory(Path.GetDirectoryName(folder)!);
                SpaceLayout.CreatePrivateDirectory(folder);
                _outbox.Watch(folder, untilSessionEnds: true);
                _saveFolder = folder;
            }

            return _saveFolder;
        }

        return _space.State.Values.TryGetValue(key, out var value) ? value : null;
    }

    public async Task SetAsync(string key, string value, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(key);
        await _space.EnsureAsync(ct).ConfigureAwait(false);
        if (key == SaveFolderKey)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return;
            }

            // Only folders inside this session's outbox; anything else would write to the server's disk outside the session.
            if (!SpaceLayout.IsInside(_space.Outbox, Path.Combine(value, "x")))
            {
                return;
            }

            _outbox.Watch(value, untilSessionEnds: true);
            _saveFolder = value;
            return;
        }

        if (!_space.State.Ended) // a session that has ended keeps nothing new
        {
            _space.State.Values[key] = value ?? string.Empty;
        }
    }
}
