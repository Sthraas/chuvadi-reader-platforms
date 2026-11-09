# Proposal for the Foundation's next combined patch: B-24 (reopened), B-25, owner-password printing; B-26

9 Nov 2026, Linux chat. The changes touch existing shared files (Core, Ui), so they go to the Foundation as one
exact diff (bottom of this file, against `platform/linux` at `c373a3d`, which carries `platform/foundation`
`c91a581`; updated 9 Nov evening, first sent against `e242d92`). Built with warnings as errors. The Linux UI steps that test them (`tools/linux/uitest.py` 34e, 34f and 31b,
plus `UITEST_ONLY` for re-checking a fix quickly) land on `platform/linux` with the rebase, so its CI stays green
until then.

| # | Bug | Change | Files |
|---|---|---|---|
| S1 | B-24 reopened: a stalled read blanks the Reader and blocks later opens | The Reader's tab-changed handler opened every new tab's file (`FlattenService.Probe`, as a PDF even for `.xlsx`) on the page's thread to set `_isXfaDoc`, which nothing reads (the XFA notice uses `tab.Session.Document.IsXfaForm`). `RefreshDocKind` and `_isXfaDoc` are removed; no behaviour changes | Ui/Pages/Reader.razor |
| S2 | B-25: viewer errors don't follow WT-10 | `ViewerBase.Describe` returns a plain sentence and the system's text: "This file is damaged or isn't an Excel workbook / a Word document / … Chuvadi can read.", WT-10's access sentence for I/O and permission errors, and a `DocumentViewException`'s own sentence with its inner error as the detail. `ViewerMessage` gets a `Detail` shown under a collapsed **Details**; all five viewers (Word, Excel, web page, Markdown, text) pass it. The access sentence is one constant, `TabsService.CantRead`, shared with the Reader | Core/Reader/TabsService.cs; Ui/Components/Viewers/ViewerBase.cs, ViewerMessage.razor(.css), DocxView, XlsxView, HtmlView, MarkdownView, TextView |
| S3 | Owner password doesn't print (found by Linux step 31b, D-139) | The Print card unlocks after an owner-password open, but `Reader.razor` opens `PrintCard` without the tab's password, so the print service opens the file with none: "Couldn't print: This PDF is encrypted and needs a password to open." Windows passes `request.Password` the same way. `Password="@tab.Password"` | Ui/Pages/Reader.razor |

## Results on Linux with the diff applied
- Tests (on `c91a581`): Reader 212/212, host kit 66/66, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16.
- B-24 (new UI step 34e, a named pipe as the stalled source): `slow.pdf` shows "Opening…" in 1.2 s and "Stop
  opening" at 10.3 s, and `five-pages.pdf` opens while it still waits; `slow.xlsx` 0.3 s / 10.1 s, the same.
  On `e242d92` the step fails (no "Opening…", the next open blocked).
- B-25 (new UI step 34f): `notzip.xlsx` → "This file couldn't be read as an Excel workbook." with Details
  (collapsed) "The file is not a valid xlsx workbook: End of Central Directory record could not be found";
  `notzip.docx` → "This file couldn't be read as a Word document." with the library's text under Details. On
  `e242d92` it fails (the technical text inline, no Details).
- S3 (UI step 31b): a no-printing file with both passwords. Opened with the user password the card stays
  locked; opened with the owner password it prints, and CUPS writes all 5 pages. Without S3 the step fails
  with the message above.
- Full UI pass with the diff and the three new steps: 118/118.

## B-26 (Excel number formats): a decision, not in the diff
D-136's tests make "every value as the file holds it" the rule (numbers raw, dates as `yyyy-mm-dd`); Excel's
display text would change what they assert. Measured with Chuvadi.Sheets 2.0.2 (`Cell.DisplayText`, en-IN):
11 of 17 non-text cells in the D-136 corpus and 5 of 7 in the Test chat's `exact.xlsx` display differently from
their value — `₹1,234.50` and `12.50%` (right), General `1.23457E+19` (digits hidden, as Excel shows them), and
**built-in date format 14 as `03-15-23`**: month first with en-IN, where Excel on an en-IN computer shows
`15-03-2023` (5 Nov 2024 would read `11-05-24`, i.e. 11 May). That last one is a library bug.

- **A. Excel's display text in the cells, the exact value on hover** (Excel's formula bar, in a tooltip), with
  the person's locale. Pros: money and percentages read as in Excel; nothing is lost (the value is one hover
  away). Cons: changes D-136's rule and its tests; General hides digits in the cell; **needs the library's date
  fix first**, or Indian dates read wrong.
- **B. Keep D-136: the raw value.** Pros: nothing hidden, no risk, no change. Cons: `12.50%` shows `0.125` and
  `₹1,234.50` shows `1234.5` — easy to misread.
