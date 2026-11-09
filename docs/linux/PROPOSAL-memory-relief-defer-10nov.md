# Proposal for Foundation: a second heavy close within 30 s still gives its memory back (36c, 10 Nov)

Linux chat. With the sixteenth patch, part 3 (`3759b6f`), closing one drawing gives its memory back every time (36c
cold, 4 of 4). In the full UI pass it failed (341 MB before opening, 671 MB with 5 sheets, 680 MB after closing):
step 36b closes a CAD tab just before 36c. `MemoryRelief.Request` drops a request that comes within `MinGap`
(30 s) of the last relief, or while one is running (the 65 s follow-up keeps it running), so the second close in a
row never gives its memory back. Measured on `a203a62` (= `3759b6f` merged): 36b then 36c, still 589 MB 40 s
after closing.

**Change:** a close inside the gap waits for it instead of being dropped. One relief at most waits at a time, and
closes while it waits share it; collections stay at least `MinGap` apart. `MinGap` becomes settable for tests
(as `Settle` and `FollowUp` are); `ResetForTests` restores it. New test
`A_second_heavy_close_inside_the_gap_waits_for_it_instead_of_being_dropped`. Linux's 36c waits up to 40 s
(the 30 s gap plus settling).

**Results:** Reader 231/231 three times (one unexplained failure in seven runs of the memory and render tests,
not repeated in the next six); Linux 36b then 36c, 3 of 3: 284–285 MB before, 560–586 MB with 5 sheets, 290–292 MB
18 s after closing; full UI pass with 36c as an assertion (warm): RESULT.

**Options.** A. Defer (this diff). Pros: every heavy close gives memory back, at most 30 s late; the spacing that
protects a shared server stays. Cons: a waiting task per gap. B. Drop as now. Pros: no change. Cons: the second
drawing closed within a minute keeps its memory until the app closes. C. Drop the gap on desktop hosts. Pros:
memory back at once. Cons: a host-specific rule for one constant. **Recommendation: A.**

## The exact diff (on `platform/linux` `a203a62`)
```diff
diff --git a/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs b/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
index c953ae3..20ba461 100644
--- a/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
+++ b/src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs
@@ -729,7 +729,7 @@ internal static class MemoryRelief
 
     /// <summary>A document whose drawing allocated this much is heavy too, whatever its pages keep.</summary>
     internal const long HeavyDrawingBytes = 64L * 1024 * 1024;
-    internal static readonly TimeSpan MinGap = TimeSpan.FromSeconds(30);
+    internal static TimeSpan MinGap { get; set; } = TimeSpan.FromSeconds(30);
     internal static TimeSpan Settle { get; set; } = TimeSpan.FromMilliseconds(500);
 
     /// <summary>
@@ -741,41 +741,51 @@ internal static class MemoryRelief
     internal static TimeSpan FollowUp { get; set; } = TimeSpan.FromSeconds(65);
 
     private static long _lastTicks = long.MinValue / 2;
-    private static int _running;
+    private static int _queued;
 
     /// <summary>Tests only: the last relief started, if any.</summary>
     internal static Task? Last { get; private set; }
 
+    /// <summary>
+    /// Asks for one relief after a heavy close. A close that comes within <see cref="MinGap"/> of the last relief (or
+    /// while one waits) is not dropped: it waits for the gap, so closing two drawings in a row gives back both
+    /// (Linux 36b then 36c). Closes while a relief is already waiting share it.
+    /// </summary>
     internal static void Request()
     {
-        var now = Environment.TickCount64;
-        var last = Interlocked.Read(ref _lastTicks);
-        if (now - last < (long)MinGap.TotalMilliseconds || Interlocked.CompareExchange(ref _running, 1, 0) != 0)
+        if (Interlocked.CompareExchange(ref _queued, 1, 0) != 0)
         {
-            return;
+            return; // the relief already waiting covers this close too
         }
 
-        Interlocked.Exchange(ref _lastTicks, now);
         Last = Task.Run(async () =>
         {
             try
             {
-                await Task.Delay(Settle).ConfigureAwait(false); // the Ui lets go of the closed tab's pages first
-                GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
-                if (FollowUp > TimeSpan.Zero)
-                {
-                    await Task.Delay(FollowUp).ConfigureAwait(false);
-                    GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true); // the pool drops buffers idle for a minute
-                    GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
-                }
+                var sinceLast = Environment.TickCount64 - Interlocked.Read(ref _lastTicks);
+                var gap = TimeSpan.FromMilliseconds(Math.Max(0, (long)MinGap.TotalMilliseconds - sinceLast));
+                await Task.Delay(gap + Settle).ConfigureAwait(false); // the gap, then the Ui lets go of the pages
             }
             finally
             {
-                Volatile.Write(ref _running, 0);
+                Volatile.Write(ref _queued, 0); // a close from here on asks for the next relief
+            }
+
+            Interlocked.Exchange(ref _lastTicks, Environment.TickCount64);
+            GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
+            if (FollowUp > TimeSpan.Zero)
+            {
+                await Task.Delay(FollowUp).ConfigureAwait(false);
+                GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true); // the pool drops buffers idle for a minute
+                GC.Collect(GC.MaxGeneration, GCCollectionMode.Aggressive, blocking: true, compacting: true);
             }
         });
     }
 
     /// <summary>Tests only: lets the next request run at once.</summary>
-    internal static void ResetForTests() => Interlocked.Exchange(ref _lastTicks, long.MinValue / 2);
+    internal static void ResetForTests()
+    {
+        Interlocked.Exchange(ref _lastTicks, long.MinValue / 2);
+        MinGap = TimeSpan.FromSeconds(30);
+    }
 }
diff --git a/tests/ChuvadiReader.Tests/MemoryAfterCloseTests.cs b/tests/ChuvadiReader.Tests/MemoryAfterCloseTests.cs
index 2f2fece..4342644 100644
--- a/tests/ChuvadiReader.Tests/MemoryAfterCloseTests.cs
+++ b/tests/ChuvadiReader.Tests/MemoryAfterCloseTests.cs
@@ -79,6 +79,34 @@ public sealed class MemoryAfterCloseTests
         Assert.True(after.Committed - before.Committed < 64 * mb, $"memory kept by the runtime after close: {before.Committed / mb} → {after.Committed / mb} MB");
     }
 
+    [Fact]
+    public async Task A_second_heavy_close_inside_the_gap_waits_for_it_instead_of_being_dropped()
+    {
+        // Linux 36b then 36c: two drawings closed within the gap. The second must still give its memory back.
+        MemoryRelief.ResetForTests();
+        MemoryRelief.MinGap = TimeSpan.FromMilliseconds(400);
+        try
+        {
+            MemoryRelief.Request();
+            var first = MemoryRelief.Last!;
+            await first.WaitAsync(TimeSpan.FromSeconds(10));
+            var firstDone = System.Diagnostics.Stopwatch.StartNew();
+
+            MemoryRelief.Request();                      // inside the gap: before this change it was dropped
+            var second = MemoryRelief.Last!;
+            Assert.NotSame(first, second);
+            MemoryRelief.Request();                      // while the second waits: it shares that relief
+            Assert.Same(second, MemoryRelief.Last);
+
+            await second.WaitAsync(TimeSpan.FromSeconds(10));
+            Assert.True(firstDone.ElapsedMilliseconds >= 300, $"ran {firstDone.ElapsedMilliseconds} ms after the first: the gap wasn't kept");
+        }
+        finally
+        {
+            MemoryRelief.ResetForTests();
+        }
+    }
+
     [Fact]
     public async Task A_light_document_never_asks_for_a_collection()
     {
```
