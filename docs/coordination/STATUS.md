# Programme status

_Last updated: 9 Nov 2026, 06:12 IST. **PR #11 merged into chuvadi-reader main (2b8899d).**_

**All chats running in parallel (D-125, Arun).**

**Restarted 18:15–18:40 IST 8 Nov** after the usage-limit stop and paused subscription (Arun paid). All build chats running; Mac Test and Web Test chats open next.

**CI:** running again on public-repo minutes (D-93). Repo stays public until the work is complete, then private.

> 9 Nov 20:25 IST: the usage limit has reset and Reader repo access is back. PR #12 has been moved to 58909d7 (Foundation part 4, P-08); CI is green on Windows, Ubuntu, macOS and the linux-x64 trimmed launch. All chats restarted with their next steps (D-148 to D-151). 21:00 IST: the usage limit hit again; only Foundation, Linux, Linux Test and Mac Test keep running until Arun picks the plan. 21:25 IST: thirteenth patch part 1 (7d1ac03); PR #12 fast-forwarded to 1e4e365; AT-13 D-152.

| Chat | State |
|---|---|
| Foundation | platform/foundation 022b7c0: twelfth patch (pdf 3.32.0, W-01, W-02, H-17..H-19, notices) + AT-03 typed registrations. PR #12 (cc6b653) green, waits for Arun. Next: P-08 from Android 4260ca4 |
| Mac | Rebasing onto 022b7c0 and checking the trimmed Mac Catalyst Release launch (9 Nov 07:30 IST) |
| Linux | Rebasing onto 022b7c0 (not waiting for main), then hand to Linux Test for B-24/B-08b/B-26 |
| Android | 4260ca4: AT-02, AT-07 (P-08 patch for Foundation), AT-08; rebasing onto 022b7c0 and running emulators incl. Release launch |
| Web | Rebasing onto 022b7c0 for pdf 3.32.0 (LIB-1) and WT-17 |
| Mobile app UI | Rebasing onto 022b7c0; checking TOOLS/Mark rails against desktop, then drop tablet Save pin |
| Linux Test | Waiting for Linux head on 022b7c0 to re-verify B-24, B-08b, B-26; open: library items, B-27, real-machine checks |
| Mac Test | Long re-verify of M-01..M-16 running (~2h45m); then trimmed Release check |
| Web Test | Waiting for Web on pdf 3.32.0 (LIB-1, WT-17); staging VM items and manual checks for a person |
| Android Test | Round 4 running (incl. same-file-opened-twice vs Windows) |
| Web portal UI | Rebasing onto 022b7c0; standing by for WT-03..WT-06 |