- **C. Display text only for currency, percent and fixed-decimal formats; raw for General and dates.** Pros:
  avoids hidden digits and the date bug now. Cons: the app chooses formats itself (processing outside the
  library), and it's neither Excel nor the file.

**Recommendation: B now, then A once Chuvadi.Sheets renders format 14 (and the other locale-dependent built-in
date formats 15–17, 22) in the culture's own order.**

## Library asks (for Arun, via the library coordinator)
1. **Chuvadi.Sheets** (B-26): built-in date formats 14–17 and 22 follow the display culture's date order and
   year length (en-IN `15-03-2023`, as Excel), not en-US order with the culture's separators.
2. **B-27** (already in BUGS.md): large vector CAD PDF — 3–4 s to open, memory grows to 1.6 GB over 5 pages.

## The exact diff
Apply with `git apply` on `platform/linux` at `c373a3d` (`git diff cfaac4e..shared-fixes-9nov-b -- src` of the Linux
chat's local branch; `cfaac4e` has the same `src` tree as `c373a3d`).

```diff
diff --git a/src/ChuvadiReader.Core/Reader/TabsService.cs b/src/ChuvadiReader.Core/Reader/TabsService.cs
index 64776a9..3ef9161 100644
--- a/src/ChuvadiReader.Core/Reader/TabsService.cs
+++ b/src/ChuvadiReader.Core/Reader/TabsService.cs
@@ -447,6 +447,9 @@ public sealed class TabsService
     /// <summary>Shown when a document can't be opened for a reason other than damage, a password or access (WT-10).</summary>
     public const string OpenFailed = "This file is damaged or isn't a PDF Chuvadi can read.";
 
+    /// <summary>WT-10: a file that can't be read (permissions, in use, a missing drive), for the Reader and the viewers.</summary>
+    public const string CantRead = "Chuvadi couldn't read this file. It may be open in another app, or you may not have permission to read it.";
+
     private async Task EnsureLoadedAsync(ReaderTab tab, CancellationToken ct)
     {
         if (tab.IsLoaded || tab.IsLoading)
@@ -534,7 +537,7 @@ public sealed class TabsService
         catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
         {
             // WT-10: a plain sentence; the system's own text stays under Details.
-            tab.Error = "Chuvadi couldn't read this file. It may be open in another app, or you may not have permission to read it.";
+            tab.Error = CantRead;
             tab.ErrorDetail = ex.Message;
         }
         catch (Exception ex) when (ex is not OperationCanceledException)
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/DocxView.razor b/src/ChuvadiReader.Ui/Components/Viewers/DocxView.razor
index fd614d8..3e43cac 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/DocxView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/DocxView.razor
@@ -14,7 +14,7 @@
     }
     else if (_error is not null)
     {
-        <ViewerMessage IconName="warning" Error="true" Text="@_error" />
+        <ViewerMessage IconName="warning" Error="true" Text="@_error" Detail="@_errorDetail" />
     }
     else if (_view is null)
     {
@@ -59,6 +59,7 @@
     private List<Item> _items = new();
     private List<ViewerOutlineEntry> _outline = new();
     private string? _error;
+    private string? _errorDetail;
     private string? _loaded;
     private string? _password;      // in memory for this tab only
     private bool _locked, _busy;
@@ -98,7 +99,7 @@
     {
         var v = ++_version;
         _view = null;
-        _error = null;
+        _error = null; _errorDetail = null;
         _items = new();
         _outline = new();
         if (string.IsNullOrEmpty(Path)) { _locked = false; return; }
@@ -149,7 +150,7 @@
             else
             {
                 _locked = false;
-                _error = Describe(ex, "document");
+                (_error, _errorDetail) = Describe(ex, "a Word document");
             }
         }
         finally
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/HtmlView.razor b/src/ChuvadiReader.Ui/Components/Viewers/HtmlView.razor
index 27f0f92..446c96a 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/HtmlView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/HtmlView.razor
@@ -18,7 +18,7 @@
 <div class="htv" @ref="_root">
     @if (_error is not null)
     {
-        <ViewerMessage IconName="warning" Error="true" Text="@_error" />
+        <ViewerMessage IconName="warning" Error="true" Text="@_error" Detail="@_errorDetail" />
     }
     else if (_doc is null || _result is null)
     {
@@ -73,6 +73,7 @@
     private HtmlSanitizeResult? _result;
     private string _srcdoc = "";
     private string? _error;
+    private string? _errorDetail;
     private string? _loaded;
     private int _version;
     private bool _allowRemote;
@@ -125,7 +126,7 @@
         _doc = null;
         _result = null;
         _srcdoc = "";
-        _error = null;
+        _error = null; _errorDetail = null;
         if (string.IsNullOrEmpty(Path)) return;
         try
         {
@@ -143,7 +144,7 @@
         catch (Exception ex)
         {
             if (v != _version) return;
-            _error = Describe(ex, "page");
+            (_error, _errorDetail) = Describe(ex, "a web page");
             await ReportOutlineAsync(Array.Empty<ViewerOutlineEntry>());
             await ReportStatusAsync("HTML · couldn't open");
         }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/MarkdownView.razor b/src/ChuvadiReader.Ui/Components/Viewers/MarkdownView.razor
index ff489cc..5662f8f 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/MarkdownView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/MarkdownView.razor
@@ -9,7 +9,7 @@
 <div class="mdv">
     @if (_error is not null)
     {
-        <ViewerMessage IconName="warning" Error="true" Text="@_error" />
+        <ViewerMessage IconName="warning" Error="true" Text="@_error" Detail="@_errorDetail" />
     }
     else if (_doc is null || _render is null)
     {
@@ -41,6 +41,7 @@
     private TextDocument? _doc;
     private MarkdownRenderResult? _render;
     private string? _error;
+    private string? _errorDetail;
     private string? _loaded;
     private int _version;
     private bool _allowRemote;
@@ -94,7 +95,7 @@
         var v = ++_version;
         _doc = null;
         _render = null;
-        _error = null;
+        _error = null; _errorDetail = null;
         if (string.IsNullOrEmpty(Path)) return;
 
         try
@@ -117,7 +118,7 @@
         catch (Exception ex)
         {
             if (v != _version) return;
-            _error = Describe(ex, "file");
+            (_error, _errorDetail) = Describe(ex, "a Markdown file");
             await ReportOutlineAsync(Array.Empty<ViewerOutlineEntry>());
             await ReportStatusAsync("Markdown · couldn't open");
         }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/TextView.razor b/src/ChuvadiReader.Ui/Components/Viewers/TextView.razor
index d07b834..04caa83 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/TextView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/TextView.razor
@@ -8,7 +8,7 @@
 <div class="txv">
     @if (_error is not null)
     {
-        <ViewerMessage IconName="warning" Error="true" Text="@_error" />
+        <ViewerMessage IconName="warning" Error="true" Text="@_error" Detail="@_errorDetail" />
     }
     else if (_doc is null)
     {
@@ -25,6 +25,7 @@
 @code {
     private TextDocument? _doc;
     private string? _error;
+    private string? _errorDetail;
     private string? _loaded;
     private int _version;
     private SourceLines? _lines;
@@ -38,7 +39,7 @@
         _loaded = Path;
         var v = ++_version;
         _doc = null;
-        _error = null;
+        _error = null; _errorDetail = null;
         if (string.IsNullOrEmpty(Path)) return;
 
         try
@@ -53,7 +54,7 @@
         catch (Exception ex)
         {
             if (v != _version) return;
-            _error = Describe(ex, "file");
+            (_error, _errorDetail) = Describe(ex, "a text file");
             await ReportStatusAsync("Text · couldn't open");
         }
         await ReportOutlineAsync(Array.Empty<ViewerOutlineEntry>());
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/ViewerBase.cs b/src/ChuvadiReader.Ui/Components/Viewers/ViewerBase.cs
index 2563123..1ead271 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/ViewerBase.cs
+++ b/src/ChuvadiReader.Ui/Components/Viewers/ViewerBase.cs
@@ -135,11 +135,13 @@ public abstract class ViewerBase : ComponentBase, IAsyncDisposable
     protected Task ReportStatusAsync(string status) =>
         OnStatus.HasDelegate ? OnStatus.InvokeAsync(status) : Task.CompletedTask;
 
-    /// <summary>Friendly message for a load failure.</summary>
-    protected static string Describe(Exception ex, string kind) => ex switch
+    /// <summary>A load failure as WT-10 words it (B-25): a plain sentence, and the system's own text as the detail
+    /// shown under a collapsed Details. <paramref name="what"/> is "a Word document", "an Excel workbook", ….</summary>
+    protected static (string Text, string? Detail) Describe(Exception ex, string what) => ex switch
     {
-        DocumentViewException dve => dve.Message,
-        _ => $"Couldn't open this {kind}: {ex.Message}",
+        DocumentViewException dve => (dve.Message, dve.InnerException?.Message),
+        IOException or UnauthorizedAccessException => (Core.Reader.TabsService.CantRead, ex.Message),
+        _ => ($"This file is damaged or isn't {what} Chuvadi can read.", ex.Message),
     };
 
     protected virtual ValueTask DisposeCoreAsync() => ValueTask.CompletedTask;
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor b/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor
index 3e1b59a..d8afe2b 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor
@@ -1,7 +1,13 @@
 @* Centered state card for the viewers: loading, error, empty. *@
 <div class="vm @(Error ? "vm-err" : null)" role="@(Error ? "alert" : "status")">
     <Icon Name="@IconName" Size="16" />
-    <span>@Text</span>
+    <span class="vm-body">
+        <span>@Text</span>
+        @if (!string.IsNullOrEmpty(Detail))
+        {
+            <details class="vm-detail"><summary>Details</summary>@Detail</details>
+        }
+    </span>
     @ChildContent
 </div>
 
@@ -9,5 +15,7 @@
     [Parameter] public string IconName { get; set; } = "info";
     [Parameter] public string? Text { get; set; }
     [Parameter] public bool Error { get; set; }
+    /// <summary>The system's own text for an error (WT-10), under a collapsed Details.</summary>
+    [Parameter] public string? Detail { get; set; }
     [Parameter] public RenderFragment? ChildContent { get; set; }
 }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor.css b/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor.css
index 38b8267..018264f 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor.css
+++ b/src/ChuvadiReader.Ui/Components/Viewers/ViewerMessage.razor.css
@@ -5,3 +5,6 @@
 }
 .vm-err { color: var(--chvd-ink); border-color: var(--chvd-error); background: var(--chvd-surface-hi); }
 .vm-err ::deep .cv-icon { color: var(--chvd-error); }
+.vm-body { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
+.vm-detail { font-size: 12px; color: var(--chvd-ink-muted); overflow-wrap: anywhere; }
+.vm-detail summary { cursor: pointer; }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor b/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
index eac7c57..f5f544d 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
@@ -14,7 +14,7 @@
     }
     else if (_error is not null)
     {
-        <ViewerMessage IconName="warning" Error="true" Text="@_error" />
+        <ViewerMessage IconName="warning" Error="true" Text="@_error" Detail="@_errorDetail" />
     }
     else if (_wb is null)
     {
@@ -79,6 +79,7 @@
 @code {
     private WorkbookView? _wb;
     private string? _error;
+    private string? _errorDetail;
     private string? _loaded;
     private string? _password;      // in memory for this tab only
     private bool _locked, _busy;
@@ -120,7 +121,7 @@
     {
         var v = ++_version;
         _wb = null;
-        _error = null;
+        _error = null; _errorDetail = null;
         _index = new();
         _hits = new();
         _sheetHits = Array.Empty<int>();
@@ -174,7 +175,7 @@
             else
             {
                 _locked = false;
-                _error = Describe(ex, "workbook");
+                (_error, _errorDetail) = Describe(ex, "an Excel workbook");
             }
         }
         finally
diff --git a/src/ChuvadiReader.Ui/Pages/Reader.razor b/src/ChuvadiReader.Ui/Pages/Reader.razor
index 35d36f4..e73b8d8 100644
--- a/src/ChuvadiReader.Ui/Pages/Reader.razor
+++ b/src/ChuvadiReader.Ui/Pages/Reader.razor
@@ -794,7 +794,7 @@
                     <SignaturesCard Path="@tab.Path" Session="@tab.Session" CurrentPage="@tab.CurrentPageIndex" OnClose="CloseCard" OnMessage="OnCardMessage" OnReport="OnSigReport" />
                     break;
                 case "print":
-                    <PrintCard Path="@tab.Path" Session="@tab.Session" CurrentPage="@tab.CurrentPageIndex" OnClose="CloseCard" OnMessage="OnCardMessage" />
+                    <PrintCard Path="@tab.Path" Session="@tab.Session" Password="@tab.Password" CurrentPage="@tab.CurrentPageIndex" OnClose="CloseCard" OnMessage="OnCardMessage" />
                     break;
                 case "password":
                     <PasswordCard Path="@tab.Path" Session="@tab.Session" CurrentPage="@tab.CurrentPageIndex" OnClose="CloseCard" OnMessage="OnCardMessage" OnSaved="OnProtectedSaved" />
@@ -3134,7 +3134,6 @@
     }
 
     // ── Flatten to a static PDF (XFA form data / AcroForm fields / markup) ──────
-    private bool _isXfaDoc;
     private bool _flattening;
 
     // ── Recovery (opt-in): a page failed to decode, offer to open a repaired copy ──
@@ -3192,12 +3191,6 @@
     private async Task DocFlatten() { CloseDocMenu(); await FlattenNow(); }
     private void DocNav(string path) { CloseDocMenu(); Nav.NavigateTo(path); }
 
-    private void RefreshDocKind(string? path)
-    {
-        try { _isXfaDoc = !string.IsNullOrEmpty(path) && Flatten.Probe(path!).IsXfa; }
-        catch { _isXfaDoc = false; }
-    }
-
     private async Task FlattenNow()
     {
         var source = Tab?.Path;
@@ -3331,7 +3324,6 @@
                 _mkTagged = false; _mkTaggedPath = null;
                 if (_markup) _ = CheckTaggedAsync();
             }
-            RefreshDocKind(tab?.Path);
             OnActiveDocChanged(tab);
             ApplyShellModeForTab(tab);
         }
```
