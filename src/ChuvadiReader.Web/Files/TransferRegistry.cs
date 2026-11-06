using System.Collections.Concurrent;
using System.Security.Cryptography;

namespace ChuvadiReader.Web.Files;

/// <summary>
/// Short-lived, unguessable tickets that let the browser move bytes in and out of one person's
/// session folder over plain HTTP (not through the Blazor circuit, so large files stream instead of
/// being held in memory). Every ticket is bound to the user key and session that created it; the
/// endpoints check the signed-in user again on every request. Singleton.
/// </summary>
public sealed class TransferRegistry
{
    private readonly ConcurrentDictionary<string, UploadTicket> _uploads = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, DownloadTicket> _downloads = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, PrintTicket> _prints = new(StringComparer.Ordinal);
    private readonly TimeProvider _time;

    public TransferRegistry(TimeProvider time) => _time = time;

    public static string NewToken() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(24))
        .Replace('+', '-').Replace('/', '_').TrimEnd('=');

    // ── uploads ──────────────────────────────────────────────────────────────

    public UploadTicket CreateUpload(string userKey, string sessionId, string uploadsFolder, PickKind kind, bool multiple,
        int maxFiles, long maxBytes, TimeSpan lifetime)
    {
        var t = new UploadTicket(NewToken(), userKey, sessionId, uploadsFolder, kind, multiple ? maxFiles : 1, maxBytes,
            _time.GetUtcNow() + lifetime);
        _uploads[t.Id] = t;
        return t;
    }

    public UploadTicket? FindUpload(string id, string userKey)
        => _uploads.TryGetValue(id, out var t) && t.UserKey == userKey && t.ExpiresAt > _time.GetUtcNow() ? t : null;

    public void RemoveUpload(string id) => _uploads.TryRemove(id, out _);

    // ── downloads ────────────────────────────────────────────────────────────

    public DownloadTicket CreateDownload(string userKey, string sessionId, string path, string fileName, TimeSpan lifetime, bool deleteAfter)
    {
        var t = new DownloadTicket(NewToken(), userKey, sessionId, path, fileName, _time.GetUtcNow() + lifetime, deleteAfter);
        _downloads[t.Id] = t;
        return t;
    }

    /// <summary>Takes a download ticket (single use) when it belongs to <paramref name="userKey"/>.</summary>
    public DownloadTicket? TakeDownload(string id, string userKey)
    {
        if (!_downloads.TryGetValue(id, out var t) || t.UserKey != userKey)
        {
            return null;
        }

        if (!_downloads.TryRemove(new KeyValuePair<string, DownloadTicket>(id, t)))
        {
            return null;
        }

        return t.ExpiresAt > _time.GetUtcNow() ? t : null;
    }

    // ── print ────────────────────────────────────────────────────────────────

    public PrintTicket CreatePrint(string userKey, string sessionId, string pdfPath, string title, TimeSpan lifetime)
    {
        var t = new PrintTicket(NewToken(), userKey, sessionId, pdfPath, title, _time.GetUtcNow() + lifetime);
        _prints[t.Id] = t;
        return t;
    }

    public PrintTicket? FindPrint(string id, string userKey)
        => _prints.TryGetValue(id, out var t) && t.UserKey == userKey && t.ExpiresAt > _time.GetUtcNow() ? t : null;

    public void RemovePrint(string id) => _prints.TryRemove(id, out _);

    /// <summary>Forgets every ticket of a session (called when it ends).</summary>
    public void ForgetSession(string sessionId)
    {
        foreach (var (k, v) in _uploads)
        {
            if (v.SessionId == sessionId) _uploads.TryRemove(k, out _);
        }

        foreach (var (k, v) in _downloads)
        {
            if (v.SessionId == sessionId) _downloads.TryRemove(k, out _);
        }

        foreach (var (k, v) in _prints)
        {
            if (v.SessionId == sessionId) _prints.TryRemove(k, out _);
        }
    }

    /// <summary>Drops expired tickets. Called periodically.</summary>
    public int Prune()
    {
        var now = _time.GetUtcNow();
        int n = 0;
        foreach (var (k, v) in _uploads)
        {
            if (v.ExpiresAt <= now && _uploads.TryRemove(k, out _)) n++;
        }

        foreach (var (k, v) in _downloads)
        {
            if (v.ExpiresAt <= now && _downloads.TryRemove(k, out _)) n++;
        }

        foreach (var (k, v) in _prints)
        {
            if (v.ExpiresAt <= now && _prints.TryRemove(k, out _)) n++;
        }

        return n;
    }

    internal int Count => _uploads.Count + _downloads.Count + _prints.Count;
}

/// <summary>One pick's upload: the files the browser announces, then their bytes in order.</summary>
public sealed class UploadTicket
{
    private readonly object _lock = new();
    private readonly List<UploadFile> _files = new();

    internal UploadTicket(string id, string userKey, string sessionId, string folder, PickKind kind, int maxFiles, long maxBytes, DateTimeOffset expiresAt)
    {
        Id = id;
        UserKey = userKey;
        SessionId = sessionId;
        Folder = folder;
        Kind = kind;
        MaxFiles = maxFiles;
        MaxBytes = maxBytes;
        ExpiresAt = expiresAt;
    }

