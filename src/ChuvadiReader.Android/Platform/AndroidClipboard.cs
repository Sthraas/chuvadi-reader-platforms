using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using global::Android.Content;
using AUri = global::Android.Net.Uri;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Text and image clipboard (Foundation's IClipboard, plus Core's IImageClipboard for today's Ui).
/// Android holds images by content URI, so the PNG is written to a private folder and offered through
/// the app's own read-only <see cref="SharedFileProvider"/>. Only the latest clip is kept.
/// </summary>
public sealed class AndroidClipboard : IClipboard, IImageClipboard
{
    public bool CanCopyText => true;

    public bool CanCopyImage => true;

    public Task SetTextAsync(string text, CancellationToken ct = default)
        => MainThread.InvokeOnMainThreadAsync(() =>
        {
            if (Manager is { } clipboard)
            {
                clipboard.PrimaryClip = ClipData.NewPlainText("Chuvadi", text ?? string.Empty);
            }
        });

    public Task SetImageAsync(byte[] pngBytes, CancellationToken ct = default)
    {
        if (pngBytes is null || pngBytes.Length == 0)
        {
            return Task.CompletedTask;
        }

        var uri = SharedFileProvider.Publish(SharedFileProvider.ClipArea, $"snapshot-{DateTime.Now:yyyyMMdd-HHmmss}.png",
            target => File.WriteAllBytes(target, pngBytes));

        return MainThread.InvokeOnMainThreadAsync(() =>
        {
            var resolver = global::Android.App.Application.Context.ContentResolver;
            if (Manager is { } clipboard && resolver is not null)
            {
                clipboard.PrimaryClip = ClipData.NewUri(resolver, "Chuvadi snapshot", uri);
            }
        });
    }

    private static ClipboardManager? Manager
        => (ClipboardManager?)global::Android.App.Application.Context.GetSystemService(Context.ClipboardService);
}

/// <summary>Android share sheet for a document or image Chuvadi has on disk.</summary>
public sealed class AndroidShare : IShare
{
    public bool IsAvailable => true;

    public Task<bool> ShareFileAsync(string localPath, string title, CancellationToken ct = default)
    {
        if (!File.Exists(localPath))
        {
            return Task.FromResult(false);
        }

        var name = Path.GetFileName(localPath);
        AUri uri = SharedFileProvider.Publish(SharedFileProvider.ShareArea, name, target => File.Copy(localPath, target, overwrite: true));

        return MainThread.InvokeOnMainThreadAsync(() =>
        {
            var send = new Intent(Intent.ActionSend);
            send.SetType(SharedFileProvider.MimeFor(name));
            send.PutExtra(Intent.ExtraStream, uri);
            send.PutExtra(Intent.ExtraTitle, title);
            send.AddFlags(ActivityFlags.GrantReadUriPermission);

            var chooser = Intent.CreateChooser(send, title);
            var activity = Microsoft.Maui.ApplicationModel.Platform.CurrentActivity;
            if (chooser is null || activity is null)
            {
                return false;
            }

            activity.StartActivity(chooser);
            return true;
        });
    }
}
