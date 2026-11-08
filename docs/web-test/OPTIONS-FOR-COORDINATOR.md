# Web Test — options and questions for the coordinator (session 1, 8 Nov 2026)

## O-1 How long a person waits when Sangam is slow (G-9)
Measured: 60.05 s before "Sangam can't be reached right now."
- (a) Keep 60 s. Pros: nothing to change; survives a very slow Sangam. Cons: a minute of a blank tab looks broken; people retry and pile up requests.
- (b) 10 s timeout for discovery and the token call. Pros: a clear answer within 10 s; Sangam answers in well under a second when healthy. Cons: a Sangam that is slow but working (10–60 s) now fails sign-in.
**Recommendation: (b).** Owner: Web.

## O-2 Sangam down while discovery is cached (G-1 warm)
A portal that has already read Sangam's discovery sends the browser straight to Sangam, so a down Sangam shows the browser's own "can't connect" page instead of ours.
- (a) Accept. Pros: no extra request; the cold case is already correct. Cons: the person leaves Chuvadi to an error page.
- (b) Before redirecting, the portal checks Sangam (a quick request to discovery, 2 s limit, the result cached for 30 s). Pros: our message in both cases. Cons: ~one extra small request per 30 s; a few ms on sign-in.
**Recommendation: (b).** Owner: Web.

## WT-05 12a pitch "encrypted at rest"
Options and recommendation in `BUGS.md` WT-05. **Recommendation: (a)** "kept in memory only", in line with D-98.

## Q-3 Home's "Storage map" and "Your shelves" on the portal
With no server storage this release (D-31 scope), Home still shows a Storage map (Finance, Legal, Clinical… "0 docs · 0 B") and "Your shelves are empty — open the Library". They describe this session's files only and are empty at every sign-in.
- (a) Keep as is. Pros: same Home as the desktop (rule 1). Cons: reads as storage the portal doesn't offer.
- (b) Hide them when `Kind == Web` (Web portal UI component hook). Pros: no implied storage. Cons: a portal-only difference and another hook.
- (c) Keep them, with the Web wording already used elsewhere ("this session").
**Recommendation: (c)** if the Web portal UI chat confirms it needs no layout change; otherwise (a). Your call.

## Q-4 Order of re-testing
WT-03, WT-04, WT-06 all clear when `platform/web` rebases on Foundation ≥ 584bbf2 plus the Web portal UI's 5bec046 files. Suggest the Web chat does that rebase first, then WT-01, WT-07, WT-08, WT-11…WT-13; WT-02, WT-09, WT-10 go to Arun as listed changes.
