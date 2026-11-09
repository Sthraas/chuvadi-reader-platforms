# Proposal for Foundation: three findings from the corrected 36c (B-28), 10 Nov

Linux chat, on `platform/linux` with `fc6286a` merged. With B-28 fixed (a page counts as drawn only when its
page-sized svg is there), the stand-in drawing showed what 36c had been hiding. The stand-in is now 10,000 strokes a
sheet, sized to the real CAD file's memory (~1 GB at sheet 1, ~2 GB over 5 sheets); it takes 5.5–7 s a sheet here
(the real one ~1 s; B-27). At 120,000 strokes it took ~49 s a sheet.

## 1. A page that comes back into view after its render was cancelled is never drawn (shared Ui; diff below)
`PageLeft` cancels a waiting render, but the request stays in `_rendering` until that render notices. If the page
comes back meanwhile, `EnsureRendered` sees the entry and doesn't ask again; when the cancelled one clears, nothing
asks, and the page observer won't fire again while the page stays in view. Seen with 49 s sheets: sheets 2 and 5
never drew in 6 minutes. **Fix:** treat a cancelled entry as gone and ask again (the `finally` already removes only
its own entry). With it, sheet 2 drew in 48 s. Low priority at real weights (10,000-stroke sheets draw either way),
but a page that never draws is a hang to the person.

## 2. Moving to a page while the view fits the first drawing lands on another page (shared Ui; for Foundation)
When sheet 1 lands, the view fits it (43 %) and every page's height changes (A1 landscape: ~2,600 px → ~1,000 px).
A page-box jump or a scroll made just before that keeps its pixel offset, so it lands two sheets on (asked for sheet
2, shown sheet 4; screenshot in the Linux UI artifacts), and the page you asked for is never drawn because it never
comes into view. After a jump the page box also kept showing 1 while page 2 was in view. 36c now waits for the page
heights to hold before moving. Suggested: keep the current page anchored when the fit zoom changes the heights.

## 3. Memory after closing: the relief runs before the drawing is garbage (Core; for Foundation)
36b then 36c, 5 sheets drawn: 284–290 MB before, 2.1–2.3 GB with 5 sheets, 600–1,000 MB 130 s after closing (once
rising 859 → 990 MB at 30 s). With the test-only `gc` verb 80 s after closing: **.NET heap 678 MB → 5 MB** after
one aggressive collection, resident 634 → 401 MB. So nothing holds the closed document (your retention test is
right), but the relief (0.5 s after the close) and its 65 s follow-up run before that memory is garbage, and ~150 MB
stays outside the .NET heap even after a full collection (WebKit/GTK in the app's process, likely). 36c records
memory until this is settled; it needs (a) the relief to run once the closed tab's pages are released, and (b) a
target that allows what stays outside the heap (e.g. within 200 MB of the start) — the coordinator's call.

## The exact diff for 1 (on `platform/linux` HEAD, which carries `fc6286a`)
```diff
diff --git a/src/ChuvadiReader.Ui/Pages/Reader.razor b/src/ChuvadiReader.Ui/Pages/Reader.razor
index e826963..a685259 100644
--- a/src/ChuvadiReader.Ui/Pages/Reader.razor
+++ b/src/ChuvadiReader.Ui/Pages/Reader.razor
@@ -3481,11 +3481,14 @@
     private void EnsureRendered(int n)
     {
         var session = Tabs.Active?.Session;
-        if (session is null || session.TryGetRenderedSvg(n, out _) || _rendering.ContainsKey((session, n)))
+        if (session is null || session.TryGetRenderedSvg(n, out _)
+            || (_rendering.TryGetValue((session, n), out var asked) && !asked.IsCancellationRequested))
         {
             return;
         }
 
+        // A request cancelled when the page left (PageLeft) stays here until its render notices; the page came back
+        // meanwhile, so ask again now. Otherwise nothing asks once the old one clears, and the page stays undrawn.
         var cts = new CancellationTokenSource();
         _rendering[(session, n)] = cts;
         _ = RenderOneAsync(session, n, cts);
```
