# Real-Mac checks

Things CI cannot see (no screen, no trackpad, no printer, no Finder). Run them once on a real Mac
before the Mac push — on Arun's friend's Mac at the end of the programme. Tick each line, note the macOS
version and the Mac model, and attach a screenshot where it says so.

**Mac:** model ______ · chip Apple Silicon / Intel · macOS ______ · build (CI run) ______

## 0. Install and first launch
- [ ] Install the unsigned build exactly as in `README.md` → "Installing the unsigned test build". Note
      which route worked (Open Anyway / Control-click → Open / `xattr`).
- [ ] The window opens with no white flash and no native title bar; the page reaches the top edge.
- [ ] `~/Library/Logs/Chuvadi/startup.log` exists. Copy the first-launch and a second-launch line here:
      `__________________________________________`
- [ ] Quit (⌘Q) and reopen: settings (theme, interface size) are kept.

## 1. Look (compare side by side with the Windows app and the handout)
- [ ] Fonts are LiPi Sans / the handout's fonts, same weights and sizes as Windows (screenshot).
- [ ] Traffic lights on the left of the top bar, 15 px dots, 9 px apart; no second set of buttons anywhere.
- [ ] Status bar text and every shortcut label show ⌘ (not Ctrl).
- [ ] Each theme (light, dark, palm, indigo, contrast) — screenshot of Home and the Reader in light and dark.
- [ ] Interface size 100 / 125 / 150 %: everything scales together; nothing clipped.
- [ ] Retina sharpness: text and icons crisp; PDF pages crisp at 100 % and 400 %.

## 2. Window
- [ ] Drag the window by the empty top bar; drag along the very top edge (first 4 px) too.
- [ ] Double-click the empty top bar → zooms; again → back.
- [ ] Red closes, yellow minimises (Dock restores it), green zooms.
- [ ] Resize from every edge and corner; minimum size is respected; layout reflows like Windows.
- [ ] Full screen through the green button is **not** offered (expected: Immersive in the View menu, ⌃⌘F).
- [ ] View → Immersive (⌃⌘F) enters and leaves cleanly; Esc leaves it.
- [ ] Two displays: move the window across; text stays sharp on both.

## 3. Trackpad, mouse, keyboard
- [ ] Two-finger scroll in the Reader: smooth, with momentum; no rubber-banding of the whole page.
- [ ] Pinch on a page zooms the **page** (Reader zoom), not the whole app.
- [ ] Smart zoom (two-finger double-tap) does nothing to the app chrome.
- [ ] ⌘+ / ⌘− / ⌘0 zoom the page as Ctrl does on Windows.
- [ ] Mouse wheel (external mouse) scrolls; ⌘+wheel zooms the page.
- [ ] Text fields: ⌘C / ⌘V / ⌘X / ⌘A / ⌘Z work; ⌥←/→ jumps words; emoji & symbols (⌃⌘Space) insert.
- [ ] ⌘K opens "Find or do anything…"; ⌘F opens Chuvadi's Find (not a system Find bar).
- [ ] Tab moves focus in dialogs; Esc closes them.

## 4. Menu bar
- [ ] Menus: Chuvadi, File, Edit, View, Document, Window, Help. No Format menu.
- [ ] File: Open…, Close, Save, Save as, Print, Show in Finder, Copy file path, sessions — each works.
- [ ] View: Read / Mark / Arrange / Protect switch modes; view options; panels; Go to; Find or do anything.
- [ ] Document: matches the Reader's Document ▾ menu — same items, order and dividers — plus the
      Mark / Protect / Arrange / Tools submenus.
- [ ] **Live states**: with no document open, document items are greyed; open a PDF → they enable;
      switch modes → Document items change; close it → greyed again.
- [ ] Every ⌘ shortcut shown in the menu does the same as clicking the item.
- [ ] Help → search field finds a Chuvadi command by name.

## 5. Files
- [ ] File → Open: native panel, only supported types selectable; opens the file.
- [ ] Save / Save as: native panel with the name filled in; asks before replacing; the file is written.
- [ ] Choose output folder: folder panel; New Folder works.
- [ ] **Finder drop** onto the Reader page, onto Home, and onto the top bar: the document opens.
- [ ] Drop 3 PDFs while the Bench is open: all three join the shelf, in drag order.
- [ ] Drop an unsupported file (.zip): nothing happens, no error.
- [ ] Finder → right-click a PDF → Open With → Chuvadi: opens (app already running, and app not running).
- [ ] Chuvadi does **not** become the default PDF app by itself.
- [ ] Show in Finder: Finder opens with the file selected.
- [ ] Share (where the Ui offers it): the macOS share sheet appears next to the top bar; Mail attaches the file.
- [ ] A file on iCloud Drive / an external disk / a network share opens and saves.

## 6. Clipboard
- [ ] Copy text from a PDF → paste into TextEdit.
- [ ] Copy a page/region as image → paste into Preview (File → New from Clipboard): sharp, correct colours.

## 7. Printing (vector — decision D-06)
- [ ] File → Print: the macOS print panel opens with a preview of the right pages.
- [ ] Page range "3, 1": prints page 3 then page 1. "current" prints the current page.
- [ ] Password-protected PDF prints after it was opened with its password.
- [ ] **Output is vector**: Print → PDF → Save as PDF; open the result in Preview, zoom to 800 %: text and
      lines stay sharp; text is selectable.
- [ ] Filled form: field values print exactly as on screen (compare with the Windows print).
- [ ] Comments (highlights, notes, stamps, ink) print as on screen.
- [ ] Tamil / Hindi / Malayalam text in a PDF **without embedded fonts** prints with the same glyphs as on
      screen (known risk: macOS substitutes its own fonts — library ask L-1).
- [ ] A real printer (if one is available): one page in colour, one duplex.
- [ ] Cancel in the panel: no error, nothing printed.

## 8. Everything else in the Reader
- [ ] Open, read, search, Mark, Arrange, Protect, Bench, Merge, Split, Redact, Stamp, Sign — the same
      quick pass as on Windows (one document each), no errors.
- [ ] Word (.docx) and Excel (.xlsx) viewing as on Windows.
- [ ] Links in a PDF open in the default browser; mailto opens Mail.
- [ ] Certificate signing with a .pfx (needs Foundation's Mac Catalyst `IsMacOS()` fix, finding F6).

## 9. System
- [ ] Dark mode switch in System Settings while Chuvadi is open (if the theme follows the system).
- [ ] Sleep and wake with a document open: still works.
- [ ] Activity Monitor: memory after opening a 100-page PDF ______ MB; CPU idles at ~0 % when idle.
- [ ] Console.app: no repeated errors from ChuvadiReader.Mac while using it.
