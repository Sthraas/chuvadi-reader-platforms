# Proposal for Foundation: closing a mid-sized drawing gives its memory back too (36c, 10 Nov)

Linux chat. The sixteenth patch, part 2 (`4f67a4c`) gives memory back after a heavy document closes, but only when
its pages held ≥ 64 MB **or its drawing allocated ≥ 256 MB**. The Linux stand-in drawing (5 A1 sheets, ~120,000
strokes each) allocates close to that line, so it crosses it in some runs and not others:

| Cold runs of UI step 36c on `379c26c` (= `4f67a4c` merged) | Before | With 5 sheets | After closing |
|---|---|---|---|
| passed (5 of 7) | 257–259 MB | 517–588 MB | 272–275 MB |
| failed (2 of 7) | 257–258 MB | 424–486 MB | 446–523 MB, still there 15 s later |

**Change:** `MemoryRelief.HeavyDrawingBytes` 256 MB → 64 MB, the same line as the pages. One collection after
closing a document that allocated 64 MB (74 ms measured by Foundation; still at most once per 30 s).

**Results with it:** Reader 229/229; 36c cold 6 of 6 (peaks 449–536 MB → 270–277 MB after closing); full UI pass
with 36c as an assertion (warm): RESULT. 36c becomes an assertion on `platform/linux` when this lands.

**Options.** A. 64 MB (this diff). Pros: a drawing of any real size gives memory back; one constant. Cons: more
documents qualify for the 74 ms collection (still once per 30 s at most). B. Keep 256 MB. Pros: no change.
Cons: a 150–250 MB drawing keeps that memory until the app closes. **Recommendation: A.**

Also seen (not changed): `Request` drops a close that comes within 30 s of the last collection, or while one runs
(the 65 s follow-up keeps it running), so closing two drawings in a row gives back only the first. Deferring the
second request instead of dropping it would cover that; say if you want it in the same diff.

## The exact diff (on `platform/linux` `379c26c`)
```diff
diff --git a/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs b/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
index 4b97eaf..c953ae3 100644
--- a/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
+++ b/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
@@ -728,7 +728,7 @@ internal static class MemoryRelief
     internal const long HeavyBytes = 64L * 1024 * 1024;
 
     /// <summary>A document whose drawing allocated this much is heavy too, whatever its pages keep.</summary>
-    internal const long HeavyDrawingBytes = 256L * 1024 * 1024;
+    internal const long HeavyDrawingBytes = 64L * 1024 * 1024;
     internal static readonly TimeSpan MinGap = TimeSpan.FromSeconds(30);
     internal static TimeSpan Settle { get; set; } = TimeSpan.FromMilliseconds(500);
 
```