    public string Id { get; }
    public string UserKey { get; }
    public string SessionId { get; }
    public string Folder { get; }
    public PickKind Kind { get; }
    public int MaxFiles { get; }
    public long MaxBytes { get; }
    public DateTimeOffset ExpiresAt { get; }

    /// <summary>Announces a file. Returns null with a user-facing reason when it can't be accepted.</summary>
    public (UploadFile? File, string? Error) Begin(string? name, long size)
    {
        var safe = SpaceLayout.SafeFileName(name, "document");
        if (!FileKinds.HasAllowedExtension(Kind, safe))
        {
            return (null, $"{safe}: this kind of file can't be opened here.");
        }

        if (size <= 0)
        {
            return (null, $"{safe} is empty.");
        }

        if (size > MaxBytes)
        {
            return (null, $"{safe} is larger than the {MaxBytes / (1024 * 1024)} MB limit.");
        }

        lock (_lock)
        {
            if (_files.Count >= MaxFiles)
            {
                return (null, MaxFiles == 1 ? "Choose one file." : $"Choose at most {MaxFiles} files.");
            }

            var dir = Path.Combine(Folder, NewFolderName());
            SpaceLayout.CreatePrivateDirectory(dir);
            var f = new UploadFile(_files.Count.ToString(System.Globalization.CultureInfo.InvariantCulture), Path.Combine(dir, safe), safe, size);
            _files.Add(f);
            return (f, null);
        }
    }

    public UploadFile? Find(string fileId)
    {
        lock (_lock)
        {
            return _files.FirstOrDefault(f => f.Id == fileId);
        }
    }

    /// <summary>Completed files with the given ids, in the order asked.</summary>
    public IReadOnlyList<UploadFile> Completed(IEnumerable<string> ids)
    {
        lock (_lock)
        {
            return ids.Select(id => _files.FirstOrDefault(f => f.Id == id)).Where(f => f is { IsComplete: true }).Cast<UploadFile>().ToList();
        }
    }

    /// <summary>Removes files whose upload never finished.</summary>
    public void DiscardIncomplete()
    {
        lock (_lock)
        {
            foreach (var f in _files.Where(f => !f.IsComplete))
            {
                f.Discard();
            }
        }
    }

    private static string NewFolderName() => Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(8));
}

/// <summary>One file of an upload, written strictly in order.</summary>
public sealed class UploadFile
{
    private readonly SemaphoreSlim _write = new(1, 1);

    internal UploadFile(string id, string path, string name, long size)
    {
        Id = id;
        Path = path;
        Name = name;
        Size = size;
    }

    public string Id { get; }
    public string Path { get; }
    public string Name { get; }
    public long Size { get; }
    public long Received { get; private set; }
    public bool IsComplete { get; private set; }
    public bool IsRejected { get; private set; }

    /// <summary>Appends one chunk that starts at <paramref name="offset"/>. Returns an error text or null.</summary>
    public async Task<string?> AppendAsync(long offset, Stream body, long maxChunk, CancellationToken ct)
    {
        await _write.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (IsComplete || IsRejected)
            {
                return "This file is already finished.";
            }

            if (offset != Received)
            {
                return $"Expected bytes from {Received}, got {offset}.";
            }

            var mode = Received == 0 ? FileMode.CreateNew : FileMode.Append;
            long written = 0;
            var fso = new FileStreamOptions { Mode = mode, Access = FileAccess.Write, Share = FileShare.None };
            if (!OperatingSystem.IsWindows() && mode == FileMode.CreateNew)
            {
                fso.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
            }

            await using (var fs = new FileStream(Path, fso))
            {
                var buffer = new byte[81920];
                int n;
                while ((n = await body.ReadAsync(buffer, ct).ConfigureAwait(false)) > 0)
                {
                    written += n;
                    if (written > maxChunk || Received + written > Size)
                    {
                        fs.SetLength(Received);
                        return "More bytes than announced.";
                    }

                    await fs.WriteAsync(buffer.AsMemory(0, n), ct).ConfigureAwait(false);
                }
            }

            Received += written;
            if (Received == Size)
            {
                var head = new byte[(int)Math.Min(1024, Size)];
                await using (var check = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.Read))
                {
                    await check.ReadExactlyAsync(head, ct).ConfigureAwait(false);
                }

                if (!FileKinds.ContentMatches(Name, head))
                {
                    IsRejected = true;
                    Discard();
                    return $"{Name} isn't a valid {System.IO.Path.GetExtension(Name).TrimStart('.').ToUpperInvariant()} file.";
                }

                IsComplete = true;
            }

            return null;
        }
        finally
        {
            _write.Release();
        }
    }

    internal void Discard()
    {
        try
        {
            var dir = System.IO.Path.GetDirectoryName(Path)!;
            if (Directory.Exists(dir))
            {
                Directory.Delete(dir, recursive: true);
            }
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}

public sealed record DownloadTicket(string Id, string UserKey, string SessionId, string Path, string FileName, DateTimeOffset ExpiresAt, bool DeleteAfter);

public sealed record PrintTicket(string Id, string UserKey, string SessionId, string PdfPath, string Title, DateTimeOffset ExpiresAt);
