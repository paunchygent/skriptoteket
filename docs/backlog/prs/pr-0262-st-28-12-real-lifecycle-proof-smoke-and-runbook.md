---
type: pr
id: PR-0262
title: "ST-28-12 real lifecycle proof smoke and runbook"
status: done
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
  - "Given approved `REV-TASK-0326-01`, `REV-TASK-0327-01`, `REV-PR-0260`, and `REV-PR-0261`, when this proof is implemented, then it consumes their exact accepted subject-export, role-matrix, action-route, diagnostics, and URL contracts without inventing local variants."
  - "Given HuleEdu `TASK-0327` produced the final `status=ok` live apply artifact, when the retained proof runs, then Skriptoteket validates that artifact as upstream provider evidence instead of re-driving the real-inbox lifecycle."
  - "Given the upstream artifact proves product and email lifecycle links, when Skriptoteket retains PR-0262 evidence, then it records sanitized action-page assertions for login, create account, forgot-password, reset completion, and email verification."
  - "Given the lifecycle session returns to Skriptoteket, when projection proof is retained, then it asserts `active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`, signed-context subject/email presence and match booleans, `email_verified=true`, the matching local `identity_projection`, and the expected local `User.role` from the accepted local role matrix."
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

Implementation may start now. The prerequisite slices are implemented or
accepted, and the remaining HuleEdu live-apply blocker has been resolved:

- HuleEdu `REV-TASK-0326-01`, which freezes the sanitized proof subject export.
- HuleEdu `REV-TASK-0327-01`, which freezes the real-inbox lifecycle,
  direct-action route matrix, and final sanitized diagnostics shape.
- Skriptoteket `REV-PR-0260`, which freezes the local role matrix and projection bootstrap
  consumer contract.
- Skriptoteket `REV-PR-0261`, which freezes the Skriptoteket auth-entry URL builder and
  direct-action continuation contract.
- HuleEdu `TASK-0327` done, with final retained live apply artifact:
  `/Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json`.
- Skriptoteket `PR-0260` done and accepted, so the proof role matrix and local
  projections exist.
- Skriptoteket `PR-0261` implemented and verified, so product links target the
  accepted HuleEdu action routes and the hidden consumer diagnostics probe exists.

After approval, this PR must consume the exact accepted contracts. If any approved upstream review
renames fields, changes URL paths, changes token handling, or changes the local role-matrix key,
update this PR before adding the smoke command or runbook.

## Decision: Provider Proof Consumption

`PR-0262` must not duplicate HuleEdu's provider-owned real-inbox runner. The
provider lifecycle proof now lives in the HuleEdu `TASK-0327` artifact. This PR
validates that artifact and then proves the Skriptoteket-owned half of the
chain: callback continuation, signed-context diagnostics, local projection, and
local role observation.

The accepted diagnostics shape is sanitized. Retained Skriptoteket artifacts
may assert presence and equality booleans such as
`realm_subject_id_present`, `email_present`, `subject_matches_realm_subject`,
and `linked_identity_matches_realm_subject`. They must not require or retain raw
signed-context email, raw `realm_subject_id`, raw HuleEdu signed headers, JWT or
signature material, cookies, CSRF, reset tokens, verification tokens, or raw
magic links.

## Proof Assertions

The lifecycle proof must retain decoded and sanitized assertions only. It must not retain raw
signed identity payloads.

The upstream HuleEdu artifact must prove:

- `status=ok`
- direct first interactive page/action evidence for product-originating login,
  create-account, and forgot-password links
- direct first interactive page/action evidence for email-originating verification
  and password-reset completion links without retaining raw URLs
- rerun-safe account handling, reset delivery/consumption, login, and
  `GET /v1/auth/session`
- sanitized signed-context claim proof from
  `/api/v1/diagnostics/huleedu-internal-identity`

The Skriptoteket proof must then prove:

- callback continuation to the intended Skriptoteket route
- shared-session bootstrap using `active_app=skriptoteket`
- `active_product_identity_realm=skriptoteket_standalone`
- signed-context and session claim presence/equality booleans for the realm
  subject and provider email, with `email_verified=true`
