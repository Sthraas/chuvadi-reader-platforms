# Manual checks — a short script for a person (M-1 to M-4, G-12)

For anyone with the device in hand; ~20 minutes per device. Use the staging address `https://<staging domain>` and the Sangam test person P1 (P2 for G-12). Test files: `text-13.pdf` (pages headed "Page N of 13"), `form.pdf`, `no-print.pdf`, `fid.xlsx` — ask the Web Test chat for the folder. Write ✓ or ✗ beside each step; for ✗ add a screenshot and one line of what happened.

## The same 12 steps on every device
1. Open the address. The sign-in page shows "Continue with Sangam" (no password box). Check it in **light and dark** mode (device setting).
2. Tap **Terms of use** and **Privacy** before signing in — both open.
3. **Continue with Sangam** → sign in as P1 → you come back signed in; your name is on the account button.
4. **Upload** `text-13.pdf` (on phones: from Files, then again from Photos/Drive where offered). Page 1 shows.
5. Go to page 5 → **Print** → **Current page** → the printed/preview page says "Page 5 of 13".
6. Upload `no-print.pdf` → Print: the card says the file doesn't allow printing.
7. **Mark**: draw a rectangle → **Save as new PDF** → the file downloads (note where it lands) and opens with the rectangle.
8. **Document ▾ → Split** the 13-page file → **one .zip** downloads (no "download multiple files" prompt).
9. Upload `fid.xlsx` → the grid shows; the "Two  spaces here" cell keeps its two spaces.
10. Account button → menu ends with **Terms of use · Privacy**; status bar says "kept in memory only".
11. **Sign out** → you land on "signed out"; pressing Back doesn't show your file.
12. Sign in again → your earlier file is **not** there (session files are gone).

## Device-specific checks
### M-1 — Windows 11, current Edge
- Shortcuts read **Ctrl** (Ctrl P, Ctrl F) and work.
- Step 5: Edge's own PDF viewer prints the right page.
- Step 7/8: the downloads bar shows the file/zip.

### M-2 — Mac, macOS 15+, current Safari
- Shortcuts read **⌘** (⌘P, ⌘F) and work.
- Step 5: the print link opens a PDF tab; ⌘P there prints it.
- Copy an image from a page: Safari asks permission first.
- Step 1 in light and dark (System Settings → Appearance).

### M-3 — iPhone and iPad, iOS/iPadOS 18+, Safari
- iPhone: **phone layout** (bottom bar Read · Mark · Arrange · Protect). iPad: tablet layout in **both orientations**.
- Step 4 from **Files** and from **Photos**.
- Step 5: print via the PDF tab's **share sheet**.
- Step 7/8: downloads land in **Files**.
- Touch: select text, draw a mark with a finger; **double-tap doesn't zoom the page**.

### M-4 — Android 14+, current Chrome
- **Phone layout** as above.
- Step 4 from the device and from **Drive**.
- Step 5: print via the PDF tab.
- Step 7/8: downloads appear in Chrome's downloads.
- The phone's **Back button** inside the Reader doesn't sign you out or lose the open file.

## G-12 — person in two organisations (any one browser)
1. Sign in as **P2**. Sangam shows its **organisation chooser** (expected).
2. Pick organisation **A** → the portal's account menu shows A.
3. Sign out, sign in as P2 again, pick **B** → the menu shows B.
4. ✗ if no chooser appears, or the menu shows the wrong organisation.

## Hand back
Send the ✓/✗ list per device with screenshots of any ✗. The Web Test chat adds them to `RESULTS.md` (M-1…M-4, G-12) and files any bug.
