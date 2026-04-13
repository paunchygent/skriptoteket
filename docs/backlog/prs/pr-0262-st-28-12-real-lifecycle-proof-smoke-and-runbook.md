---
type: pr
id: PR-0262
title: "ST-28-12 real lifecycle proof smoke and runbook"
status: blocked
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
stories:
  - "ST-28-12"
adrs:
  - "ADR-0083"
dependencies:
  - "PR-0260"
  - "PR-0261"
  - "REV-PR-0260"
  - "REV-PR-0261"
  - "HuleEdu TASK-0326"
  - "HuleEdu TASK-0327"
  - "REV-TASK-0326-01"
  - "REV-TASK-0327-01"
tags: ["auth", "playwright", "runbook", "lifecycle", "email"]
acceptance_criteria:
  - "Given approved `REV-TASK-0326-01`, `REV-TASK-0327-01`, `REV-PR-0260`, and `REV-PR-0261`, when this proof is implemented, then it consumes their exact accepted subject-export, role-matrix, action-route, and URL contracts without inventing local variants."
  - "Given a controlled real inbox account, when the retained proof runs, then it covers create account, verify email, login, forgot-password, reset-password, app continuation, projection resolution, and local role observation through the accepted contracts."
  - "Given lifecycle links are clicked from the product or email, when the browser reaches HuleEdu, then the first interactive page is the exact action page requested by the accepted route matrix."
  - "Given the lifecycle session returns to Skriptoteket, when projection proof is retained, then it asserts `active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`, nonblank `realm_subject_id`, provider-owned email, `email_verified=true`, the matching local `identity_projection`, and the expected local `User.role` from `PR-0260`."
  - "Given the proof produces artifacts, when they are retained, then they include the required manifest fields and sanitized evidence without credentials, verification tokens, reset tokens, session cookies, raw magic links, or raw signed identity payloads."
  - "Given dev and production use different infrastructure, when operators follow the runbook, then the same conceptual proof model works for both without rewriting repo code."
  - "Given the proof role matrix from `PR-0260` exists, when lifecycle proof completes, then `PR-0254` can consume the same accounts for final cross-app auth cutover smoke."
---

## Problem

The app needs proof that a real user can go through the full standalone account
lifecycle and arrive in Skriptoteket. Unit tests and provider-only checks do not
show the browser, email, projection, and local role behavior together.

## Goal

Add a retained lifecycle proof lane and runbook that operators can run before
the final cross-app `PR-0254` smoke.

## Non-goals

- Implementing the provider lifecycle; that belongs to HuleEdu `TASK-0327`.
- Reworking the auth-entry UI; that belongs to `PR-0261`.
- Bulk importing old Skriptoteket alpha users.
- Making production probes send mail without an explicit operator action.

## Prerequisite Gate

Implementation must not start until these prerequisite slices are implemented
and their retained reviews are approved:

- HuleEdu `REV-TASK-0326-01`, which freezes the sanitized proof subject export.
- HuleEdu `REV-TASK-0327-01`, which freezes the real-inbox lifecycle and direct-action route
  matrix.
- Skriptoteket `REV-PR-0260`, which freezes the local role matrix and projection bootstrap
  consumer contract.
- Skriptoteket `REV-PR-0261`, which freezes the Skriptoteket auth-entry URL builder and
  direct-action continuation contract.
- HuleEdu `TASK-0327` done, so the lifecycle/direct-action routes exist.
- Skriptoteket `PR-0260` done, so the proof role matrix and local projections exist.
- Skriptoteket `PR-0261` done, so product links target the accepted HuleEdu action routes.

After approval, this PR must consume the exact accepted contracts. If any approved upstream review
renames fields, changes URL paths, changes token handling, or changes the local role-matrix key,
update this PR before adding the smoke command or runbook.

## Proof Assertions

The lifecycle proof must retain decoded and sanitized assertions only. It must not retain raw
signed identity payloads.

For each controlled account, the Playwright/operator smoke must prove:

- browser lifecycle coverage for register, email verification, login, forgot-password request, and
  password-reset completion through the accepted HuleEdu route matrix
- direct first interactive page for product-originating login, create-account, and forgot-password
  links
- direct first interactive page for email-originating verification and password-reset completion
  links without retaining the raw URLs
- callback continuation to the intended Skriptoteket route
- shared-session bootstrap using `active_app=skriptoteket`
- `active_product_identity_realm=skriptoteket_standalone`
- nonblank `realm_subject_id`
- provider-owned account email and `email_verified=true`
- local `identity_projection` keyed by
  `(active_product_identity_realm, realm_subject_id)`
- local `User.role` matching the accepted `PR-0260` role matrix for the controlled-account key

