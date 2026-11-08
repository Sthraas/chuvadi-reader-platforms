using Foundation;

namespace ChuvadiReader.Mac;

/// <summary>
/// MAUI's scene delegate, named in Info.plist's scene manifest (Mac Test M-02). With it, macOS hands
/// files opened with Chuvadi to the app as scene events — at launch (connection options) and while
/// it runs (open URL contexts) — which MauiProgram routes to the shared IncomingFiles.
/// </summary>
[Register("SceneDelegate")]
public sealed class SceneDelegate : MauiUISceneDelegate
{
}
