---
type: review
id: REV-PR-0262
title: "Review: PR-0262 real lifecycle proof smoke and runbook"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0262
links:
  - EPIC-28
  - ST-28-12
  - PR-0260
  - PR-0261
  - HuleEdu TASK-0326
  - HuleEdu TASK-0327
---

## TL;DR

Approved for implementation after adapting the proof lane to consume the final
HuleEdu `TASK-0327` `status=ok` artifact and retain only sanitized
Skriptoteket-side projection/role evidence.

## Problem Statement

The final auth cutover should not rely on assumptions about email verification,
password reset, or projection behavior. Operators need a repeatable proof that
uses controlled accounts and sanitized artifacts.

## Proposed Solution

Add a dedicated lifecycle smoke/runbook before `PR-0254`, using HuleEdu
provider lifecycle routes and Skriptoteket projection/role behavior.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md` | Proof scope and artifact contract | 10 min |
| `docs/backlog/stories/story-28-12-real-standalone-lifecycle-and-auth-entry-proof.md` | Parent story expectations | 5 min |
| HuleEdu `TASK-0326` / `TASK-0327` | Provider prerequisites | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Separate lifecycle proof from final cutover smoke | Keeps failures easier to diagnose | [x] |
| Use controlled real inbox accounts | Proves launch behavior without bulk alpha import | [x] |
| Prove direct-action link landing | Product and email links must open the requested action page directly | [x] |
| Sanitize retained artifacts | Proof must not leak credentials or tokens | [x] |

## Review Checklist

- [x] Proof covers register, verify, login, forgot, reset, callback, projection, and role
- [x] Product and email links land directly on their requested action pages
- [x] Side-effecting production proof is explicit
- [x] Artifact redaction is mandatory
- [x] `PR-0254` dependency handoff is clear
- [x] Dev and production proof models are aligned

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** changes_requested

### Scope Under Review

- `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md`
- `docs/backlog/stories/story-28-12-real-standalone-lifecycle-and-auth-entry-proof.md`
- `PR-0260`, `PR-0261`, HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, and their retained reviews

Runtime/operational surfaces affected: the future lifecycle Playwright/operator smoke,
controlled-account inputs, sanitized artifact contract, app callback/bootstrap proof,
projection resolution, local role observation, and handoff into final `PR-0254`.

### Required Changes

1. **high: The proof lane depends on unapproved prerequisite reviews.**

   `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md:13`
   depends on `PR-0260`, `PR-0261`, HuleEdu `REV-TASK-0326-01`, and HuleEdu
   `REV-TASK-0327-01`. The two HuleEdu reviews are currently `changes_requested`, and the
   two Skriptoteket prerequisite reviews now require changes as well. This lifecycle smoke
   cannot be approved until the schema, route matrix, and auth-entry contracts are accepted.

   **Fix:** keep `PR-0262` gated behind approved provider reviews plus approved `REV-PR-0260`
   and `REV-PR-0261`; then update the runbook/proof plan to consume their exact accepted
   schema and URL contracts.

   **Proof requirement:** re-review `PR-0262` after those reviews are approved and rerun
   `pdm run docs-validate`.

2. **high: Projection/role proof is not tied tightly enough to the accepted bootstrap identity.**

   `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md:58`
   requires callback, projection resolution, and role visibility. That is not precise enough
   for a cross-app auth proof: the smoke must prove the post-lifecycle session context maps to
   the same realm-aware identity consumed by `PR-0260`, not merely that some local user opens.

   **Fix:** require the lifecycle proof to assert `active_app=skriptoteket`,
   `active_product_identity_realm=skriptoteket_standalone`, nonblank `realm_subject_id`,
   provider-owned email, `email_verified=true`, the matching local `identity_projection`, and
   the expected local `User.role` from the `PR-0260` matrix. Retain decoded/sanitized
   assertions, not raw signed identity payloads.

   **Proof requirement:** add Playwright/operator assertions and focused backend helper tests
   that fail if the callback resolves by email alone, by an unsupported realm, or by a local role
   that was not assigned from the accepted matrix.

3. **medium: The artifact contract needs a concrete manifest before implementation.**

   `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md:24`
   requires sanitized evidence, and `:60` says to redact raw links/tokens/cookies. The PR does
   not yet define the artifact directory, manifest fields, allowed evidence types, or how
   screenshots/logs prove email-link landing without retaining raw verification/reset URLs.

   **Fix:** add an artifact manifest contract before implementation: command, environment,
   timestamp, app/realm, controlled-account key, action-page assertions, redacted email-link
   evidence, callback/projection/local-role assertions, and explicit forbidden fields
   (credentials, cookies, verification tokens, reset tokens, raw magic links, raw signed
   identity payloads).

   **Proof requirement:** add redaction tests or artifact-inspection checks and record the
   sanitized artifact path in `.agents/handoff.md`.

4. **medium: Verification commands are still placeholders.**

   `docs/backlog/prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md:65`
   names focused tests, docs validation, and local/production proof, but not the exact
   Playwright command, type/lint gates, or failure-triage checks the runbook must preserve.

   **Fix:** once the proof script exists, name the command and include `pdm run fe-type-check`
   if frontend proof helpers change, `pdm run typecheck`, `pdm run lint`,
   `pdm run docs-validate`, and `git diff --check`, plus the local non-production HuleEdu lane
   used for the smoke.

   **Proof requirement:** retain command results and sanitized artifacts before requesting
   re-review.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Separate lifecycle smoke
- [x] Controlled real inbox account
- [x] Direct-action link landing
- [x] Sanitized artifacts

### Re-review

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** approved

The previous blocker is resolved. HuleEdu `TASK-0327` now has a final
`status=ok` live apply artifact against the new `PR-0261` Skriptoteket
diagnostics route, and the HuleEdu runner accepts the approved sanitized
diagnostics shape from `/api/v1/diagnostics/huleedu-internal-identity`.

`PR-0262` is approved with one explicit adaptation: Skriptoteket must consume
the HuleEdu artifact as upstream provider proof rather than re-drive the
real-inbox lifecycle. The retained Skriptoteket proof must validate the
upstream direct-action/session/signed-context evidence, then prove
Skriptoteket callback continuation, local projection, and local role
observation. Raw signed-context email, raw `realm_subject_id`, raw signed
headers, tokens, cookies, CSRF, and magic links remain forbidden in retained
Skriptoteket artifacts.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0262` | Initial review-ready lifecycle proof slice |
| 2 | `PR-0262` | Added `REV-PR-0260` and `REV-PR-0261` as explicit dependencies and added a prerequisite gate requiring approved HuleEdu provider reviews plus approved Skriptoteket prerequisite reviews before implementation |
| 3 | `PR-0262` | Tightened lifecycle proof assertions around `active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`, nonblank `realm_subject_id`, provider-owned verified email, matching `identity_projection`, and local `User.role` from the accepted `PR-0260` matrix |
| 4 | `PR-0262` | Added the concrete `manifest.redacted.json` artifact contract, default `.artifacts/playwright-pr-0262-real-lifecycle/...` path, allowed evidence types, and forbidden retained fields |
| 5 | `PR-0262` | Named the future `scripts/playwright_pr_0262_real_lifecycle.py` module, `pdm run pr-0262-real-lifecycle` proof command, required validation gates, HuleEdu local non-production lane, and failure-triage interpretation |
| 6 | `REV-PR-0262` | Requested re-review of the revised proof plan; final approval remains gated by approved `REV-TASK-0326-01`, `REV-TASK-0327-01`, `REV-PR-0260`, and `REV-PR-0261` |
| 7 | `PR-0262` / `REV-PR-0262` | Approved the adapted proof shape after HuleEdu `TASK-0327` final live apply succeeded against the `PR-0261` sanitized diagnostics route |