The focused backend helper tests must fail if callback/projection resolution succeeds by email
alone, by an unsupported realm, by a blank realm subject, or by a local role that was not assigned
from the accepted `PR-0260` role matrix.

## Artifact Manifest Contract

Default retained local artifacts live under:

```text
.artifacts/playwright-pr-0262-real-lifecycle/<environment>/<run-id>/
```

The manifest filename is `manifest.redacted.json`. Each manifest must include:

- `command`
- `environment` (`local-nonprod` or `production`)
- `timestamp_utc`
- `accepted_contracts` (`REV-TASK-0326-01`, `REV-TASK-0327-01`, `REV-PR-0260`,
  `REV-PR-0261`)
- `app` (`skriptoteket`)
- `product_identity_realm` (`skriptoteket_standalone`)
- `controlled_account_key`
- `action_page_assertions` for login, register, password-reset request, password-reset
  completion, and email verification
- `redacted_email_link_evidence` recording link kind, target action, first interactive page, and
  `raw_url_retained=false`
- `callback_assertions`
- `projection_assertions`
- `local_role_assertions`
- `screenshots` and `logs` paths, if retained
- `redaction_checks` with an explicit pass/fail result

Allowed evidence types are sanitized screenshots, browser event summaries, route/action names,
HTTP status summaries, redacted log excerpts, and decoded non-secret assertion summaries.

Forbidden fields are credentials, session cookies, CSRF tokens, verification tokens, reset tokens,
raw magic links, raw email bodies containing action links, raw signed identity payloads, and
unredacted provider headers.

## Implementation Plan

1. Define the controlled-account proof inputs and artifact directory for dev
   and production runs using the manifest contract above.
2. Inspect the closest existing proof scripts before implementation:
   `scripts/playwright_pr_0254_auth_cutover.py`, `scripts/playwright_pr_0257_auth_lifecycle.py`,
   and `scripts/playwright_pr_0258_auth_projection.py`.
3. Add `scripts/playwright_pr_0262_real_lifecycle.py` plus a
   `pdm run pr-0262-real-lifecycle` wrapper that invokes
   `python -m scripts.playwright_pr_0262_real_lifecycle`.
4. Drive the browser through HuleEdu-owned register, verify, login, forgot-password, and reset
   flows, using only the approved `TASK-0327` / `PR-0261` app, realm, callback, `return_to`,
   `next`, and token-handling contract.
5. Assert that each clicked product/email lifecycle link lands directly on the
   requested action page with no generic HuleEdu interstitial.
6. Verify Skriptoteket callback, shared-session bootstrap, realm-aware projection resolution, and
   local role visibility with the assertion contract above.
7. Add redaction tests or artifact-inspection checks for `manifest.redacted.json`, retained logs,
   and retained screenshots.
8. Update the operator runbook with dev/prod commands, prerequisites, expected evidence, failure
   interpretation, redaction rules, and handoff to `PR-0254`.

## Runbook Verification Gates

The runbook must name these commands before this PR can close:

```bash
pdm run pr-0262-real-lifecycle --environment local-nonprod --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod
pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py tests/unit/web/test_profile_app_continuation_api.py
pdm run typecheck
pdm run lint
pdm run fe-type-check
pdm run docs-validate
git diff --check
```

If frontend proof helpers or auth-entry URL helpers change, add the focused Vitest command for
those files beside `pdm run fe-type-check`. If no frontend files change, record that
`pdm run fe-type-check` is the frontend close-out gate.

The local non-production lane is the HuleEdu `TASK-0325` shared-auth setup: Skriptoteket SPA at
`http://localhost:5173`, HuleEdu Gateway at `http://localhost:8080`, and HuleEdu
login/lifecycle UI at `http://localhost:5174`, with protected Skriptoteket API traffic entering
through the Gateway.

Failure triage must preserve these interpretations:

- generic HuleEdu landing for a deliberate action link is a `TASK-0327` / `PR-0261` route-matrix
  failure, not a successful proof
- callback success without the accepted app/realm/subject assertions is a `PR-0260` /
  continuation contract failure
- local role mismatch is a `PR-0260` role-matrix failure
- artifact redaction failure invalidates the smoke even if browser actions succeeded

## Test Plan

- Run the focused backend helper tests named in the runbook verification gates.
- Run any focused frontend tests for changed auth-entry or proof helpers.
- Run `pdm run pr-0262-real-lifecycle --environment local-nonprod --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod`.
- Run `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`, `pdm run docs-validate`, and
  `git diff --check`.
- Inspect `manifest.redacted.json` and retained artifact paths for forbidden fields before
  requesting re-review.
- Run production proof only with explicit operator credentials and record the sanitized artifact
  path in `.agents/handoff.md`.

## Rollback Plan

Remove the proof command/runbook additions if they encode an incorrect lifecycle
contract. Keep `ST-28-12` open until real-account proof is available.
