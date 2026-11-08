# Programme status

_Last updated: 9 Nov 2026, 01:35 IST._

**All chats running in parallel (D-125, Arun).**

**Restarted 18:15–18:40 IST 8 Nov** after the usage-limit stop and paused subscription (Arun paid). All build chats running; Mac Test and Web Test chats open next.

**CI:** running again on public-repo minutes (D-93). Repo stays public until the work is complete, then private.

| Chat | State |
|---|---|
| Foundation | Eighth patch landed: platform/foundation 839d39d (green on 6); PR #11 at 50182a4 (green). Footer lines need deleting again by Arun. B-18 waits on Arun (D-121) |
| Mac | Fixing Mac Test's M-01..M-12 (crash on quit, empty menu bar, files from macOS never open, startup ~2 s gap, icon, …) |
| Linux | Rebasing onto 839d39d, full Xvfb pass, then hand head to Linux Test |
| Android | All four emulators green (rounds 6–7); fixing what Android Test finds |
| Web | Rebase, then WT-01 (CSP), WT-07/08/11–13, Sangam timeouts (D-117, D-118) |
| Mobile app UI | Handout comparison 12d–12j done (nine fixes), H-14; D-111..D-114 answered |
| Linux Test | Re-verifying Linux fixes (B-20 in progress) |
| Mac Test | Round 2 running on macOS runners; M-01..M-12 filed (⌘Tab, F11 label, quit exception, small items) |
| Web Test | Round 1 done: WT-01..WT-13 filed (BUGS.md on platform/web-test); options decided (D-117..D-119) |
| Android Test | Opened 20:58 IST (b4b95b1d), D-122 |
| Web portal UI | U-17 (b) diff ready; pushing without force (D-115) |
