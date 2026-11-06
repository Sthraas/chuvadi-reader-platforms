# Web — Sangam sign-in: how it integrates

Answers to my W-04 questions, read from `github.com/arunshivab/sangam` (read-only, tag `v1.0.0-rc.16`, commit `d43a5ff`): `src/Sangam.Client/README.md`, ADR-0003, ADR-0007, ADR-0017, `docs/pilot-guide.md`, `docs/native-and-mobile.md`, and the sample `samples/Sangam.Sample.AspNetCore`. Nothing in that repo was changed.

## Answers

| Question | Answer from the Sangam repo |
|---|---|
| Protocol | OpenID Connect, Authorization Code flow with **PKCE required for every client** (ADR-0003). The portal is a confidential client. |
| Client authentication | Client secret, or (rc.15, stronger) `private_key_jwt`: our server keeps a P-256 or RSA-3072 private key and signs a two-minute, single-use assertion; Sangam keeps only the public key. |
| Authority / discovery | `https://id.sangamid.in`; discovery `https://id.sangamid.in/.well-known/openid-configuration`; keys `https://id.sangamid.in/.well-known/jwks`. |
| Registration | Ask the Sangam team (help@sangamid.in). We get a client id (and secret, or we upload a public key on the partner console) and register `https://<portal domain>/signin-sangam` and `https://<portal domain>/signout-sangam`. Because the domain is a config value, these are set when the domain is bought. |
| Pilot | Sangam is invitation-only in the pilot. Testers are invited by e-mail or listed in `AllowedEmails`. `demo.sangamid.in` (imagiQa demo) is the first pilot app and the reference integration. |
| Scopes we would ask for | `openid profile email` (`orgs.read` only if the portal shows the organisation — 12b shows "· Records"). No `offline_access`: the portal does not need refresh tokens. |
| Claims | ID token: `sub`, `name`, `email`, `email_verified`, `sangam_orgs`. Userinfo (read fresh): profile, phone and organisations. Every token carries `acr`, `amr`, `auth_time`. |
| User id to store against | **`sub`**. Since rc.14 it is pairwise: a random UUID that is ours alone for that person and never changes (ADR-0017). Never key storage on e-mail. |
| Token lifetimes | Code 5 min; access token 1 h; ID token 1 h; refresh token 14 days sliding (only with `offline_access`); 90 days absolute. The portal's own session is a cookie whose lifetime we set. |
| Sign-out | RP-initiated logout at `/connect/endsession` (`id_token_hint`, `post_logout_redirect_uri`). The SDK maps it with `app.MapSangamSignOut()`. |
| Being told when Sangam ends the session | Back-channel logout (OIDC Back-Channel Logout 1.0): Sangam POSTs a signed `logout_token` (`typ logout+jwt`, our client id as `aud`, our `sub` and `sid`) to an address we register; retried on failure. Front-channel logout also exists, but cookies may be blocked in the frame. **Recommend back-channel**: the portal ends that user's session (and worker) on receipt. The SDK does not handle the receiving end; the portal implements one endpoint. |
| How people authenticate | Sangam's decision, not the portal's: no social sign-in; passkeys and SMS OTP. The portal never sees a password or a code. |
| Stronger sign-in before a sensitive action | `SangamStepUp.ChallengeAsync(..., SangamAcr.TwoFactor / PhishingResistant / Signature, maxAge)`. Useful later for "Sign with a certificate" (12c lists signing as Sangam-gated). |
| Language and branding of the Sangam screens | `ui_locales` (en, hi, ml) and `sangam_org` on the authorise request; branding is set on the partner console. |
| The 12a "or with your Sangam ID" field | **Not supported today.** Sangam's code and docs have no `login_hint` handling, so an ID typed on our page cannot be passed to Sangam. Options below (S-02). |

## How the portal integrates (built 6 Nov: our own code, no Microsoft sign-in package)

The portal is a confidential OpenID Connect client written in our own C# on the .NET framework only:

1. `GET /signin` → redirect to Sangam's `authorization_endpoint` (from discovery) with `response_type=code`, `client_id`, `redirect_uri=https://<portal>/signin-sangam`, `scope=openid profile email`, `state`, `nonce`, PKCE `code_challenge` (S256), optional `ui_locales`. State, nonce and verifier kept in a short-lived, encrypted, HttpOnly cookie (ASP.NET Data Protection, part of the framework).
2. `GET /signin-sangam` → check `state`; POST the code to the `token_endpoint` with the PKCE verifier and client authentication (`private_key_jwt` with an ES256 assertion signed by our key — BCL `ECDsa`; or the client secret).
3. Validate the ID token ourselves: JWS signature against Sangam's JWKS (BCL RSA/ECDsa; keys cached and refreshed on unknown `kid`), `iss`, `aud` = client id, `exp`/`iat` with small clock skew, `nonce`, algorithm allow-list (no `none`).
4. Sign the person in with the framework's cookie authentication (`__Host-` cookie, Secure, HttpOnly, SameSite=Lax), holding `sub`, `name`, `email`, `sid`, `acr`, `auth_time` and the `id_token` for sign-out.
5. `GET /signout` → end the portal session (stop the circuit/worker, delete the session folder), then RP-initiated logout at `end_session_endpoint` with `id_token_hint` and `post_logout_redirect_uri=https://<portal>/signout-sangam`.
6. `POST /backchannel-logout` → validate the `logout_token` (signature, `iss`, `aud`, `iat`, `events` contains the back-channel event, no `nonce`), then end every portal session with that `sid` (or `sub`). Answer 200.

Also: RFC 9207 `iss` on the authorization response is checked when Sangam advertises it; a revoked sign-in's cookie stops working at once (checked on every request) and every open tab of it is ended (files deleted, browser sent to `/signed-out`); logout tokens are single-use (`jti`); the portal cookie lasts at most 8 hours (D-30).

Tests: 30 in CI against `FakeSangam` (our test code: discovery, JWKS, authorize, token with PKCE and client authentication, end-session, logout tokens), covering refusals (wrong signature, `alg`, `iss`, `aud`, `azp`, nonce, expiry, replayed or wrong logout tokens, missing `iss`, open redirects). End to end against a real Sangam run locally (`tests/web-e2e/sangam_signin.py`): register a person, sign in, the Reader shows the name, cookie flags, sign-out ends a second tab too, sign in again with the password, sign out on Sangam itself → back-channel logout ends the open portal tab (1.5–4 s; 4 runs in a row).

## Found while testing against Sangam (for Sangam's team; nothing changed in Sangam)
1. **`login_hint` is not supported** (D-34: "else report"). The 12a "Sangam ID" field can't be passed on; the portal shows "Continue with Sangam" and Sangam asks for the ID.
2. **The back-channel logout address can only be set from Sangam's operator console**, not through the client configuration. Production registration must include `https://<portal>/backchannel-logout`.
3. **In Development, Sangam signs logout tokens with issuer `http://localhost/`** unless `Sangam:Issuer` is set, while discovery reports the real address; the portal (correctly) refuses those tokens. Production sets the issuer, so this matters only for local runs.

## Still open (S-02, S-03)
**S-02 The "Sangam ID" field on 12a.** (a) Show only "Continue with Sangam" and the "Download the desktop app" line — Sangam asks for the ID on its own screen; (b) keep the field and ask Sangam to support `login_hint` (a Sangam change, your decision). Recommendation: (a) for launch, which needs your approval as a small departure from 12a, and (b) as a Sangam ask.

**S-03 Registration of the portal as a Sangam client.** Needs the portal domain first (not bought): the redirect and sign-out addresses are registered with help@sangamid.in. Until then the client is built and tested against our own fake Sangam (test code); a real local Sangam (its development server, Docker and PostgreSQL, test only) can follow for an end-to-end check.
