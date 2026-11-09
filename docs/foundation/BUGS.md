# Foundation bug list (D-142)

Bugs found in Arun's Windows checks, fixed for the next PR. Each has a test, and is retested on Windows by Arun when the PR lands.

| # | Sev | Bug | Already in main before our patches? | Status |
|---|---|---|---|---|
| W-01 | S2 | Title-bar drag and double-click to maximise work only on the Chuvadi logo area, not the empty centre of the top bar | **Yes**, identical in chuvadi-reader main c7b9e44 | Fixed (twelfth patch); test passes; awaiting Arun's Windows retest |
| W-02 | S2 | Dragging a file into the app window does nothing | **Yes**: the drop mechanism is unchanged since c7b9e44 (we changed only where files go after a drop) | Fixed (twelfth patch); page-side test passes; host side awaiting Arun's Windows retest |

## W-01 — the top bar's empty middle doesn't move the window
**Cause:**
- The top bar moves the window from its own mouse-down (`StartDrag`). Two press = maximise.
- But `.tb-mid` (the centre) and `.tb-right` (the right group) stopped the mouse-down on their **whole box**, empty space included.
- `.tb-right` stretches into the centre column, so the empty middle of the bar was its leading space. Only the brand cell's surroundings dragged.
- Identical markup in main c7b9e44.

**Fix:**
- The press-stopping moves onto a wrapper around the controls (`<span class="tb-ctl">`).
- The wrapper is `display: contents`, so it draws no box and the layout doesn't change (Windows screens 27/27 identical).
- Empty space now belongs to the containers and reaches `StartDrag`.

**Test:** `tools/PixelProof/titlebar-drag.js` against the desktop preview, which records the window calls it receives (`PreviewWindowControls`, `/__preview/window-log`).

| Check | Before (eb74e52) | After |
|---|---|---|
| Empty middle of the bar drags | FAIL (no drag) | PASS |
| Empty space around the brand drags | PASS | PASS |
| Search box doesn't drag | PASS | PASS |
| Page number doesn't drag | PASS | PASS |
| Brand doesn't drag | PASS | PASS |
| Double press on the empty middle maximises | FAIL | PASS |

A scan across the bar at 1440 px shows every empty stretch now drags, and every control keeps its press.

**Retest on Windows (Arun):**
1. Drag the window by the empty middle of the top bar. It moves.
2. Double-click there. It maximises; double-click again to restore.
3. Click the search box, the page number, the tabs and the window buttons. Each does its own job, not a drag.

## W-02 — dropping a file on the window does nothing
**Cause:**
- The Windows host turned off WebView2's own drop handling (`AllowExternalDrop = false`), expecting the WPF window's `Drop` event to fire instead.
- But WebView2 is a native child window covering almost all of the client area, and WPF drop events don't pass through it.
- So `Drop` could fire only on the window's edges, and a drop on the page did nothing.
- Unchanged since main c7b9e44. Our patches changed only where the files go after a drop: the shared router, so the Bench shelf when it's open, otherwise a Reader tab each.

**Fix (WebView2's own mechanism for dropped files):**
- WebView2's drop handling stays on.
- `ChuvadiReader.Ui/wwwroot/js/host-drop.js`, loaded only by the Windows host, accepts file drags on the page. It hands dropped `File` objects to the host with `chrome.webview.postMessageWithAdditionalObjects('chvd:files-dropped', files)`.
- The host (`MainWindow.OnWebMessageReceived`) reads each `CoreWebView2File.Path`; this needs WebView2 SDK 1.0.1774 or later, and the host has 1.0.3179.45.
- It then sends the files to the same router as before.
- Drops a component already handled (an image onto a page in Mark mode) are left alone.
- The window's own `Drop` stays for the window edges.

**Test:** `tools/PixelProof/host-drop.js` in the desktop preview, with a stand-in for `chrome.webview`, passes 5 of 5:
- a file drag is accepted, so the browser won't open the file itself;
- dropped files reach the host with their names;
- a drop already taken by a component is left alone;
- a drag without files is left alone;
- a drop without files sends nothing.

The last step, WebView2 turning `File` objects into paths, exists only in WebView2 on Windows.

**Retest on Windows (Arun):**
1. Drag a PDF from Explorer onto the middle of the window (Home). It opens in a tab.
2. Drag two files. Each opens in its own tab.
3. With Arrange open, drop a PDF. It joins the shelf.
4. In Mark mode, drag an image onto a page. It's placed on the page, not opened.
5. Drag a .exe. Nothing opens.
