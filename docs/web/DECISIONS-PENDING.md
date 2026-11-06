# Web — decisions

Kept by the Web chat. "Decided" items record who decided and when; "Open" items carry options, pros and cons and a recommendation for the coordinator to finalise.

## Decided

| # | Decision | By, when |
|---|---|---|
| W-01 | **No server storage** this release. Files live only for the session; Save / Save as deliver a browser download. Dropped: My files, quota, "autosaved to your storage", storage in the account menu. | Arun, 6 Nov |
| W-03 | TLS: Pezhai can't issue browser-trusted certificates, so **our own C# ACME client for Let's Encrypt** (no externals), automatic renewal, hot reload in Kestrel (pluggable source already built). Storing the certificate in Pezhai as a secret: maybe later. | Arun, 6 Nov |
| — | Domain will likely be **chuvadi.in**; it stays a config value. | Arun, 6 Nov |
| — | Sangam client registration when Sangam goes to production; until then integrate and test against Sangam run locally from `arunshivab/sangam` (read-only) or its demo setup. Issuer, client id and redirect URLs are config. | Arun, 6 Nov |
| — | E2E deployment is the **last** step: build and test everything first; keep the runbook ready. | Arun, 6 Nov |
| W-04 / S-01 | Sangam sign-in with **our own OpenID Connect client code**; no Microsoft sign-in package; Sangam repo read-only. Protocol facts: `SANGAM-INTEGRATION.md`. | Arun, 6 Nov |
| W-06 | Packages come from the Reader's committed `ci/packages` feed (byte-identical to what Windows ships). | Coordinator, 6 Nov |
| W-07 | No sharing ("Shared with me", "Share a link") this release. | Arun, 6 Nov |
| — | File model: session-only **encrypted** working copies, deleted on sign-out, session end or expiry. | Coordinator (Foundation), 6 Nov |
| — | Web printing = the browser printing the PDF (built). | Coordinator, 6 Nov |
| — | Portal look (sign-in page, account menu, status bar, gating) moves to the Web portal UI chat; this chat integrates its components from `platform/web-ui`. | Coordinator, 6 Nov |
| — | Rebase on `platform/foundation` when its Group A lands. | Coordinator, 6 Nov |

## Open

### W-02 Isolation: per-person worker vs shared process
Full pros, cons and measurements: `ISOLATION-DECISION.md`. Recommendation: per-person workers.

### W-05 Existing-file hooks
The earlier H0–H9 proposal is withdrawn in favour of the Foundation's groups. Remaining gaps G1–G4: `WEB-GAPS-AFTER-FOUNDATION.md`.

### W-08 Signing certificates uploaded to the server
The Reader's "Sign with a certificate" asks for a `.pfx`/`.p12`, which contains the person's **private key**. On the portal that key would be uploaded to our server (kept only for the session). 12c lists signing as Sangam-gated.

| Option | Pros | Cons |
|---|---|---|
| (a) Off on the portal (built as the default: the picker returns nothing) | Private keys never reach the server | Signing with a certificate isn't available on the web |
| (b) Allow, session-only, deleted at session end | Feature parity with desktop | A private key on a shared server, however briefly; key handling and audit become our responsibility |
| (c) Later: Sangam's own e-signature ceremony (`/api/v1/signatures`) instead of a personal certificate | No private keys anywhere near us; Sangam already supports it | A different signing model from the desktop; needs a library/product decision |

Recommendation: (a) now, (c) as the web's signing path later.

### W-09 Encrypting the session working copies at rest
Decided above that working copies are encrypted at rest. The Reader opens files **by path**, so the host can't hand it an encrypted file without Foundation/Core changes. Options for this release:

| Option | Pros | Cons |
|---|---|---|
| (a) Data root on a LUKS-encrypted volume on the E2E VM (key unlocked at boot from a key file or Pezhai) | Transparent to the Reader; standard Linux (OS component) | Protects the disk at rest (stolen disk, snapshot, decommissioned volume), not against someone on the running server |
| (b) Data root on `tmpfs` (RAM only), with encrypted swap or no swap | Files never touch a disk; vanish on reboot; nothing to clean up after a crash | Big documents use RAM; size the VM for it |
| (c) App-level encryption with a per-session key (AES-GCM, BCL) | Each session's files unreadable without its key, even on the running server | Needs the Foundation's file model or Core to read through streams; the Reader's own temp files stay plain |

Recommendation: (b) for working copies (RAM-only, size-limited) plus (a) for anything that must touch disk, until the Foundation's file model allows (c). Waiting for the Foundation's Group A to see what it provides.

### W-10 Settings across sessions
With no server storage, each visit starts with default settings (theme, interface size, preferred name).

| Option | Pros | Cons |
|---|---|---|
| (a) Defaults every visit (built) | Nothing kept anywhere | People redo their settings each time |
| (b) Keep settings (not recents or paths) in the person's own browser storage | Remembered per browser; nothing on the server | Settings live on a shared computer's browser too; one more JS bridge |

Recommendation: (b) for appearance settings only, if the coordinator agrees.

### W-11 Session expiry
Proposed: 30 minutes idle, 8 hours absolute, then the session's files are deleted and sign-in is required again. Values needed from Arun/coordinator.
