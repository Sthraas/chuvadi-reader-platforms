using ChuvadiReader.Core.Reader;

namespace ChuvadiReader.Web.Hosting;

/// <summary>
/// Closing a connection's documents because its sign-in has ended (expiry, sign-out on another tab or at
/// Sangam). D-190 gives every close inside the Ui a question first when marks are unsaved (Save / Save as /
/// Discard / Cancel). This close is the one that cannot wait for an answer: the sign-in is already over, the
/// files are about to be deleted, and the warning before it has offered the downloads. So it is not asked;
/// asking would leave the documents open and their memory held. The guard is not put back: the tab is leaving.
/// </summary>
public static class SessionEndClose
{
    public static Task CloseDocumentsAsync(TabsService documents)
    {
        ArgumentNullException.ThrowIfNull(documents);
        documents.CloseGuard = null;
        return documents.CloseAllAsync();
    }
}
