# Proposal for the Foundation's next combined patch: shared fixes from the Linux Test chat, and D-101

8 Nov 2026, Linux chat. Every change below touches an existing shared file (Platform, Core, Ui, nuget.config),
so it goes to the Foundation as one exact diff (bottom of this file, against `platform/linux` at `ffb2823`).
Built with warnings as errors; tested on Linux with the diff applied (results per item). The Linux parts that
depend on the contract (D-101) are in the same diff and land on `platform/linux` with the rebase.

| # | Bug | Change | Files |
|---|---|---|---|
| S1 | D-101 live button layout | `IPlatformInfo.ChromeChanged` (default: no-op, so no other host changes); `MainLayout` redraws on it; Linux raises it when GTK's `gtk-decoration-layout` changes | Platform/PlatformInfo.cs, Ui/Layout/MainLayout.razor; Linux: chvdhost.c, Native.cs, GtkHost.cs, LinuxDesktop.cs, UiTestDriver.cs |
| S2 | B-07 PDF password | `ReaderTab.NeedsPassword/Password/PasswordError`, `TabsService.UnlockAsync`; the Reader shows the existing `UnlockCard` (as Word/Excel); password in memory for that tab only | Core/Reader/TabsService.cs, Ui/Pages/Reader.razor, Ui/Components/Viewers/UnlockCard.razor |
| S3 | B-11 damaged PDF | `PdfParseException`/`PdfCorruptionException` → the handout's "This PDF is damaged" state (States & Feedback 8e) with "Try to repair (new copy)" (the existing `TryRecovery`) and "Show in folder"; the parser text under Details | Core/Reader/TabsService.cs, Ui/Pages/Reader.razor, Reader.razor.css |
| S4 | B-08 zip bomb (app side) | `OfficePackageGuard`: reads the zip directory only and refuses a part over 256 MB, a package over 1 GB, or a >16 MB part compressed over 200:1, before the library inflates it; `ViewErrorReason.TooLarge` | Core/Documents/OfficePackageGuard.cs (new), DocumentViewException.cs, DocxViewService.cs, XlsxViewService.cs |
| S5 | B-09, B-10 huge sheet | The Excel grid draws only the rows on screen (`<Virtualize>`; frozen rows outside it, so they stay sticky); find-in-sheet scrolls to the hit's row first | Ui/Components/Viewers/XlsxView.razor, wwwroot/js/viewers.js |
| S6 | B-03 dependency confusion | `packageSourceMapping`: `Chuvadi.*` and `LiPicons.*` only from the local feed | nuget.config |
| S8 | B-19 left-hand buttons misaligned | With the buttons on the left (`close,minimize,maximize:`), they sit inside `.tb-brandbox` next to the brand mark, so the brand stays on the top bar's centre line; `.tb-brandbox { gap: 10px; min-width: max-content; }` | Ui/Layout/MainLayout.razor, shell.css |
| S9 | B-23 Tab order | The page's "send" hover button (`rpage-send`) is out of the Tab order (`tabindex="-1"`; the same action is in the page menu), so Tab goes from the toolbar to the page, not through every page's hidden button | Ui/Pages/Reader.razor |
| S7 | B-02 font licences (shared) | The Ui ships the full OFL 1.1 text next to its fonts: `fonts/google/OFL.txt` (each family's holder from the font files) and `lipi-sans/OFL.txt` (LiPi's `LICENSE.txt` is an abridged text without the preamble and definitions; left as is) | Ui/wwwroot/fonts/google/OFL.txt, Ui/wwwroot/lipi-sans/OFL.txt (new) |

## Results on Linux with the diff applied
- Tests (rebased on ffb2823): Reader 179/179 (+8 new: `PdfPasswordTabTests` 3, `DamagedPdfTabTests` 2, `OfficePackageGuardTests` 3),
  host kit 54/54, Linux 25/25, Web Ui 33/33, Mobile Ui 16/16.
- The Test chat's files in the real app:
  - B-07 `aes256.pdf`: password card; a wrong password says "That password doesn't open this file."; the right
    one opens all 5 pages.
  - B-11 `badxref.pdf`: "This PDF is damaged", parser text only under Details; "Try to repair (new copy)"
    rebuilds it (7 objects) and opens "badxref (recovered).pdf".
  - B-08 `bomb.docx` (1 MB, unpacks to 1 GB): refused in 1.6 s, "This Word document is too large to open: its
    contents unpack to more than 1,024 MB. It may be damaged."; memory stays at 303 MB.
  - B-09 `far-cell.xlsx` (cell at XFD1048576): grid in 2.6 s, 26,112 cells drawn instead of 1.28 million;
    memory 372 MB (Test chat: 1.7 GB and "Opening…" for 185 s+).
  - B-10: a PDF opened right after it opens in 0.3 s.
- Full UI pass on the shared build: see the result line at the end of this file.

## Options
**S1 (D-101), how the change reaches the Ui.** A. An event on `IPlatformInfo` with a no-op default (built).
Pros: one member; every other host compiles and behaves unchanged. Cons: a host must remember to raise it.
B. Make `Chrome` an observable object. Pros: one place for every chrome change. Cons: a wider contract change for
one platform's need. **Recommendation: A.**

**S5 (B-09/B-10), how much to draw.** A. Virtualise rows (built). Pros: any sheet size; dense 5,000 × 256 sheets
no longer choke the web view either. Cons: the scroll bar is estimated from a 22 px row (rows with wrapped text
are taller, so it corrects itself while scrolling). B. A smaller cell cap. Pros: a one-line change. Cons: a
wide real sheet would show only a few hundred rows. **Recommendation: A.**

**S3 (B-11) wording.** The handout's description is written for one damage kind ("The file ends early…"). Built:
"Chuvadi couldn't read this file, maybe because a download or copy didn't finish. Chuvadi can try to rebuild
it as a new copy." — the handout's title and actions unchanged. The handout also draws the icon in a tinted red
circle with "Try to repair" as the primary button; the built state uses the Reader's existing empty-state
style. Foundation can match the handout's styling exactly when applying.

