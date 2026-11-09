# Programme status

_Last updated: 9 Nov 2026, 06:12 IST. **PR #11 merged into chuvadi-reader main (2b8899d).**_

**All chats running in parallel (D-125, Arun).**

**Restarted 18:15–18:40 IST 8 Nov** after the usage-limit stop and paused subscription (Arun paid). All build chats running; Mac Test and Web Test chats open next.

**CI:** running again on public-repo minutes (D-93). Repo stays public until the work is complete, then private.

> 9 Nov 20:25 IST: the usage limit has reset and Reader repo access is back. PR #12 has been moved to 58909d7 (Foundation part 4, P-08); CI is green on Windows, Ubuntu, macOS and the linux-x64 trimmed launch. All chats restarted with their next steps (D-148 to D-151). 21:00 IST: the usage limit hit again; only Foundation, Linux, Linux Test and Mac Test keep running until Arun picks the plan. 21:25 IST: thirteenth patch part 1 (7d1ac03); PR #12 fast-forwarded to 1e4e365; AT-13 D-152.

| Chat | State |
|---|---|
| Foundation | platform/foundation-pr 556090b (fourteenth patch, D-152). PR #12 at 556090b, 5/5 green after one osx-arm64 hang (being looked at). Next: H-20 (Mobile UI, D-151) |
| Mac | Rebasing onto 022b7c0 and checking the trimmed Mac Catalyst Release launch (9 Nov 07:30 IST) |
| Linux | 7595ef3: thirteenth patch merged, 118/118 build-log steps; ready for Arun |
| Android | 4260ca4: AT-02, AT-07 (P-08 patch for Foundation), AT-08; rebasing onto 022b7c0 and running emulators incl. Release launch |
| Web | Rebasing onto 022b7c0 for pdf 3.32.0 (LIB-1) and WT-17 |
| Mobile app UI | Rebasing onto 022b7c0; checking TOOLS/Mark rails against desktop, then drop tablet Save pin |
| Linux Test | **Linux 7595ef3 verified ready for Arun's check** (9 Nov 22:00 IST): every Linux and shared bug fixed except B-26 (deferred by D-147); open elsewhere: library B-08a, B-09a, B-27; Reader chat collapse button; Windows timings; six real-machine checks |
| Mac Test | Long re-verify of M-01..M-16 running (~2h45m); then trimmed Release check |
| Web Test | Waiting for Web on pdf 3.32.0 (LIB-1, WT-17); staging VM items and manual checks for a person |
| Android Test | Round 4 running (incl. same-file-opened-twice vs Windows) |
| Web portal UI | Rebasing onto 022b7c0; standing by for WT-03..WT-06 |
