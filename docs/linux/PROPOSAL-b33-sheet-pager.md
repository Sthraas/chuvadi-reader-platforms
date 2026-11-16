# Proposal to Foundation: B-33, the title bar's sheet arrows do nothing (shared Reader page)

> **Superseded, 16 Nov.** Foundation fixed B-33 in patch 31 (6c85f066, merged here from b895750): each viewer is
> keyed by its tab, and the reference is kept when the new tab is a viewer tab. That covers both causes below,
> the Linux-only one by another route. Checked on Linux: UI step 40 passes. **The diff below is not to be applied.**
> The page is kept for its account of why Linux alone showed the first cause.

16 Nov, Linux chat. For Linux Test's **B-33** (S2), found on `platform/linux` b0e5608 (patch 29) and still there on
patch 30 (4b704c8). The cause is in the shared Reader page, so nothing is changed on `platform/linux`: this is the
exact diff, with tests, for Foundation to take. It applies cleanly to `platform/foundation-pr` 4b704c8.

## What happens
In an Excel file the title bar's Previous / Next arrows do nothing, and typing a sheet number changes the number but
not the sheet. The sheet tabs under the grid work. The same goes for anything else that reaches the viewer from
outside it: the outline (`ScrollToAnchorAsync`) and "Copy all text" in Word, Excel, Markdown, HTML and text files.

## Why
`Reader` keeps the tab's viewer in `_viewer` (`@ref`), and `OnActiveDocChanged` sets it to null on a tab change. Blazor
hands a component's reference over once, when the component is made. The reference was lost for good two ways:

1. **The page is drawn in the middle of the tab change (this is the Linux part).** `SyncActive` calls
   `_ = LoadPageBgAsync(tab?.Path)` *before* `OnActiveDocChanged(tab)`. `LoadPageBgAsync` awaits the settings store and
   then `InvokeAsync(StateHasChanged)`. Linux's store answers at once, so that draw happens before `LoadPageBgAsync`
   returns: the new tab's `XlsxView` is made and its reference taken, and two lines later `OnActiveDocChanged` forgets
   it. On a host whose store answers later (a browser's), the draw comes after the reset and all is well, which is why
   the Web portal and Foundation's proof pass. Seen directly with a trace build:
   `OnTabsChanged → SyncActive → LoadPageBgAsync → Renderer.ProcessRenderQueue → XlsxView created`, then
   `OnActiveDocChanged … viewer was #35016340`, then every `CounterGoAsync` with `viewer=null`.
   (`CheckTaggedAsync` on the next lines can do the same in Mark.)
2. **A second file of the same kind reuses the first one's viewer (this part is every host).** The viewer has no
   `@key`, so going from one workbook's tab to another's keeps the same `XlsxView` and only changes its `Path`. Its
   reference is not handed over again, and the tab change has just forgotten it. With only fix 1 applied, Linux still
   showed: open `three-sheets.xlsx`, then `layout.xlsx`: arrows dead on the second, and on the first after going back.

## The fix
- `SyncActive`: the two calls that can draw run last, after the reset. Whether the tagged-PDF check runs is still
  decided where it was (from the mode before the reset), so nothing else changes.
- The viewer's host element gets `@key="tab.Id"`: one viewer per tab, made (and its reference taken) on every tab
  change. A viewer already reloaded its file when `Path` changed, so nothing that was kept before is lost.
- `PinchZoomTests` line 41 asserts that element's exact text, so it gains the `@key`.

## Checked on Linux (build of 4b704c8 with this diff)
| | before | with the diff |
|---|---|---|
| From Home, open a workbook: Next | stays on sheet 1 | sheet 2 |
| A PDF open, then the workbook: Next | stays on sheet 1 | sheet 2 |
| A second workbook: Next | stays on sheet 1 | sheet 2 |
| Back on the first workbook's tab: Next | stays on sheet 1 | sheet 2 |
| Previous; a typed sheet number; a tab press then Next | no change / number only | the sheet changes |

Unit tests with the diff: Reader 438 passed / 6 skipped, host kit 105 (3 new). Linux UI step 40 (`sheet_pager` in
`tools/linux/uitest.py`, real clicks and typing) fails without the diff and passes with it; it is in the tree but
only runs by name (`UITEST_ONLY=40`, or `UITEST_B33=1` for the whole pass) until the fix is merged.
The full Linux UI pass on the build with this diff is recorded in BUILD-LOG §60.

## Not chosen
- **Make Linux's settings store answer later** (a host-side delay): hides cause 1 on Linux only, leaves cause 2 on
  every host, and leaves the order in `SyncActive` a trap for the next host whose store is quick.
- **Only reorder `SyncActive`:** fixes the first workbook, not the second (measured above).

## The diff
```diff
diff --git a/src/ChuvadiReader.Ui/Pages/Reader.razor b/src/ChuvadiReader.Ui/Pages/Reader.razor
index e8c6cd13..478592e7 100644
--- a/src/ChuvadiReader.Ui/Pages/Reader.razor
+++ b/src/ChuvadiReader.Ui/Pages/Reader.razor
@@ -345,7 +345,9 @@
     }
     else if (viewOnly)
     {
-        <div class="rviewer" @ref="_viewerHost" data-zoom="@_textSize">
+        @* One viewer per tab (@key): a second file of the same kind used to reuse the first one's viewer, whose
+           reference the tab change had just forgotten, so the title bar's arrows did nothing on it (B-33). *@
+        <div class="rviewer" @ref="_viewerHost" data-zoom="@_textSize" @key="tab.Id">
             @switch (tab.Format)
             {
                 case DocumentFormat.Docx:
@@ -3533,15 +3535,20 @@
             _renderFailed = false;
             _recoverBannerDismissed = false;
             _recoverStatus = null;
-            if (tab?.Path != _pageBgPath) _ = LoadPageBgAsync(tab?.Path);
             bool otherFile = tab?.Path != _mkDocPath;
+            bool checkTagged = false;
             if (UseMarksOf(tab) || otherFile)
             {
                 _mkTagged = false; _mkTaggedPath = null;
-                if (_markup) _ = CheckTaggedAsync();
+                checkTagged = _markup;
             }
             OnActiveDocChanged(tab);
             ApplyShellModeForTab(tab);
+            // Last, after everything above is reset: these two can draw the page before they return (a host whose
+            // settings store answers at once, as Linux's does). Drawn earlier, the new tab's viewer was made and
+            // then forgotten by the reset above, and the title bar's sheet arrows did nothing (Linux Test B-33).
+            if (tab?.Path != _pageBgPath) _ = LoadPageBgAsync(tab?.Path);
+            if (checkTagged) _ = CheckTaggedAsync();
         }
         else if (pageCount != _shownPageCount || !ReferenceEquals(tab?.Session, _activeSession))
         {
diff --git a/tests/ChuvadiReader.Hosting.Tests/PinchZoomTests.cs b/tests/ChuvadiReader.Hosting.Tests/PinchZoomTests.cs
index d82f3c58..95f38d2d 100644
--- a/tests/ChuvadiReader.Hosting.Tests/PinchZoomTests.cs
+++ b/tests/ChuvadiReader.Hosting.Tests/PinchZoomTests.cs
@@ -38,7 +38,7 @@ public sealed class PinchZoomTests
     public void The_viewers_take_the_pinch_as_their_text_size()
     {
         var razor = Ui("Pages", "Reader.razor");
-        Assert.Contains(@"<div class=""rviewer"" @ref=""_viewerHost"" data-zoom=""@_textSize"">", razor);
+        Assert.Contains(@"<div class=""rviewer"" @ref=""_viewerHost"" data-zoom=""@_textSize"" @key=""tab.Id"">", razor);
         Assert.Contains(@"InvokeAsync<bool>(""viewerPinch"", _viewerHost, _ref)", razor);
         Assert.Contains("public void OnViewerPinch(int percent)", razor);
     }
diff --git a/tests/ChuvadiReader.Hosting.Tests/ViewerReferenceTests.cs b/tests/ChuvadiReader.Hosting.Tests/ViewerReferenceTests.cs
new file mode 100644
index 00000000..a2fd12c9
--- /dev/null
+++ b/tests/ChuvadiReader.Hosting.Tests/ViewerReferenceTests.cs
@@ -0,0 +1,44 @@
+using Xunit;
+
+namespace ChuvadiReader.Hosting.Tests;
+
+/// <summary>
+/// Linux Test B-33: the title bar's sheet arrows and number box did nothing in an Excel file. The Reader page
+/// keeps a reference to the tab's viewer and forgets it when the tab changes. Two ways the reference was lost
+/// for good: (1) the tab change drew the page before it forgot (a settings store that answers at once, as
+/// Linux's does, lets <c>LoadPageBgAsync</c> draw before it returns), so the new viewer was made and then
+/// forgotten; (2) a second file of the same kind reused the first one's viewer, which is never handed over again.
+/// The live proof is Linux's UI step 40 (tools/linux/uitest.py).
+/// </summary>
+public sealed class ViewerReferenceTests
+{
+    private static string Ui(params string[] path) =>
+        File.ReadAllText(Path.Combine([AppContext.BaseDirectory, "UiSources", .. path]));
+
+    private static string SyncActive()
+    {
+        var razor = Ui("Pages", "Reader.razor");
+        int from = razor.IndexOf("private void SyncActive()", StringComparison.Ordinal);
+        int to = razor.IndexOf("else if (pageCount != _shownPageCount", from, StringComparison.Ordinal);
+        Assert.True(from >= 0 && to > from, "SyncActive's tab-change branch was not found");
+        return razor[from..to];
+    }
+
+    [Theory]
+    [InlineData("_ = LoadPageBgAsync(tab?.Path);")]
+    [InlineData("_ = CheckTaggedAsync();")]
+    public void On_a_tab_change_nothing_that_can_draw_runs_before_the_reset(string canDraw)
+    {
+        var body = SyncActive();
+        int reset = body.IndexOf("OnActiveDocChanged(tab);", StringComparison.Ordinal);
+        int call = body.IndexOf(canDraw, StringComparison.Ordinal);
+        Assert.True(reset >= 0, "the reset is gone from SyncActive");
+        Assert.True(call > reset, $"'{canDraw}' runs before the reset: it can draw the new tab's viewer, which the reset then forgets");
+    }
+
+    [Fact]
+    public void Each_tab_has_its_own_viewer()
+    {
+        Assert.Contains(@"<div class=""rviewer"" @ref=""_viewerHost"" data-zoom=""@_textSize"" @key=""tab.Id"">", Ui("Pages", "Reader.razor"));
+    }
+}
```
