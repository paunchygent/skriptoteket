---
type: story
id: ST-28-12
title: "Real standalone lifecycle and auth entry proof"
status: blocked
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
epic: "EPIC-28"
acceptance_criteria:
  - "Given `PR-0260` or HuleEdu `TASK-0327` is not done, when this story is scheduled for implementation, then it remains blocked until local role bootstrap and provider lifecycle routes are available."
  - "Given a real controlled account is used, when the user creates an account for Skriptoteket, then HuleEdu owns registration, verification, password storage, and browser session creation."
  - "Given the account is verified, when the user returns to Skriptoteket, then the app resolves or creates the local projection and opens the intended route without local browser-auth endpoints."
  - "Given the user has forgotten the password, when they use the reset affordance, then HuleEdu owns the email/reset flow and Skriptoteket only preserves safe app continuation."
  - "Given the user clicks login, create account, forgot password, verification, or reset links from Skriptoteket or email, when the browser opens the target, then the first interactive page is the exact action page and not a generic HuleEdu landing or chooser step."
  - "Given signed-out users reach the auth entry page, when they choose to sign in, create an account, or reset a password, then the copy speaks in user terms and does not expose provider internals."
  - "Given final proof is retained, when operators review it, then register, verify, login, forgot-password, reset, projection, local role, and redirect behavior are all covered with sanitized evidence."
ui_impact: "Auth entry affordances become ready for real users."
dependencies: ["ADR-0083", "ST-28-08", "ST-28-09", "ST-28-11", "HuleEdu TASK-0327", "REV-TASK-0327-01"]
---

## Context

The previous planning treated standalone registration/password lifecycle as a
provider contract. That remains true, but the launch-critical proof now needs a
complete user-facing path: a real controlled account creates an account, verifies
email, logs in, resets a password, and lands back in Skriptoteket with the right
local projection and role.

This is not a bulk migration story. It is the proof that new real users can use
the HuleEdu-owned identity lifecycle and still arrive in Skriptoteket as local
Skriptoteket users.

## Notes

- The final UI should say what the user is trying to do: sign in, create an
  account, reset a password, continue to Skriptoteket.
- Direct-action links are canonical. A clicked link must take the user straight
  to the page where that action is performed: login to login, create account to
  registration, forgot password to reset request, verification email to
  verification, and reset email to password reset.
- HuleEdu landing pages, chooser pages, or extra "click login/register again"
  steps are not acceptable on canonical links. They may exist only as fallback
  recovery for interruptions, expired links, or invalid contexts.
- Avoid wording that describes implementation internals such as provider
  ceremony, realm mismatch, projection, bootstrap, or Smart needing to restart.
- HuleEdu `TASK-0327` owns the provider-side real-inbox lifecycle proof.
- Do not implement `PR-0261` or `PR-0262` until `PR-0260` has created the local
  projection/role matrix and HuleEdu `TASK-0327` has implemented the
  direct-action lifecycle route matrix. `PR-0261` must consume that implemented
  matrix and update its local table if any path, required field, or token rule
  changes.
- Skriptoteket `PR-0261` owns the auth-entry UI and redirect contract.
- Skriptoteket `PR-0262` owns retained end-to-end proof and runbook evidence.
