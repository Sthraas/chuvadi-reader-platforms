using System.Collections.Concurrent;
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Web.Files;

namespace ChuvadiReader.Web.Platform;

/// <summary>
/// The Reader's settings store on the portal: in memory, for this session only (no server storage in
/// this release — Arun, 6 Nov). One default differs from the desktop: the save folder
/// (<c>save-folder</c>) is the session's own "Chuvadi Documents" folder instead of the server
/// account's Documents, and every file the Reader saves there is downloaded by the browser.
/// </summary>
public sealed class SessionAppStorage : IAppStorage
{
    /// <summary>The key <see cref="ChuvadiReader.Core.Documents.SaveFolderService"/> reads.</summary>
    public const string SaveFolderKey = "save-folder";

    private readonly ConcurrentDictionary<string, string> _values = new(StringComparer.Ordinal);
    private readonly SessionSpace _space;
    private readonly OutboxDelivery _outbox;

    public SessionAppStorage(SessionSpace space, OutboxDelivery outbox)
    {
        _space = space;
        _outbox = outbox;
    }

    public async Task<string?> GetAsync(string key, CancellationToken ct = default)
    {
        if (_values.TryGetValue(key, out var value))
        {
            return value;
        }

        if (key == SaveFolderKey)
        {
            await _space.EnsureAsync(ct).ConfigureAwait(false);
            var folder = Path.Combine(_space.Outbox, "Chuvadi Documents");
            SpaceLayout.CreatePrivateDirectory(folder);
            _outbox.Watch(folder, untilSessionEnds: true);
            _values.TryAdd(key, folder);
            return _values[key];
        }

        return null;
    }

    public async Task SetAsync(string key, string value, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(key);
        if (key == SaveFolderKey && !string.IsNullOrWhiteSpace(value))
        {
            // Only folders inside this session's outbox; anything else would write to the server's disk outside the session.
            await _space.EnsureAsync(ct).ConfigureAwait(false);
            if (!SpaceLayout.IsInside(_space.Outbox, Path.Combine(value, "x")))
            {
                return;
            }

            _outbox.Watch(value, untilSessionEnds: true);
        }

        _values[key] = value ?? string.Empty;
    }
}