- local `identity_projection` resolved from
  `(active_product_identity_realm, realm_subject_id)` during the run without
  retaining the raw subject in Skriptoteket artifacts
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
- `upstream_huleedu_task_0327` with artifact path, `status=ok`, validated
  direct-action summary, session-claim summary, and sanitized signed-context
  claim summary
- `action_page_assertions` consumed from the upstream artifact for login,
  register, password-reset request, password-reset completion, and email
  verification
- `redacted_email_link_evidence` recording link kind, target action, first interactive page, and
  `raw_url_retained=false`
- `callback_assertions`
- `projection_assertions`
- `local_role_assertions`
- `screenshots` and `logs` paths, if retained
- `redaction_checks` with an explicit pass/fail result

Allowed evidence types are sanitized screenshots, browser event summaries, route/action names,
HTTP status summaries, redacted log excerpts, and decoded non-secret assertion summaries.

Forbidden fields are credentials, session cookies, CSRF tokens, verification
tokens, reset tokens, raw magic links, raw email bodies containing action links,
raw signed identity payloads, raw signed-context email, raw `realm_subject_id`,
and unredacted provider headers.

## Implementation Plan

1. Define the controlled-account proof inputs, upstream HuleEdu artifact input,
   and artifact directory for dev and production runs using the manifest
   contract above.
2. Inspect the closest existing proof scripts before implementation:
   `scripts/playwright_pr_0254_auth_cutover.py`, `scripts/playwright_pr_0257_auth_lifecycle.py`,
   and `scripts/playwright_pr_0258_auth_projection.py`.
3. Add `scripts/playwright_pr_0262_real_lifecycle.py` plus a
   `pdm run pr-0262-real-lifecycle` wrapper that invokes
   `python -m scripts.playwright_pr_0262_real_lifecycle`.
4. Validate the HuleEdu `TASK-0327` artifact for final provider lifecycle,
   direct-action, session, and sanitized diagnostics proof.
5. Verify Skriptoteket callback, shared-session bootstrap, realm-aware
   projection resolution, and local role visibility with the assertion contract
   above.
6. Retain only sanitized summaries. Use raw session subject/email values
   transiently if needed to seed or verify the local projection, then assert
   they are absent from `manifest.redacted.json`.
7. Add redaction tests or artifact-inspection checks for `manifest.redacted.json`, retained logs,
   and retained screenshots.
8. Update the operator runbook with dev/prod commands, prerequisites, expected evidence, failure
   interpretation, redaction rules, and handoff to `PR-0254`.

## Implementation Summary (as of 2026-04-13)

`PR-0262` is implemented as the Skriptoteket-side companion proof to HuleEdu
`TASK-0327`. The reusable artifact contract and redaction checks live in
`scripts/_pr_0262_lifecycle_manifest.py`; the retained live proof entrypoint is
`scripts/playwright_pr_0262_real_lifecycle.py`; and the command surface is
`pdm run pr-0262-real-lifecycle`.

The proof consumes the final HuleEdu `TASK-0327` `status=ok` artifact as
upstream provider evidence. It validates the direct-action lifecycle matrix,
session claims, and sanitized signed-context probe shape, then uses transient
session subject/email values only to seed and verify the local Skriptoteket
projection. The retained Skriptoteket manifest records callback continuation,
local projection resolution, local `User.role` observation, live diagnostics
probe assertions, and explicit redaction checks without retaining raw
signed-context email, raw `realm_subject_id`, raw signed headers, tokens,
cookies, CSRF, or raw magic links.

The local non-production proof passed and retained:

```text
.artifacts/playwright-pr-0262-real-lifecycle/local-nonprod/20260413T132801Z/manifest.redacted.json
```

## Runbook Verification Gates

The runbook must name these commands before this PR can close:

```bash
pdm run pr-0262-real-lifecycle --environment local-nonprod --huleedu-artifact /Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod
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

- upstream artifact missing direct-action evidence is a HuleEdu `TASK-0327` /
  `PR-0261` route-matrix failure, not a successful Skriptoteket proof
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
  path in `.codex/handoff.md`.

## Rollback Plan

Remove the proof command/runbook additions if they encode an incorrect lifecycle
contract. Keep `ST-28-12` open until real-account proof is available.
