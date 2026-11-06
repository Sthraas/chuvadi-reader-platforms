# Proposal for the Foundation's combined patch: Print card errors in the error style

Approved by the coordinator (7 Nov). One existing file: `src/ChuvadiReader.Ui/Components/Cards/PrintCard.razor`.

**Bug.** The Print card hands every result message to `OnMessage`; the Reader page's `OnCardMessage` then
guesses the toast style from the wording (starts with "Couldn't" / "Could not" / "Error", or contains
"failed"). Print failures worded otherwise show with the success tick — on every platform: "The printer
didn't take the job: …" (Linux), "This file's permissions don't allow printing." (D-66, every platform once
the Foundation's L-8 fix lands), and any host's "unavailable" message.

**Fix.** The card already knows the outcome, so it passes it: results go to `ShellService.Notify` (what
`OnCardMessage` calls) with `isError` = outcome is `Failed` or `Unavailable`. No API change, no change to
other cards or to the page; the `OnMessage` parameter stays so `Reader.razor` needs no edit.

**Checked on Linux** (built with the diff, warnings as errors): the no-printing refusal now shows the error
toast (`msg err`), before/after in `screenshots/print-refusal-toast-before-after.png`; a successful print
keeps the success toast (checked: `msg ok`, "Sent 5 pages to the printer"). Not committed on `platform/linux`
(existing file): the Linux branch stays without it until the combined patch lands.

```diff
diff --git a/src/ChuvadiReader.Ui/Components/Cards/PrintCard.razor b/src/ChuvadiReader.Ui/Components/Cards/PrintCard.razor
index d64e8f8..de16ac6 100644
--- a/src/ChuvadiReader.Ui/Components/Cards/PrintCard.razor
+++ b/src/ChuvadiReader.Ui/Components/Cards/PrintCard.razor
@@ -1,5 +1,6 @@
 @namespace ChuvadiReader.Ui.Components.Cards
 @inject IServiceProvider Services
+@inject ShellService Shell
 @implements IDisposable
 @*
     Print: page range (All / Current / Custom "1-3, 5"), copies, fit to page → IPrintService,
@@ -84,7 +85,8 @@
 
     [Parameter] public EventCallback OnClose { get; set; }
 
-    /// <summary>Success/error toasts.</summary>
+    /// <summary>Kept for the page's markup; print results go to <see cref="ShellService.Notify"/>
+    /// with their outcome (error style for Failed / Unavailable).</summary>
     [Parameter] public EventCallback<string> OnMessage { get; set; }
 
     private IPrintService? _print;
@@ -164,12 +166,13 @@
 
             if (result.Outcome != PrintOutcome.Cancelled && !string.IsNullOrEmpty(result.Message))
             {
-                await OnMessage.InvokeAsync(result.Message!);
+                // The outcome decides the toast's style, not the wording of the message.
+                Shell.Notify(result.Message!, isError: result.Outcome is PrintOutcome.Failed or PrintOutcome.Unavailable);
             }
         }
         catch (Exception ex)
         {
-            await OnMessage.InvokeAsync("Couldn't print: " + ex.Message);
+            Shell.Notify("Couldn't print: " + ex.Message, isError: true);
         }
         finally
         {
```
