# Programme status

_Last updated: 7 Nov 2026, 04:13 IST (repo and CI only: two Chrome browsers still connected with none selected, so the chats could not be read)._

**BLOCKER:** GitHub Actions on Sthraas stopped since ~01:40 IST (billing/spending limit). All chats building locally; Mac and Android cannot build/test without it. Re-checked 03:10 IST: Android dispatches at 02:47, 02:57 and 03:07 IST still refused with the same billing message; 03:17, 03:27 and 03:37 IST refused too. No new commits on any branch since 02:30 IST (chats idle, likely waiting on the coordinator).

| Chat | State |
|---|---|
| Foundation | Combined patch 3, single-instance (Windows side), legal drafts, notices contract; PR waits on Arun's GitHub verification |
| Mac | Universal app green before the block; waiting for LICENSE/EULA to embed |
| Linux | Build complete (eb65770, whole workflow green locally); Linux Test chat to open once a browser is selected |
| Android | Round 3 emulator tests ready (waits on Actions); P-06 and over-wide probe pushed |
| Web | Plan built except deployment (domain/E2E last); /terms, 12a, TEST-PLAN next |
| Mobile app UI | MU-8 screens; over-wide fix after Android probe |
| Web portal UI | Waiting on Foundation hooks H5/H6 and wording |
