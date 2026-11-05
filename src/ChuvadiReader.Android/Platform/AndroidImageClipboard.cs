using ChuvadiReader.Core.Reader;
using global::Android.Content;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Copies a PNG (e.g. a page snapshot) to the Android clipboard.
///
/// Android's clipboard holds images by content URI, not bytes, so the PNG is written to a
/// private clip folder and offered through the app's own read-only <see cref="ClipProvider"/>.
/// Only the latest clip is kept.
/// </summary>
public sealed class AndroidImageClipboard : IImageClipboard
{
    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return Task.CompletedTask;
        }

        Directory.CreateDirectory(ClipProvider.ClipFolder);
        foreach (var old in Directory.EnumerateFiles(ClipProvider.ClipFolder))
        {
            File.Delete(old);
        }

        var name = $"snapshot-{DateTime.Now:yyyyMMdd-HHmmss}.png";
        File.WriteAllBytes(Path.Combine(ClipProvider.ClipFolder, name), pngBytes);

        return MainThread.InvokeOnMainThreadAsync(() =>
        {
            var context = global::Android.App.Application.Context;
            var uri = AUri.Parse($"content://{context.PackageName}.clip/{name}");
            var clipboard = (ClipboardManager?)context.GetSystemService(Context.ClipboardService);
            if (clipboard is null || context.ContentResolver is null || uri is null)
            {
                return;
            }

            clipboard.PrimaryClip = ClipData.NewUri(context.ContentResolver, "Chuvadi snapshot", uri);
        });
    }
}
