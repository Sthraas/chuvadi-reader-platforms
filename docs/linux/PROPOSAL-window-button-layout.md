# Proposal: window buttons follow the desktop's layout exactly (D-93, bug)

**Route (coordinator, 8 Nov 18:15):** fixed and pushed on `platform/linux` with its tests; the shared-file
diff below (Platform contract + Ui) goes into the Foundation's next combined patch unchanged, so the Linux
rebase onto it is a no-op.

**Bug.** The design note says to honour the GNOME/KDE button layout. Linux took only the side from it; the
Ui then drew all three buttons. Vanilla GNOME (`appmenu:close`) showed minimise and maximise it doesn't have;
`close:maximize` or `:close,minimize` couldn't be shown at all.

**Fix.**
- Contract (`ChuvadiReader.Platform`, additive): `ShellChrome.ButtonLayout` — `WindowButtonLayout(Left, Right)`,
  each an ordered list of `WindowButton` (Minimize, Maximize, Close). Null (Windows, macOS, Android, Web):
  exactly today's behaviour; the positional record and its constructor are unchanged.
- Ui: `WindowButtons` gets an optional `Items` list and draws exactly those buttons in that order at its
  side (left: the left-hand look, 15 px; right: the right-hand look, 13 px — the existing styles).
  `MainLayout` uses it at both ends when `ButtonLayout` is set; otherwise its markup runs as before (the
  Windows inline buttons are untouched).
- Linux (own files): the shim returns GTK's whole `gtk-decoration-layout`; `GtkButtonLayout.Parse` reads it
  exactly as GTK 4.14's header bar does (checked against Ubuntu's GTK 4.14.5 source, gtkwindowcontrols.c:
  split at the first ':', names compared exactly, unknown/icon/menu/appmenu/spacer skipped, duplicates
  drawn twice, no ':' = all on the left).

**Tests.**
- `tests/ChuvadiReader.Linux.Tests` (new): 25 parser cases — vanilla GNOME, Ubuntu, KDE, left, split, any
  subset and order, none, no ':', extra ':', non-button names, exact names, duplicates, unset.
- UI pass step `35-button-layouts` (new): the real app under 8 layouts set through GTK's own settings file;
  checks the buttons and their order at both ends, and that minimise / maximise do their job; the final
  window-close step then runs under vanilla GNOME's close-only layout.
- Screenshot: `screenshots/button-layouts-close-only-and-split.png` (top: `appmenu:close`; bottom:
  `close:maximize`).

**Not included (option for the coordinator).** The layout is read at start-up. If the person changes it in
GNOME/KDE settings while Chuvadi is open, GTK apps redraw at once; Chuvadi would follow on the next start.
- A. At start-up (built): no more contract; but a running window keeps the old buttons until restarted.
- B. Live: the host watches GTK's setting and the Ui redraws — needs a change event in the contract (e.g.
  `IPlatformInfo.ChromeChanged`) and MainLayout listening. True to "follow the desktop" at every moment.
Recommendation: B, small; it would ride the same patch if you agree.

## The shared-file diff (Platform + Ui)

