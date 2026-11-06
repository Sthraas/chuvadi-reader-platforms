using global::Android.App;
using global::Android.Content;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Starts a system activity (document picker, share sheet) and awaits its result. MainActivity
/// forwards <c>OnActivityResult</c> here. One request code per call, so concurrent pickers never mix.
/// </summary>
public static class ActivityResults
{
    private static readonly Dictionary<int, TaskCompletionSource<(Result Code, Intent? Data)>> Pending = new();
    private static int _nextCode = 0x4300;

    public static Task<(Result Code, Intent? Data)> StartAsync(Intent intent)
    {
        var tcs = new TaskCompletionSource<(Result, Intent?)>(TaskCreationOptions.RunContinuationsAsynchronously);
        int code;
        lock (Pending)
        {
            code = _nextCode++;
            Pending[code] = tcs;
        }

        MainThread.BeginInvokeOnMainThread(() =>
        {
            var activity = Microsoft.Maui.ApplicationModel.Platform.CurrentActivity;
            if (activity is null)
            {
                Complete(code, Result.Canceled, null);
                return;
            }

            try
            {
                activity.StartActivityForResult(intent, code);
            }
            catch (ActivityNotFoundException)
            {
                Complete(code, Result.Canceled, null);
            }
        });

        return tcs.Task;
    }

    /// <summary>Called by MainActivity.OnActivityResult. Returns false for codes not started here.</summary>
    public static bool Complete(int requestCode, Result resultCode, Intent? data)
    {
        TaskCompletionSource<(Result, Intent?)>? tcs;
        lock (Pending)
        {
            if (!Pending.Remove(requestCode, out tcs))
            {
                return false;
            }
        }

        tcs.TrySetResult((resultCode, data));
        return true;
    }
}
