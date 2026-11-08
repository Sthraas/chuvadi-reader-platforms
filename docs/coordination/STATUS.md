# Programme status

_Last updated: 8 Nov 2026, 18:20 IST._

**Restarted 18:15 IST 8 Nov** after the usage-limit stop and paused subscription (7 to 8 Nov; Arun paid). Staggered restart: Foundation, Linux, Linux Test, Android now; Web, Mobile UI and Web portal UI at the next check-in; then the Mac Test chat.

**CI:** running again on public-repo minutes (D-93). Repo stays public until the work is complete, then private.

| Chat | State |
|---|---|
| Foundation | PR #11 green on a12b14e; next combined patch: Mobile UI H-5..H-12 + PhoneShell slot, Web UI H5/H6, touch wording (D-94, D-96); then update PR |
| Mac | Done: legal texts embedded and verified on runner; Mac workflows manual-only; pushed 7a65178. Waiting for the friend's Mac (REAL-MAC-CHECKS.md). Mac Test chat next |
| Linux | Build complete (D-92); ARM64 rerun; fixing GNOME close-only button layout bug (min/max still shown) |
| Android | Round 3 running (one run, 8acce05) |
| Web | D-86 (/terms, /privacy, 12a-ready, TEST-PLAN) and D-89 DropFiles=false; resent 05:50 |
| Mobile app UI | CI green; H-12 approved (sample data bug); next: gesture bugs |
| Linux Test | Running T1 (build and package) and T2 (startup timing); sandbox tips from Linux chat to relay |
| Web portal UI | U-15 = footer line (D-97); waits on Foundation for PhoneShell slot, H5, H6, drop overlay |