```diff
diff --git a/src/ChuvadiReader.Platform/PlatformInfo.cs b/src/ChuvadiReader.Platform/PlatformInfo.cs
index f9f7fb6..00e2bf3 100644
--- a/src/ChuvadiReader.Platform/PlatformInfo.cs
+++ b/src/ChuvadiReader.Platform/PlatformInfo.cs
@@ -63,7 +63,27 @@ public sealed record ShellChrome(
     bool NativeMenuBar,
     bool AccountMenu,
     bool TitleBarDrag,
-    int CornerRadiusPx);
+    int CornerRadiusPx)
+{
+    /// <summary>
+    /// The desktop's own button layout, followed exactly: which buttons, in which order, on which side
+    /// (Linux: GNOME/KDE via GTK's <c>gtk-decoration-layout</c>, e.g. close only, or close on the left and
+    /// maximise on the right). Null: the platform's usual set on the side <see cref="Buttons"/> names
+    /// (Windows, macOS).
+    /// </summary>
+    public WindowButtonLayout? ButtonLayout { get; init; }
+}
+
+/// <summary>One window button.</summary>
+public enum WindowButton
+{
+    Minimize,
+    Maximize,
+    Close,
+}
+
+/// <summary>Window buttons in order at each end of the top bar (either list may be empty).</summary>
+public sealed record WindowButtonLayout(IReadOnlyList<WindowButton> Left, IReadOnlyList<WindowButton> Right);
 
 /// <summary>
 /// What this host can do. The Ui hides or locks a control whose capability is false
diff --git a/src/ChuvadiReader.Ui/Components/Platform/WindowButtons.razor b/src/ChuvadiReader.Ui/Components/Platform/WindowButtons.razor
index ae4721c..d3a6f0f 100644
--- a/src/ChuvadiReader.Ui/Components/Platform/WindowButtons.razor
+++ b/src/ChuvadiReader.Ui/Components/Platform/WindowButtons.razor
@@ -4,13 +4,38 @@
 @inject IWindowControls Win
 
 @*
-    Left-hand window buttons: macOS order (close · minimise · zoom), and Linux desktops whose button
-    layout is on the left. MainLayout instantiates this only when Chrome.Buttons is Left; right-hand
-    buttons (Windows, Linux default) stay inline in MainLayout so the Windows markup and startup are
-    exactly as before. Android and Web: none (Web shows the account menu instead).
+    Left-hand window buttons: macOS order (close · minimise · zoom). MainLayout instantiates this when
+    Chrome.Buttons is Left; right-hand buttons (Windows) stay inline in MainLayout so the Windows markup
+    and startup are exactly as before. Android and Web: none (Web shows the account menu instead).
+
+    With Items (the desktop's exact layout, Chrome.ButtonLayout — Linux), this draws exactly those
+    buttons in that order at the Side it is placed on, any subset, either side.
 *@
 
-@if (Platform.Chrome.Buttons == Side)
+@if (Items is { } items)
+{
+    @if (items.Count > 0)
+    {
+        <div class="traffic @(Side == ChuvadiReader.Platform.WindowButtons.Left ? "traffic-left" : null)" @onmousedown:stopPropagation="true" @ondblclick:stopPropagation="true">
+            @foreach (var b in items)
+            {
+                @switch (b)
+                {
+                    case WindowButton.Minimize:
+                        <button class="tl tl-min" @onclick="() => Win.Minimize()" aria-label="Minimize"><Icon Name="minus" Size="10" /></button>
+                        break;
+                    case WindowButton.Maximize:
+                        <button class="tl tl-max" @onclick="() => Win.ToggleMaximize()" aria-label="@(Win.IsMaximized ? "Restore" : "Maximize")"><Icon Name="@(Win.IsMaximized ? "restore" : "square")" Size="9" /></button>
+                        break;
+                    case WindowButton.Close:
+                        <button class="tl tl-close" @onclick="() => Win.Close()" aria-label="Close"><Icon Name="x" Size="10" /></button>
+                        break;
+                }
+            }
+        </div>
+    }
+}
+else if (Platform.Chrome.Buttons == Side)
 {
     <div class="traffic traffic-left" @onmousedown:stopPropagation="true" @ondblclick:stopPropagation="true">
         <button class="tl tl-close" @onclick="() => Win.Close()" aria-label="Close"><Icon Name="x" Size="10" /></button>
@@ -24,6 +49,10 @@
     [Parameter, EditorRequired]
     public ChuvadiReader.Platform.WindowButtons Side { get; set; }
 
+    /// <summary>The exact buttons, in order (from <see cref="ShellChrome.ButtonLayout"/>); null: the usual set.</summary>
+    [Parameter]
+    public IReadOnlyList<WindowButton>? Items { get; set; }
+
     protected override void OnInitialized() => Win.StateChanged += OnWindowStateChanged;
 
     private void OnWindowStateChanged() => InvokeAsync(StateHasChanged);
diff --git a/src/ChuvadiReader.Ui/Layout/MainLayout.razor b/src/ChuvadiReader.Ui/Layout/MainLayout.razor
index e0f06f0..4a9119a 100644
--- a/src/ChuvadiReader.Ui/Layout/MainLayout.razor
+++ b/src/ChuvadiReader.Ui/Layout/MainLayout.razor
@@ -43,7 +43,11 @@
     {
     <header class="topbar @(_leftOpen ? "lb-open" : null)" @onmousedown="StartDrag">
         <div class="tb-left">
-            @if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Left)
+            @if (Platform.Chrome.ButtonLayout is { } layoutL)
+            {
+                <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" Items="layoutL.Left" />
+            }
+            else if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Left)
             {
                 <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Left" />
             }
@@ -138,7 +142,11 @@
                 <Icon Name="search" Size="13" /><span class="tb-cmd-t">Find or do anything…</span><span class="kbd">@Platform.Keys.Format("Ctrl K")</span>
             </button>
             <button class="tb-icon" @onclick="ToggleTheme" title="@(Theme.Current.IsDark() ? "Switch to Cream paper" : "Switch to Night paper")" aria-label="Toggle light and dark"><Icon Name="@(Theme.Current.IsDark() ? "shift-day" : "shift-night")" Size="16" /></button>
-            @if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Right)
+            @if (Platform.Chrome.ButtonLayout is { } layoutR)
+            {
+                <WindowButtons Side="ChuvadiReader.Platform.WindowButtons.Right" Items="layoutR.Right" />
+            }
+            else if (Platform.Chrome.Buttons == ChuvadiReader.Platform.WindowButtons.Right)
             {
                 <div class="traffic">
                     <button class="tl tl-min" @onclick="() => Win.Minimize()" aria-label="Minimize"><Icon Name="minus" Size="10" /></button>
```