**B-22, a designed keyboard-focus style (not in the diff; a design decision).** Today each engine draws its own
focus ring (GTK blue on Linux, Chromium's on Windows), and only `.tb-pg-box` and `.ph-pager-in` define one.
A. One rule in tokens.css: `:focus-visible { outline: 2px solid var(--chvd-binding); outline-offset: 2px; }`.
Pros: the same ring on every platform, in the theme's colour; keyboard-only (`:focus-visible`), so mouse clicks
draw nothing. Cons: a visible design change the handout doesn't specify; a few tight controls (tabs, pager)
may need their own offset. B. Leave the engines' default. Pros: no change. Cons: focus looks different per
platform and clashes with the Palm and Indigo themes. **Recommendation: A, once the designer confirms the colour
and offset** — the design is final, so it isn't in this diff.

**B-18 routing.** The rail at rest (62 px icons, labels on hover) changes Windows too, so it belongs to the Reader
chat's desktop revamp rather than this patch.

**B-16 in the kit (optional).** Linux no longer needs a shared change (its own `ResilientAppStorage` wraps the
kit's `FileAppStorage`). The same wrapper in `ChuvadiReader.Hosting.Desktop` would cover Windows and Mac too
(a locked-down or full `%AppData%`). Pros: every desktop host starts with an unwritable settings folder. Cons:
one more kit type. Recommendation: adopt it in the kit when convenient; Linux then uses the kit's.

## Library asks (for Arun, via the library coordinator)
1. **Chuvadi.Docs / Chuvadi.Sheets input limits** (B-08): a package that lies about its sizes still reaches the
   library; limits on part size and inflation ratio there, as chuvadi-pdf has.
2. **Chuvadi.Sheets** (B-09): don't build anything to the sheet's declared extent; a stray far cell shouldn't cost
   memory.
3. **chuvadi-pdf** (B-11): rebuild the cross-reference table on open when `startxref` is wrong (the repairer
   already can; doing it on open saves the person a step).
4. **Cancellation** in `Document.Load` / `Workbook.Load` (B-08/B-10): the app can then stop a long open instead
   of only leaving it.
5. **Chuvadi.Print.Ipp** (B-14, also L-5 (3)): an "automatic" orientation that leaves `orientation-requested` out
   in document mode. Linux removes it from the ticket today (`CupsPrintService`); with the library option that
   step goes away.
6. **Chuvadi.Print.Ipp `CupsQueues`** (B-20): it ignores `CUPS_SERVER` and `~/.cups/client.conf`, so a computer
   that prints through a remote CUPS server shows "no printers". Read them as `lpstat` does.
7. **chuvadi-pdf owner password** (D-102 item 3, passed to Arun): say whether a file opened with the owner
   password, so `PrintPermission` can allow printing then. Until it lands, Linux keeps refusing.

## The exact diff
Apply with `git apply` on `platform/linux` at `ffb2823` (`git diff ffb2823..shared` of the Linux chat's local branch).

```diff
diff --git a/nuget.config b/nuget.config
index 9a4d36b..e2cf4d7 100644
--- a/nuget.config
+++ b/nuget.config
@@ -5,4 +5,15 @@
     <!-- The chuvadi-pdf distribution packages live here as .nupkg files. -->
     <add key="chuvadi-local" value="./localpackages" />
   </packageSources>
+  <!-- Arun's own packages come only from the local feed (ci/packages), never from nuget.org, so a package
+       published there under the same name can't be taken instead (dependency confusion, B-03). -->
+  <packageSourceMapping>
+    <packageSource key="chuvadi-local">
+      <package pattern="Chuvadi.*" />
+      <package pattern="LiPicons.*" />
+    </packageSource>
+    <packageSource key="nuget.org">
+      <package pattern="*" />
+    </packageSource>
+  </packageSourceMapping>
 </configuration>
diff --git a/src/ChuvadiReader.Core/Documents/DocumentViewException.cs b/src/ChuvadiReader.Core/Documents/DocumentViewException.cs
index 0435d2c..47ed962 100644
--- a/src/ChuvadiReader.Core/Documents/DocumentViewException.cs
+++ b/src/ChuvadiReader.Core/Documents/DocumentViewException.cs
@@ -1,6 +1,6 @@
 namespace ChuvadiReader.Core.Documents;
 
-public enum ViewErrorReason { PasswordProtected, BadFormat, Other }
+public enum ViewErrorReason { PasswordProtected, BadFormat, Other, TooLarge }
 
 /// <summary>Raised by the Docs/Sheets view-services so the Ui can react without
 /// referencing the underlying document libraries.</summary>
diff --git a/src/ChuvadiReader.Core/Documents/DocxViewService.cs b/src/ChuvadiReader.Core/Documents/DocxViewService.cs
index d3ca444..f7639f2 100644
--- a/src/ChuvadiReader.Core/Documents/DocxViewService.cs
+++ b/src/ChuvadiReader.Core/Documents/DocxViewService.cs
@@ -38,6 +38,7 @@ public sealed class DocxViewService
     public WordView Load(string path, string? password = null)
     {
         Document doc;
+        OfficePackageGuard.Check(path, "Word document"); // B-08: no zip bombs into the library
         try
         {
             doc = string.IsNullOrEmpty(password) ? Document.Load(path) : Document.Load(path, password);
diff --git a/src/ChuvadiReader.Core/Documents/OfficePackageGuard.cs b/src/ChuvadiReader.Core/Documents/OfficePackageGuard.cs
new file mode 100644
index 0000000..3cd2e33
--- /dev/null
+++ b/src/ChuvadiReader.Core/Documents/OfficePackageGuard.cs
@@ -0,0 +1,54 @@
+using System.IO.Compression;
+
+namespace ChuvadiReader.Core.Documents;
+
+/// <summary>
+/// B-08: refuses a Word / Excel package whose parts unpack to an unreasonable size (a "zip bomb") before the
+/// document library inflates anything. Reads only the zip directory (declared sizes): cheap, and it stops
+/// honest-header bombs; a package that lies about its sizes needs the library's own input limits (library
+/// ask). Not a zip (an encrypted Office file is a different container): left to the library.
+/// </summary>
+public static class OfficePackageGuard
+{
+    /// <summary>Largest single part, unpacked.</summary>
+    public const long MaxPartBytes = 256L * 1024 * 1024;
+
+    /// <summary>All parts together, unpacked.</summary>
+    public const long MaxTotalBytes = 1024L * 1024 * 1024;
+
+    /// <summary>Compression ratio beyond which a large part (over <see cref="RatioFloorBytes"/>) is refused.</summary>
+    public const long MaxRatio = 200;
+
+    public const long RatioFloorBytes = 16L * 1024 * 1024;
+
+    /// <param name="kind">"Word document" or "Excel workbook", for the message.</param>
+    public static void Check(string path, string kind)
+    {
+        ZipArchive zip;
+        try
+        {
+            zip = ZipFile.OpenRead(path);
+        }
+        catch (InvalidDataException)
+        {
+            return;
+        }
+
+        using (zip)
+        {
+            long total = 0;
+            foreach (var e in zip.Entries)
+            {
+                total += e.Length;
+                var bomb = e.Length > MaxPartBytes
+                           || total > MaxTotalBytes
+                           || (e.Length > RatioFloorBytes && e.CompressedLength > 0 && e.Length / e.CompressedLength > MaxRatio);
+                if (bomb)
+                {
+                    throw new DocumentViewException(ViewErrorReason.TooLarge,
+                        $"This {kind} is too large to open: its contents unpack to more than {Math.Max(total, e.Length) / (1024 * 1024):N0} MB. It may be damaged.");
+                }
+            }
+        }
+    }
+}
diff --git a/src/ChuvadiReader.Core/Documents/XlsxViewService.cs b/src/ChuvadiReader.Core/Documents/XlsxViewService.cs
index 5ccf480..23d5b55 100644
--- a/src/ChuvadiReader.Core/Documents/XlsxViewService.cs
+++ b/src/ChuvadiReader.Core/Documents/XlsxViewService.cs
@@ -37,6 +37,7 @@ public sealed class XlsxViewService
     public WorkbookView Load(string path, string? password = null)
     {
         Workbook wb;
+        OfficePackageGuard.Check(path, "Excel workbook"); // B-08: no zip bombs into the library
         try
         {
             wb = string.IsNullOrEmpty(password) ? Workbook.Load(path) : Workbook.Load(path, password);
diff --git a/src/ChuvadiReader.Core/Reader/TabsService.cs b/src/ChuvadiReader.Core/Reader/TabsService.cs
index 2955901..d2091ab 100644
--- a/src/ChuvadiReader.Core/Reader/TabsService.cs
+++ b/src/ChuvadiReader.Core/Reader/TabsService.cs
@@ -25,6 +25,21 @@ public sealed class ReaderTab
 
     public string? Error { get; set; }
 
+    /// <summary>The PDF is password-protected and waits for its password (B-07).</summary>
+    public bool NeedsPassword { get; set; }
+
+    /// <summary>The password that opened this tab's PDF. Memory only, for this tab (as Word/Excel); never persisted.</summary>
+    public string? Password { get; set; }
+
+    /// <summary>Set when the last password tried didn't open the file.</summary>
+    public string? PasswordError { get; set; }
+
+    /// <summary>The PDF couldn't be parsed (damaged or not really a PDF) — B-11. <see cref="Error"/> holds the
+    /// plain message; <see cref="ErrorDetail"/> the library's own text, for "Details".</summary>
+    public bool IsDamaged { get; set; }
+
+    public string? ErrorDetail { get; set; }
+
     // Per-tab view-state, persisted so switching (and restarting) lands where you left off.
     public int CurrentPage { get; set; } = 1;
 
@@ -413,17 +428,35 @@ public sealed class TabsService
 
         tab.IsLoading = true;
         tab.Error = null;
+        tab.ErrorDetail = null;
+        tab.IsDamaged = false;
         Changed?.Invoke();
 
         try
         {
-            tab.Session = await _reader.OpenAsync(tab.Path, tab.FileName, null, ct, transparentBackground: true).ConfigureAwait(false);
+            tab.Session = await _reader.OpenAsync(tab.Path, tab.FileName, tab.Password, ct, transparentBackground: true).ConfigureAwait(false);
+            tab.NeedsPassword = false;
+            tab.PasswordError = null;
             if (tab.CurrentPage > tab.Session.Document.PageCount)
             {
                 tab.CurrentPage = 1;
                 tab.ScrollTop = 0;
             }
         }
+        catch (Chuvadi.Pdf.Primitives.PdfPasswordRequiredException)
+        {
+            // B-07: ask for the password (the library throws this for a missing and for a wrong one).
+            tab.PasswordError = tab.Password is null ? null : "That password doesn't open this file.";
+            tab.Password = null;
+            tab.NeedsPassword = true;
+        }
+        catch (Exception ex) when (ex is Chuvadi.Pdf.Primitives.PdfParseException or Chuvadi.Pdf.Primitives.PdfCorruptionException)
+        {
+            // B-11: the handout's damaged-file state, not the parser's text (kept under Details).
+            tab.IsDamaged = true;
+            tab.Error = "This PDF is damaged";
+            tab.ErrorDetail = ex.Message;
+        }
         catch (Exception ex)
         {
             tab.Error = $"Could not open this document. {ex.Message}";
@@ -435,6 +468,24 @@ public sealed class TabsService
         }
     }
 
+    /// <summary>Opens a password-protected PDF tab with <paramref name="password"/> (kept in memory for this tab only).</summary>
+    public async Task UnlockAsync(string id, string password, CancellationToken ct = default)
+    {
+        var tab = _tabs.FirstOrDefault(t => t.Id == id);
+        if (tab is null || !tab.NeedsPassword)
+        {
+            return;
+        }
+
+        tab.Password = password;
+        await EnsureLoadedAsync(tab, ct).ConfigureAwait(false);
+        if (tab.Session is not null)
+        {
+            DropOtherCaches(tab);
+            await PersistAsync(ct).ConfigureAwait(false);
+        }
+    }
+
     private void DropOtherCaches(ReaderTab keep)
     {
         foreach (var t in _tabs)
diff --git a/src/ChuvadiReader.Linux/GtkHost.cs b/src/ChuvadiReader.Linux/GtkHost.cs
index 4b5523b..e046bf6 100644
--- a/src/ChuvadiReader.Linux/GtkHost.cs
+++ b/src/ChuvadiReader.Linux/GtkHost.cs
@@ -21,6 +21,8 @@ internal static unsafe class GtkHost
 
     public static event Action<string[]>? FilesDropped;
 
+    /// <summary>The desktop's window-button layout changed (D-101).</summary>
+    public static event Action<string>? ButtonLayoutChanged;
 
 #if CHUVADI_UITEST
     /// <summary>UI test build only: the same event the window's GTK drop target raises.</summary>
@@ -235,6 +237,9 @@ internal static unsafe class GtkHost
                     var nl = text.IndexOf('\n');
                     JsResult?.Invoke(int.Parse(text.AsSpan(0, nl), System.Globalization.CultureInfo.InvariantCulture), text[(nl + 1)..]);
                     break;
+                case Native.WindowEvent.ButtonLayout:
+                    ButtonLayoutChanged?.Invoke(text ?? string.Empty);
+                    break;
                 case Native.WindowEvent.FirstPaint:
                     FirstPaint?.Invoke();
                     break;
diff --git a/src/ChuvadiReader.Linux/Native.cs b/src/ChuvadiReader.Linux/Native.cs
index 3b26bec..215318b 100644
--- a/src/ChuvadiReader.Linux/Native.cs
+++ b/src/ChuvadiReader.Linux/Native.cs
@@ -18,6 +18,7 @@ internal static unsafe partial class Native
         DialogResult = 6,
         PrintResult = 7,
         JsResult = 8,
+        ButtonLayout = 9,
     }
 
     [LibraryImport(Lib, EntryPoint = "chvd_init")]
@@ -110,6 +111,10 @@ internal static unsafe partial class Native
     [LibraryImport(Lib, EntryPoint = "chvd_render_info")]
     public static partial int RenderInfo();
 
+    /// <summary>Sets GTK's window-button layout (UI tests: what the desktop's settings bridge does).</summary>
+    [LibraryImport(Lib, EntryPoint = "chvd_set_button_layout", StringMarshalling = StringMarshalling.Utf8)]
+    public static partial void SetButtonLayout(string layout);
+
     [LibraryImport(Lib, EntryPoint = "chvd_button_layout")]
     private static partial int ButtonLayout(byte* buf, int size);
 
diff --git a/src/ChuvadiReader.Linux/Platform/LinuxDesktop.cs b/src/ChuvadiReader.Linux/Platform/LinuxDesktop.cs
index 7109ed1..b1d1be8 100644
--- a/src/ChuvadiReader.Linux/Platform/LinuxDesktop.cs
+++ b/src/ChuvadiReader.Linux/Platform/LinuxDesktop.cs
@@ -5,26 +5,62 @@ using ChuvadiReader.Platform;
 
 namespace ChuvadiReader.Linux.Platform;
 
-/// <summary>What the Linux host is: desktop form factor, Ctrl labels, window buttons on the side the
-/// desktop's own button layout puts them (GNOME/KDE setting), 12 px window corners (handout).</summary>
-internal static class LinuxPlatformInfo
+/// <summary>What the Linux host is: desktop form factor, Ctrl labels, 12 px window corners (handout), and
+/// the window buttons exactly as the desktop lays them out (GNOME/KDE setting) — followed live: when the
+/// person changes the layout while Chuvadi is open, <see cref="IPlatformInfo.ChromeChanged"/> is raised and
+/// the top bar redraws (D-101).</summary>
+internal sealed class LinuxPlatformInfo : IPlatformInfo
 {
-    /// <summary>Main thread, after GTK init (reads GtkSettings). The window buttons follow the desktop's
-    /// layout exactly (<see cref="GtkButtonLayout"/>).</summary>
-    public static IPlatformInfo Create()
+    private ShellChrome _chrome;
+
+    private LinuxPlatformInfo(ShellChrome chrome) => _chrome = chrome;
+
+    /// <summary>Main thread, after GTK init (reads GtkSettings and listens for its changes).</summary>
+    public static LinuxPlatformInfo Create()
+    {
+        var info = new LinuxPlatformInfo(ChromeFor(Native.ButtonLayout()));
+        GtkHost.ButtonLayoutChanged += info.OnLayoutChanged;
+        return info;
+    }
+
+    public PlatformKind Kind => PlatformKind.Linux;
+
+    public FormFactor FormFactor => FormFactor.Desktop;
+
+    public event Action? FormFactorChanged { add { } remove { } }
+
+    public InputKinds Input => InputKinds.Mouse | InputKinds.Keyboard;
+
+    public ShellChrome Chrome => Volatile.Read(ref _chrome);
+
+    public event Action? ChromeChanged;
+
+    public PlatformCapabilities Capabilities => FixedPlatformInfo.DesktopCapabilities;
+
+    public IKeyLabels Keys { get; } = new CtrlKeyLabels();
+
+    private void OnLayoutChanged(string layout)
+    {
+        var chrome = ChromeFor(layout);
+        if (chrome.ButtonLayout is { } now && Chrome.ButtonLayout is { } was
+            && now.Left.SequenceEqual(was.Left) && now.Right.SequenceEqual(was.Right))
+        {
+            return;
+        }
+
+        Volatile.Write(ref _chrome, chrome);
+        ChromeChanged?.Invoke();
+    }
+
+    private static ShellChrome ChromeFor(string? layoutText)
     {
-        var layout = GtkButtonLayout.Parse(Native.ButtonLayout());
-        return new FixedPlatformInfo(
-            PlatformKind.Linux,
-            InputKinds.Mouse | InputKinds.Keyboard,
-            new ShellChrome(
-                GtkButtonLayout.SideOf(layout),
-                NativeMenuBar: false,
-                AccountMenu: false,
-                TitleBarDrag: true,
-                CornerRadiusPx: 12) { ButtonLayout = layout },
-            FixedPlatformInfo.DesktopCapabilities,
-            new CtrlKeyLabels());
+        var layout = GtkButtonLayout.Parse(layoutText);
+        return new ShellChrome(
+            GtkButtonLayout.SideOf(layout),
+            NativeMenuBar: false,
+            AccountMenu: false,
+            TitleBarDrag: true,
+            CornerRadiusPx: 12) { ButtonLayout = layout };
     }
 }
 
diff --git a/src/ChuvadiReader.Linux/UiTestDriver.cs b/src/ChuvadiReader.Linux/UiTestDriver.cs
index 0239dce..48e82d2 100644
--- a/src/ChuvadiReader.Linux/UiTestDriver.cs
+++ b/src/ChuvadiReader.Linux/UiTestDriver.cs
@@ -16,6 +16,7 @@ namespace ChuvadiReader.Linux;
 ///   commands             → [{id,label,group,keys,enabled}…] (the Ctrl K registry, IAppCommands)
 ///   invoke &lt;id&gt;          → true | false | "pending" (still running after 2 s, e.g. waiting in a dialog)
 ///   open &lt;path&gt;          → true (as a file arriving from outside: OpenDocumentService.Request)
+///   set-layout &lt;layout&gt;   → true (sets GTK's gtk-decoration-layout, as a desktop settings change does)
 ///   render-info          → {"noGpu":…,"compositingOff":…} (what the host chose at start-up, B-12)
 ///   drop &lt;p1&gt;\t&lt;p2&gt;…    → true (the window's drop handler, with these paths, as GTK's drop target calls it)
 /// tools/linux/uitest.py drives it.
@@ -118,6 +119,10 @@ internal static class UiTestDriver
                 await manager.Dispatcher.InvokeAsync(() => services.GetRequiredService<OpenDocumentService>().Request(arg));
                 return "true";
 
+            case "set-layout":
+                GtkHost.Post(() => Native.SetButtonLayout(arg));
+                return "true";
+
             case "render-info":
             {
                 var tcs = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
diff --git a/src/ChuvadiReader.Linux/native/chvdhost.c b/src/ChuvadiReader.Linux/native/chvdhost.c
index 953189e..5f82240 100644
--- a/src/ChuvadiReader.Linux/native/chvdhost.c
+++ b/src/ChuvadiReader.Linux/native/chvdhost.c
@@ -40,6 +40,7 @@ enum
     CHVD_EVENT_DIALOG_RESULT = 6,     /* payload "<token>" then one chosen path per line (none = cancelled) */
     CHVD_EVENT_PRINT_RESULT = 7,      /* payload "<token>" then key=value lines (none = cancelled) */
     CHVD_EVENT_JS_RESULT = 8,         /* payload "<token>" then the result as JSON, or "!<error>" (UI test builds) */
+    CHVD_EVENT_BUTTON_LAYOUT = 9,     /* payload: the desktop's new window-button layout (D-101) */
 };
 
 typedef void (*chvd_scheme_fn)(void *request, const char *uri);
@@ -90,6 +91,23 @@ static gboolean has_render_node(void)
     return found;
 }
 
+static void on_layout_changed(GObject *settings, GParamSpec *pspec, gpointer data)
+{
+    char *layout = NULL;
+    g_object_get(settings, "gtk-decoration-layout", &layout, NULL);
+    if (S.event)
+    {
+        S.event(CHVD_EVENT_BUTTON_LAYOUT, layout ? layout : "");
+    }
+    g_free(layout);
+}
+
+/* UI tests only call this: sets the layout the way the desktop's settings bridge does. */
+CHVD_EXPORT void chvd_set_button_layout(const char *layout)
+{
+    g_object_set(gtk_settings_get_default(), "gtk-decoration-layout", layout, NULL);
+}
+
 CHVD_EXPORT int chvd_init(chvd_scheme_fn scheme, chvd_message_fn message, chvd_wake_fn wake, chvd_event_fn event)
 {
     if (!scheme || !message || !wake || !event)
@@ -122,6 +140,9 @@ CHVD_EXPORT int chvd_init(chvd_scheme_fn scheme, chvd_message_fn message, chvd_w
      * File" pseudo-printer can't take that job, so the print dialog lists CUPS printers only.
      * (GTK 4 reads this from its settings; the GTK 3 GTK_PRINT_BACKENDS variable is gone.) */
     g_object_set(gtk_settings_get_default(), "gtk-print-backends", "cups", NULL);
+    /* D-101: the desktop's window-button layout can change while Chuvadi is open (GNOME/KDE settings reach
+     * GTK as this property); the top bar follows at once. */
+    g_signal_connect(gtk_settings_get_default(), "notify::gtk-decoration-layout", G_CALLBACK(on_layout_changed), NULL);
 
     S.loop = g_main_loop_new(NULL, FALSE);
     return 1;
diff --git a/src/ChuvadiReader.Platform/PlatformInfo.cs b/src/ChuvadiReader.Platform/PlatformInfo.cs
index 00e2bf3..86cc807 100644
--- a/src/ChuvadiReader.Platform/PlatformInfo.cs
+++ b/src/ChuvadiReader.Platform/PlatformInfo.cs
@@ -145,6 +145,17 @@ public interface IPlatformInfo
 
     ShellChrome Chrome { get; }
 
+    /// <summary>
+    /// Raised on the host's UI thread after <see cref="Chrome"/> changes — Linux: the desktop's window-button
+    /// layout changed while the app is open (D-101), so the top bar redraws at once. Hosts whose chrome never
+    /// changes don't implement it (the default does nothing).
+    /// </summary>
+    event Action? ChromeChanged
+    {
+        add { }
+        remove { }
+    }
+
     PlatformCapabilities Capabilities { get; }
 
     IKeyLabels Keys { get; }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/UnlockCard.razor b/src/ChuvadiReader.Ui/Components/Viewers/UnlockCard.razor
index c88757b..8af101d 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/UnlockCard.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/UnlockCard.razor
@@ -23,7 +23,7 @@
 </div>
 
 @code {
-    /// <summary>"document" or "workbook".</summary>
+    /// <summary>"document", "workbook" or "PDF".</summary>
     [Parameter] public string Kind { get; set; } = "document";
     [Parameter] public string? Error { get; set; }
     [Parameter] public bool Busy { get; set; }
diff --git a/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor b/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
index f1b52a5..161961c 100644
--- a/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
+++ b/src/ChuvadiReader.Ui/Components/Viewers/XlsxView.razor
@@ -37,18 +37,16 @@
                     </tr>
                 </thead>
                 <tbody>
-                    @for (int r = 1; r <= lastRow; r++)
+                    @* B-09/B-10: only the rows on screen are drawn (frozen header rows always), so a sheet's size
+                       — 5,000 rows × 256 columns is 1.28 million cells — can't stall the web view. *@
+                    @{ var frozen = Math.Min(s.FreezeRows, lastRow); }
+                    @for (int r = 1; r <= frozen; r++)
                     {
-                        <tr>
-                            <th class="xv-rowhdr">@r</th>
-                            @for (int c = 1; c <= lastCol; c++)
-                            {
-                                var cell = Cell(r, c);
-                                <td class="xv-cell @(cell is null ? "empty" : null) @(s.FreezeRows > 0 && r <= s.FreezeRows ? "frozen-row" : null) @(cell is not null && _hits.Contains((r, c)) ? "hit" : null)"
-                                    style="@CellStyle(cell)">@cell?.Text</td>
-                            }
-                        </tr>
+                        @Row(s, r, lastCol)
                     }
+                    <Virtualize Items="@RowsAfter(frozen, lastRow)" Context="r" ItemSize="RowPx" OverscanCount="30" SpacerElement="tr">
+                        @Row(s, r, lastCol)
+                    </Virtualize>
                 </tbody>
             </table>
         </div>
@@ -250,6 +248,16 @@
         if (_scrollToHit && _wb is not null)
         {
             _scrollToHit = false;
+            // The hit's row may not be drawn yet (rows are virtualised): bring its row on screen first, then
+            // centre the cell once it is.
+            var first = _hits.Count == 0 ? 0 : _hits.Min(h => h.Item1);
+            var sheet = _wb.Sheets[_active];
+            if (first > sheet.FreezeRows)
+            {
+                await JsVoidAsync("scrollGridTo", _scroll, (first - sheet.FreezeRows - 1) * RowPx * Scale);
+                await Task.Delay(50);
+            }
+
             await JsVoidAsync("scrollToSelector", _scroll, "td.hit");
         }
     }
@@ -305,6 +313,35 @@
 
     private SheetCell? Cell(int r, int c) => _index.TryGetValue((r, c), out var v) ? v : null;
 
+    /// <summary>A body row's height at 100 % (padding 3 + line 15 + padding 3 + border 1), for virtualising.</summary>
+    private const float RowPx = 22f;
+
+    private int[] _rowsAfter = [];
+    private int _rowsFrom = -1, _rowsTo = -1;
+
+    /// <summary>Rows after the frozen ones (the same array while the range is the same, so Virtualize keeps its place).</summary>
+    private int[] RowsAfter(int frozen, int lastRow)
+    {
+        if (frozen != _rowsFrom || lastRow != _rowsTo)
+        {
+            _rowsFrom = frozen;
+            _rowsTo = lastRow;
+            _rowsAfter = lastRow > frozen ? Enumerable.Range(frozen + 1, lastRow - frozen).ToArray() : [];
+        }
+
+        return _rowsAfter;
+    }
+
+    private RenderFragment Row(SheetView s, int r, int lastCol) => @<tr>
+        <th class="xv-rowhdr">@r</th>
+        @for (int c = 1; c <= lastCol; c++)
+        {
+            var cell = Cell(r, c);
+            <td class="xv-cell @(cell is null ? "empty" : null) @(s.FreezeRows > 0 && r <= s.FreezeRows ? "frozen-row" : null) @(cell is not null && _hits.Contains((r, c)) ? "hit" : null)"
+                style="@CellStyle(cell)">@cell?.Text</td>
+        }
+    </tr>;
+
     private static string ColLetter(int col)
     {
         // 1 → A, 26 → Z, 27 → AA …
diff --git a/src/ChuvadiReader.Ui/Layout/MainLayout.razor b/src/ChuvadiReader.Ui/Layout/MainLayout.razor
index eb6a8d6..b9763a6 100644
--- a/src/ChuvadiReader.Ui/Layout/MainLayout.razor
+++ b/src/ChuvadiReader.Ui/Layout/MainLayout.razor
@@ -52,15 +52,17 @@
     {
     <header class="topbar @(_leftOpen ? "lb-open" : null)" @onmousedown="StartDrag">
         <div class="tb-left">
-            @if (Platform.Chrome.ButtonLayout is { } layoutL)
-            {
-                <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" Items="layoutL.Left" />
-            }
-            else if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Left)
-            {
-                <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" />
-            }
+            @* B-19 (D-110 A): left-hand window buttons sit inside the brand cell, so the cell keeps the left
+               bar's width and its divider stays in line; the wordmark moves along. *@
             <div class="tb-brandbox">
+                @if (Platform.Chrome.ButtonLayout is { } layoutL)
+                {
+                    <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" Items="layoutL.Left" />
+                }
+                else if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Left)
+                {
+                    <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" />
+                }
                 <button class="tb-brand" @onclick='() => Go("/")' @onmousedown:stopPropagation="true" @ondblclick:stopPropagation="true" title="Home">
                     @if (_leftOpen)
                     {
@@ -306,6 +308,7 @@
         if (Platform.Kind != ChuvadiReader.Platform.PlatformKind.Windows)
         {
             Platform.FormFactorChanged += OnFormFactorChanged;
+            Platform.ChromeChanged += OnChromeChanged;
         }
 
     }
@@ -780,11 +783,15 @@
         StateHasChanged();
     });
 
+    // The desktop's window-button layout changed (Linux, D-101): redraw the top bar.
+    private void OnChromeChanged() => _ = InvokeAsync(StateHasChanged);
+
     public async ValueTask DisposeAsync()
     {
         if (Platform.Kind != ChuvadiReader.Platform.PlatformKind.Windows)
         {
             Platform.FormFactorChanged -= OnFormFactorChanged;
+            Platform.ChromeChanged -= OnChromeChanged;
         }
 
         Theme.Changed -= OnThemeChanged;
diff --git a/src/ChuvadiReader.Ui/Pages/Reader.razor b/src/ChuvadiReader.Ui/Pages/Reader.razor
index 41fbaa8..69b94bf 100644
--- a/src/ChuvadiReader.Ui/Pages/Reader.razor
+++ b/src/ChuvadiReader.Ui/Pages/Reader.razor
@@ -300,6 +300,35 @@
             <div class="rempty-t">Opening @tab.FileName…</div>
         </div>
     }
+    else if (tab.NeedsPassword)
+    {
+        @* B-07: a password-protected PDF asks for its password, as Word and Excel tabs do. *@
+        <UnlockCard Kind="PDF" Error="@tab.PasswordError" Busy="tab.IsLoading" OnUnlock="pw => Tabs.UnlockAsync(tab.Id, pw)" />
+    }
+    else if (tab.IsDamaged)
+    {
+        @* B-11: the handout's "Can't open · damaged file" state (States & Feedback 8e). *@
+        <div class="rempty">
+            <Icon Name="warning" Size="40" />
+            <div class="rempty-t">This PDF is damaged</div>
+            <div class="rempty-sub">Chuvadi couldn't read this file, maybe because a download or copy didn't finish. Chuvadi can try to rebuild it as a new copy.</div>
+            <div class="rempty-acts">
+                <button class="rempty-btn" @onclick="TryRecovery" disabled="@_recovering">@(_recovering ? "Repairing…" : "Try to repair (new copy)")</button>
+                @if (FileManager.IsAvailable)
+                {
+                    <button class="rempty-btn" @onclick="() => FileManager.RevealAsync(tab.Path)">Show in folder</button>
+                }
+            </div>
+            @if (_recoverStatus is not null)
+            {
+                <div class="rempty-sub">@_recoverStatus</div>
+            }
+            @if (!string.IsNullOrEmpty(tab.ErrorDetail))
+            {
+                <details class="rempty-sub"><summary>Details</summary>@tab.ErrorDetail</details>
+            }
+        </div>
+    }
     else if (tab.Error is not null)
     {
         <div class="rempty">
@@ -560,7 +589,8 @@
                     </div>
                     @if (doc is not null)
                     {
-                        <button class="rpage-send" title="Send page @(n + 1) to a desk"
+                        @* B-23: a hover control on every page; out of the Tab order, so Tab reaches the rails first. *@
+                        <button class="rpage-send" title="Send page @(n + 1) to a desk" tabindex="-1"
                                 @onclick="() => ToggleSendMenu(n)" @onclick:stopPropagation="true">
                             <Icon Name="grid-view" Size="14" />
                         </button>
diff --git a/src/ChuvadiReader.Ui/Pages/Reader.razor.css b/src/ChuvadiReader.Ui/Pages/Reader.razor.css
index 9d18587..2128436 100644
--- a/src/ChuvadiReader.Ui/Pages/Reader.razor.css
+++ b/src/ChuvadiReader.Ui/Pages/Reader.razor.css
@@ -144,6 +144,8 @@
 
 .rload-icon { color: var(--chvd-binding); animation: rpulse 1.1s ease-in-out infinite; }
 @keyframes rpulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
+.rempty-acts { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
+details.rempty-sub summary { cursor: pointer; }
 .rempty-btn {
     font-size: 13px;
     color: var(--chvd-ink);
diff --git a/src/ChuvadiReader.Ui/wwwroot/css/shell.css b/src/ChuvadiReader.Ui/wwwroot/css/shell.css
index 88764b0..eeec756 100644
--- a/src/ChuvadiReader.Ui/wwwroot/css/shell.css
+++ b/src/ChuvadiReader.Ui/wwwroot/css/shell.css
@@ -68,6 +68,9 @@
     transition: width var(--chvd-base);
 }
 .topbar.lb-open .tb-brandbox { width: calc(var(--sh-left-open) - 12px); }
+/* Left-hand window buttons inside the brand cell (B-19): the cell keeps its width; the wordmark follows the
+   buttons. Only a collapsed left bar with more buttons than fit lets the cell grow, never clipping a button. */
+.tb-brandbox { gap: 10px; min-width: max-content; }
 .tb-left { align-self: stretch; }
 .topbar:not(.lb-open) .tb-brand { margin: 0 auto 0 4px; }
 .tb-mid { display: flex; justify-content: center; }
diff --git a/src/ChuvadiReader.Ui/wwwroot/fonts/google/OFL.txt b/src/ChuvadiReader.Ui/wwwroot/fonts/google/OFL.txt
new file mode 100644
index 0000000..b5f32e7
--- /dev/null
+++ b/src/ChuvadiReader.Ui/wwwroot/fonts/google/OFL.txt
@@ -0,0 +1,97 @@
+Fonts in this folder (from Google Fonts), each under the SIL Open Font License, Version 1.1 (below):
+
+Fraunces: Copyright 2020 The Fraunces Project Authors (github.com/undercasetype/Fraunces)
+IBM Plex Mono: Copyright 2017 IBM Corp. All rights reserved.
+Instrument Serif: Copyright 2022 The Instrument Serif Project Authors (https://github.com/Instrument/instrument-serif)
+Tiro Tamil: Copyright 2020 The Indigo Project Authors (https://github.com/TiroTypeworks/Indigo)
+
+-----------------------------------------------------------
+SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
+-----------------------------------------------------------
+
+PREAMBLE
+
+The goals of the Open Font License (OFL) are to stimulate worldwide
+development of collaborative font projects, to support the font
+creation efforts of academic and linguistic communities, and to provide
+a free and open framework in which fonts may be shared and improved in
+partnership with others.
+
+The OFL allows the licensed fonts to be used, studied, modified and
+redistributed freely as long as they are not sold by themselves. The
+fonts, including any derivative works, can be bundled, embedded,
+redistributed and/or sold with any software provided that any reserved
+names are not used by derivative works. The fonts and derivatives,
+however, cannot be released under any other type of license. The
+requirement for fonts to remain under this license does not apply to
+any document created using the fonts or their derivatives.
+
+DEFINITIONS
+
+"Font Software" refers to the set of files released by the Copyright
+Holder(s) under this license and clearly marked as such. This may
+include source files, build scripts and documentation.
+
+"Reserved Font Name" refers to any names specified as such after the
+copyright statement(s).
+
+"Original Version" refers to the collection of Font Software components
+as distributed by the Copyright Holder(s).
+
+"Modified Version" refers to any derivative made by adding to,
+deleting, or substituting -- in part or in whole -- any of the
+components of the Original Version, by changing formats or by porting
+the Font Software to a new environment.
+
+"Author" refers to any designer, engineer, programmer, technical writer
+or other person who contributed to the Font Software.
+
+PERMISSION & CONDITIONS
+
+Permission is hereby granted, free of charge, to any person obtaining a
+copy of the Font Software, to use, study, copy, merge, embed, modify,
+redistribute, and sell modified and unmodified copies of the Font
+Software, subject to the following conditions:
+
+1) Neither the Font Software nor any of its individual components, in
+Original or Modified Versions, may be sold by itself.
+
+2) Original or Modified Versions of the Font Software may be bundled,
+redistributed and/or sold with any software, provided that each copy
+contains the above copyright notice and this license. These can be
+included either as stand-alone text files, human-readable headers or
+in the appropriate machine-readable metadata fields within text or
+binary files as long as those fields can be easily viewed by the user.
+
+3) No Modified Version of the Font Software may use the Reserved Font
+Name(s) unless explicit written permission is granted by the
+corresponding Copyright Holder. This restriction only applies to the
+primary font name as presented to the users.
+
+4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
+Software shall not be used to promote, endorse or advertise any
+Modified Version, except to acknowledge the contribution(s) of the
+Copyright Holder(s) and the Author(s) or with their explicit written
+permission.
+
+5) The Font Software, modified or unmodified, in part or in whole, must
+be distributed entirely under this license, and must not be distributed
+under any other license. The requirement for fonts to remain under this
+license does not apply to any document created using the Font Software.
+
+TERMINATION
+
+This license becomes null and void if any of the above conditions are
+not met.
+
+DISCLAIMER
+
+THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
+EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
+MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
+OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
+COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
+INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
+DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
+FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
+OTHER DEALINGS IN THE FONT SOFTWARE.
diff --git a/src/ChuvadiReader.Ui/wwwroot/js/viewers.js b/src/ChuvadiReader.Ui/wwwroot/js/viewers.js
index af5e974..fb59f9f 100644
--- a/src/ChuvadiReader.Ui/wwwroot/js/viewers.js
+++ b/src/ChuvadiReader.Ui/wwwroot/js/viewers.js
@@ -104,6 +104,11 @@ export function scrollToLine(el, line, approxPx, center) {
     requestAnimationFrame(settle);
 }
 
+/** Scrolls a grid's container to a vertical offset (virtualised rows: bring a row on screen first). */
+export function scrollGridTo(el, top) {
+    if (el) el.scrollTop = Math.max(0, top - el.clientHeight / 2);
+}
+
 export function scrollToSelector(el, selector) {
     if (!el) return;
     const t = el.querySelector(selector);
diff --git a/src/ChuvadiReader.Ui/wwwroot/lipi-sans/OFL.txt b/src/ChuvadiReader.Ui/wwwroot/lipi-sans/OFL.txt
new file mode 100644
index 0000000..41d88d5
--- /dev/null
+++ b/src/ChuvadiReader.Ui/wwwroot/lipi-sans/OFL.txt
@@ -0,0 +1,93 @@
+LiPi Sans combines Inter and Noto Sans; the copyright notices are in LICENSE.txt and in the font files.
+Both are licensed under the SIL Open Font License, Version 1.1, whose full text follows.
+
+-----------------------------------------------------------
+SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
+-----------------------------------------------------------
+
+PREAMBLE
+
+The goals of the Open Font License (OFL) are to stimulate worldwide
+development of collaborative font projects, to support the font
+creation efforts of academic and linguistic communities, and to provide
+a free and open framework in which fonts may be shared and improved in
+partnership with others.
+
+The OFL allows the licensed fonts to be used, studied, modified and
+redistributed freely as long as they are not sold by themselves. The
+fonts, including any derivative works, can be bundled, embedded,
+redistributed and/or sold with any software provided that any reserved
+names are not used by derivative works. The fonts and derivatives,
+however, cannot be released under any other type of license. The
+requirement for fonts to remain under this license does not apply to
+any document created using the fonts or their derivatives.
+
+DEFINITIONS
+
+"Font Software" refers to the set of files released by the Copyright
+Holder(s) under this license and clearly marked as such. This may
+include source files, build scripts and documentation.
+
+"Reserved Font Name" refers to any names specified as such after the
+copyright statement(s).
+
+"Original Version" refers to the collection of Font Software components
+as distributed by the Copyright Holder(s).
+
+"Modified Version" refers to any derivative made by adding to,
+deleting, or substituting -- in part or in whole -- any of the
+components of the Original Version, by changing formats or by porting
+the Font Software to a new environment.
+
+"Author" refers to any designer, engineer, programmer, technical writer
+or other person who contributed to the Font Software.
+
+PERMISSION & CONDITIONS
+
+Permission is hereby granted, free of charge, to any person obtaining a
+copy of the Font Software, to use, study, copy, merge, embed, modify,
+redistribute, and sell modified and unmodified copies of the Font
+Software, subject to the following conditions:
+
+1) Neither the Font Software nor any of its individual components, in
+Original or Modified Versions, may be sold by itself.
+
+2) Original or Modified Versions of the Font Software may be bundled,
+redistributed and/or sold with any software, provided that each copy
+contains the above copyright notice and this license. These can be
+included either as stand-alone text files, human-readable headers or
+in the appropriate machine-readable metadata fields within text or
+binary files as long as those fields can be easily viewed by the user.
+
+3) No Modified Version of the Font Software may use the Reserved Font
+Name(s) unless explicit written permission is granted by the
+corresponding Copyright Holder. This restriction only applies to the
+primary font name as presented to the users.
+
+4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
+Software shall not be used to promote, endorse or advertise any
+Modified Version, except to acknowledge the contribution(s) of the
+Copyright Holder(s) and the Author(s) or with their explicit written
+permission.
+
+5) The Font Software, modified or unmodified, in part or in whole, must
+be distributed entirely under this license, and must not be distributed
+under any other license. The requirement for fonts to remain under this
+license does not apply to any document created using the Font Software.
+
+TERMINATION
+
+This license becomes null and void if any of the above conditions are
+not met.
+
+DISCLAIMER
+
+THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
+EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
+MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
+OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
+COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
+INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
+DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
+FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
+OTHER DEALINGS IN THE FONT SOFTWARE.
diff --git a/tests/ChuvadiReader.Tests/OfficePackageGuardTests.cs b/tests/ChuvadiReader.Tests/OfficePackageGuardTests.cs
new file mode 100644
index 0000000..a374d6c
--- /dev/null
+++ b/tests/ChuvadiReader.Tests/OfficePackageGuardTests.cs
@@ -0,0 +1,53 @@
+using System.IO.Compression;
+using ChuvadiReader.Core.Documents;
+using Xunit;
+
+namespace ChuvadiReader.Tests;
+
+/// <summary>B-08: a Word / Excel package whose parts unpack to an unreasonable size is refused before the
+/// document library inflates it.</summary>
+public class OfficePackageGuardTests
+{
+    private static string Package(long partBytes)
+    {
+        var path = Path.Combine(Path.GetTempPath(), $"guard-{Guid.NewGuid():N}.docx");
+        using (var zip = ZipFile.Open(path, ZipArchiveMode.Create))
+        {
+            zip.CreateEntry("[Content_Types].xml").Open().Dispose();
+            using var part = zip.CreateEntry("word/document.xml", CompressionLevel.SmallestSize).Open();
+            var zeros = new byte[1 << 20];
+            for (long written = 0; written < partBytes; written += zeros.Length)
+            {
+                part.Write(zeros, 0, (int)Math.Min(zeros.Length, partBytes - written));
+            }
+        }
+
+        return path;
+    }
+
+    [Fact]
+    public void A_zip_bomb_is_refused_before_it_is_unpacked()
+    {
+        var path = Package(300L * 1024 * 1024);
+        Assert.True(new FileInfo(path).Length < 2 * 1024 * 1024, "the bomb itself is small");
+
+        var ex = Assert.Throws<DocumentViewException>(() => OfficePackageGuard.Check(path, "Word document"));
+        Assert.Equal(ViewErrorReason.TooLarge, ex.Reason);
+        Assert.Contains("too large to open", ex.Message);
+    }
+
+    [Fact]
+    public void A_normal_package_passes()
+    {
+        var path = Package(64 * 1024);
+        OfficePackageGuard.Check(path, "Word document");
+    }
+
+    [Fact]
+    public void A_file_that_is_not_a_zip_is_left_to_the_library()
+    {
+        var path = Path.Combine(Path.GetTempPath(), $"guard-{Guid.NewGuid():N}.docx");
+        File.WriteAllBytes(path, [0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]); // an encrypted Office file's header
+        OfficePackageGuard.Check(path, "Word document");
+    }
+}
diff --git a/tests/ChuvadiReader.Tests/PdfPasswordTabTests.cs b/tests/ChuvadiReader.Tests/PdfPasswordTabTests.cs
new file mode 100644
index 0000000..fd6fd40
--- /dev/null
+++ b/tests/ChuvadiReader.Tests/PdfPasswordTabTests.cs
@@ -0,0 +1,108 @@
+using ChuvadiReader.Core.Documents;
+using ChuvadiReader.Core.Reader;
+using Xunit;
+
+namespace ChuvadiReader.Tests;
+
+/// <summary>B-07: a password-protected PDF asks for its password in its tab and opens with it.</summary>
+public class PdfPasswordTabTests
+{
+    private static async Task<string> LockedPdf(string password)
+    {
+        var output = TestPdf.TempOutput();
+        await new PasswordService().ProtectAsync(TestPdf.TextPage("Locked page"), output,
+            new PasswordProtectOptions { OpenPassword = password });
+        return output;
+    }
+
+    [Fact]
+    public async Task A_locked_pdf_asks_for_its_password_instead_of_failing()
+    {
+        var path = await LockedPdf("open-sesame");
+        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
+
+        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);
+
+        Assert.True(tab.NeedsPassword);
+        Assert.Null(tab.Error);
+        Assert.Null(tab.PasswordError);
+        Assert.Null(tab.Session);
+    }
+
+    [Fact]
+    public async Task A_wrong_password_says_so_and_asks_again()
+    {
+        var path = await LockedPdf("open-sesame");
+        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
+        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);
+
+        await tabs.UnlockAsync(tab.Id, "nope");
+
+        Assert.True(tab.NeedsPassword);
+        Assert.Equal("That password doesn't open this file.", tab.PasswordError);
+        Assert.Null(tab.Session);
+        Assert.Null(tab.Password);
+    }
+
+    [Fact]
+    public async Task The_right_password_opens_the_tab()
+    {
+        var path = await LockedPdf("open-sesame");
+        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
+        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);
+
+        await tabs.UnlockAsync(tab.Id, "nope");
+        await tabs.UnlockAsync(tab.Id, "open-sesame");
+
+        Assert.False(tab.NeedsPassword);
+        Assert.Null(tab.PasswordError);
+        Assert.NotNull(tab.Session);
+        Assert.Equal(1, tab.Session!.Document.PageCount);
+        Assert.True(tab.Session.Document.IsEncrypted);
+    }
+}
+
+/// <summary>B-11: an unreadable PDF shows the damaged-file state with the library's text kept as detail.</summary>
+public class DamagedPdfTabTests
+{
+    [Fact]
+    public async Task A_bad_startxref_offset_is_reported_as_damaged_not_as_parser_text()
+    {
+        var src = TestPdf.TextPage("Page");
+        var bytes = File.ReadAllText(src, System.Text.Encoding.Latin1);
+        var at = bytes.LastIndexOf("startxref", StringComparison.Ordinal);
+        var end = bytes.IndexOf("%%EOF", at, StringComparison.Ordinal);
+        var broken = bytes[..at] + "startxref\n999999\n" + bytes[end..];
+        var path = TestPdf.TempOutput();
+        File.WriteAllText(path, broken, System.Text.Encoding.Latin1);
+
+        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
+        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);
+
+        Assert.Null(tab.Session);
+        Assert.True(tab.IsDamaged);
+        Assert.Equal("This PDF is damaged", tab.Error);
+        Assert.False(string.IsNullOrEmpty(tab.ErrorDetail));
+
+        // "Try to repair (new copy)" rebuilds it, and the copy opens.
+        var repaired = await new RecoveryService(new SaveFolderService(new MemoryStorage())).RecoverAsync(path, Path.GetTempPath());
+        Assert.True(repaired.Repaired);
+        var copy = await tabs.OpenAsync(repaired.OutputPath, Path.GetFileName(repaired.OutputPath), DocumentFormat.Pdf);
+        Assert.NotNull(copy.Session);
+        Assert.Equal(1, copy.Session!.Document.PageCount);
+    }
+
+    [Fact]
+    public async Task An_empty_file_is_reported_as_damaged()
+    {
+        var path = TestPdf.TempOutput();
+        File.WriteAllBytes(path, []);
+
+        var tabs = new TabsService(new ChuvadiPdfReader(), new MemoryStorage());
+        var tab = await tabs.OpenAsync(path, Path.GetFileName(path), DocumentFormat.Pdf);
+
+        Assert.True(tab.IsDamaged);
+        Assert.Equal("This PDF is damaged", tab.Error);
+        Assert.Contains("startxref", tab.ErrorDetail);
+    }
+}
diff --git a/tools/linux/uitest.py b/tools/linux/uitest.py
index b46c64c..70b0713 100644
--- a/tools/linux/uitest.py
+++ b/tools/linux/uitest.py
@@ -694,6 +694,21 @@ def render_choice():
 step("34b2-render-choice-without-gpu", render_choice)
 
 
+def tab_order():
+    """B-23: Tab doesn't walk through a "Send page N to a desk" button per page before anything else."""
+    ensure_reader(0)
+    stops = app.js("return [...document.querySelectorAll('button, [href], input, select, textarea, [tabindex]')]"
+                   ".filter(e => e.tabIndex >= 0 && !e.disabled && e.offsetParent !== null)"
+                   ".slice(0, 12).map(e => e.className || e.tagName)")
+    sends = [c for c in stops if "rpage-send" in str(c)]
+    if sends:
+        raise AssertionError(f"per-page buttons in the first Tab stops: {stops}")
+    return "first Tab stops: " + ", ".join(str(c).split()[0] for c in stops[:6])
+
+
+step("34b3-tab-order-skips-per-page-buttons", tab_order)
+
+
 def drop_several():
     """B-06: several files dropped on the window — each in its own tab (the window's drop handler, as GTK
     calls it; a real drag from a file manager is checked by hand)."""
@@ -807,12 +822,24 @@ def button_layouts():
             app.wait(lambda: "Iconic" in wm_state()[1], 10, "minimised")
             subprocess.run(["xdotool", "windowactivate", "--sync", wm_state()[0]], env=app.env, capture_output=True)
             app.wait(lambda: "Iconic" not in wm_state()[1], 10, "back from minimised")
+        # B-19: the brand cell's divider lines up with the left bar's edge, wherever the buttons are.
+        cell = app.js("var r=document.querySelector('.tb-brandbox').getBoundingClientRect(); return r.right")
+        bar = app.js("var r=document.querySelector('.leftbar').getBoundingClientRect(); return r.right")
+        if abs(cell - bar) > 1.5:  # top bar padding 12 px + cell (left bar − 12 px) = the left bar's edge
+            raise AssertionError(f"{layout!r}: top-bar cell ends at {cell:.0f} px, left bar at {bar:.0f} px")
         app.shot(f"35-layout-{i}")
         seen.append(f"{layout or '(empty)'} → {'/'.join(left) or '-'} | {'/'.join(right) or '-'}")
     # The window-close step runs under vanilla GNOME's close-only layout.
     app.restart(["gtk-decoration-layout=appmenu:close"], log_name="app-3.log")
     if shown_buttons() != {"left": [], "right": ["close"]}:
         raise AssertionError("close-only layout not shown for the window-close step")
+    # D-101: the desktop's layout changes while the app is open — the top bar follows without a restart.
+    for layout, left, right in [(":minimize,maximize,close", [], ["min", "max", "close"]),
+                                ("close,maximize:", ["close", "max"], []),
+                                ("appmenu:close", [], ["close"])]:
+        app.send("set-layout " + layout)
+        app.wait(lambda: shown_buttons() == {"left": left, "right": right}, 10, f"live change to {layout}")
+        seen.append(f"live {layout} → {'/'.join(left) or '-'} | {'/'.join(right) or '-'}")
     return f"{len(LAYOUTS)} layouts exact: " + "; ".join(seen)
 
 
```
