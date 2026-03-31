---
type: story
id: ST-02-10
title: "Recovery email hardening and verification resend discoverability"
status: done
owners: "agents"
created: 2026-03-30
updated: 2026-03-31
epic: "EPIC-02"
acceptance_criteria:
  - "Given a verified local account requests `Glömt lösenord`, when the app renders and sends the reset email, then the reset template satisfies the email renderer contract and a password-reset token can result in a real outbound email attempt instead of failing before send."
  - "Given a user opens the verification email in common mail clients, when remote images/scripts are blocked or unsupported, then the email still renders cleanly without a broken header image placeholder."
  - "Given an overifierat local account needs help after registration, when the user is on `Glömt lösenord` or has just failed login with `EMAIL_NOT_VERIFIED`, then the UI offers a clear way to request a new verification email without requiring the original verification link."
  - "Given a user requests a new verification email from those recovery surfaces, when they repeat the action during the cooldown window, then the backend remains authoritative with the existing generic-success and rate-limited resend behavior."
dependencies: ["ST-02-03", "ST-02-07"]
ui_impact: "Updates the anonymous auth recovery flow and login modal so unverified local users can discover the existing resend-verification path."
data_impact: "No schema change."
---

## Context

Production investigation on `2026-03-30` showed two separate trust problems in the current account-
recovery experience:

1. `forgot-password` for a verified local user created a `password_reset_tokens` row but did not
   send any email because `reset_password.html` failed the template-renderer contract (`missing
   subject comment`).
2. The verification email currently includes a header image resource that breaks in common email
   clients and adds noise to an otherwise working verification flow.

Separately, the backend already supports anonymous `resend-verification` with generic success and a
cooldown, but that path is too hidden when a user lands in `Glömt lösenord` or enters correct
credentials for an account that still is not verified.

## Implementation notes

### Recovery email robustness

- Add the required subject comment to `reset_password.html` so the existing template renderer can
  build a message instead of raising before SMTP send.
- Keep the reset email otherwise simple and client-safe; prefer plain HTML with a copyable fallback
  URL over decorative assets.

### Verification email client compatibility

- Remove the header logo/image resource from `verify_email.html`.
- Do not replace it with another remote image, background image, or script-dependent element.
- Keep the email readable when clients block external assets entirely.

### Verification resend discoverability

- Reuse the existing `POST /api/v1/auth/resend-verification` contract; do not create a second
  resend endpoint.
- Surface a resend-verification affordance from:
  - `ForgotPasswordView.vue`
  - the login modal when login fails with `EMAIL_NOT_VERIFIED`
- Reuse the current email input where possible so the user does not need to retype the address.
- Keep backend anonymity/cooldown authoritative; frontend affordances may add light guidance or
  disable-state polish, but must not invent a stricter truth model than the handler.

### Verification

- Frontend tests for forgot-password and login-modal resend affordances.
- Backend/unit coverage if any email-template contract logic changes beyond copy/template content.
- Manual proof on local dev:
  - request password reset for a verified local user and confirm the app no longer logs a template-
    render failure before send
  - open the verification email HTML in a mail-client-like environment and confirm no broken header
    image remains
  - from `Glömt lösenord`, request a new verification email for an overifierat account and confirm
    the generic success guidance appears
  - trigger `EMAIL_NOT_VERIFIED` in the login modal and confirm the resend affordance appears and
    can be used

## Linked tasks

- Primary implementation slice:
  `docs/backlog/prs/pr-0174-recovery-email-hardening-and-verification-resend-discoverability.md`
- Review remediation:
  `docs/backlog/prs/pr-0176-review-remediation-for-recovery-email-hardening-and-resend-verification-ux.md`

## Implementation Summary (as of 2026-03-31)

- `PR-0174` fixed the reset email template contract, removed the broken verification-email image
  dependency, and exposed resend-verification from both `Glömt lösenord` and the
  `EMAIL_NOT_VERIFIED` login path.
- `PR-0176` completed the follow-up review remediation by removing frontend-only resend cooldown
  truth, mapping `EMAIL_NOT_VERIFIED` to the intended auth status, and recording a rerunnable live
  proof script.
- Local verification now includes focused backend/frontend regression runs plus
  `pdm run python -m scripts.playwright_pr_0176_auth_recovery_check --base-url http://127.0.0.1:5173`
  with artifacts under `.artifacts/pr-0176-auth-recovery-check/`.
