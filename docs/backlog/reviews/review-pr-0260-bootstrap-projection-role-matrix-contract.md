---
type: review
id: REV-PR-0260
title: "Review: PR-0260 bootstrap projection role matrix contract"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0260
links:
  - EPIC-28
  - ST-28-11
  - HuleEdu TASK-0326
  - REV-TASK-0326-01
---

## TL;DR

Review the Skriptoteket consumer slice that maps HuleEdu bootstrap proof
subjects into local users, local roles, and realm-aware projections.

## Problem Statement

Final auth proof needs role-bearing Skriptoteket accounts, but Skriptoteket must
not recreate password ownership or turn fake alpha education-domain users into a
bulk migration blocker.

## Proposed Solution

Consume the provider subject export from HuleEdu `TASK-0326`, apply an explicit
Skriptoteket-owned role matrix, and keep all authorization in local `User.role`
while projection identity comes from `(product_identity_realm,
realm_subject_id)`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md` | Scope and implementation contract | 10 min |
| `docs/backlog/stories/story-28-11-bootstrap-proof-identities-and-projection-role-matrix.md` | Parent story expectations | 5 min |
| `docs/backlog/tasks/task-0326-*` in HuleEdu | Provider prerequisite fit | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Do not bulk import alpha users | Fake education-domain users are not launch-critical identity assets | [x] |
| Keep role assignment local | Skriptoteket roles remain product authorization, not provider claims | [x] |
| Require sanitized subject export input | Avoid copying credentials or tokens between repos | [x] |

## Review Checklist

- [x] Scope is in the correct repo
- [x] Acceptance criteria are reviewable
- [x] Idempotency and duplicate handling are explicit
- [x] Local role preservation is protected
- [x] Verification covers sanitized evidence

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** approved

### Scope Under Review

- `docs/backlog/prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md`
- `docs/backlog/stories/story-28-11-bootstrap-proof-identities-and-projection-role-matrix.md`
- HuleEdu `TASK-0326` and retained review `REV-TASK-0326-01`

Public/operational surfaces affected: the future Skriptoteket bootstrap command or
application service, the accepted provider subject-export schema, local
`identity_projections`, local `User.role`, sanitized operator logs/artifacts, and the
operator runbook handoff into `PR-0254`.

### Required Changes

Resolved.

1. **high: Provider prerequisite review is still unresolved.** Resolved
   2026-04-13: HuleEdu `REV-TASK-0326-01` is approved, `TASK-0326` is done,
   deployed at merge commit `92419293`, and production proof accounts were
   verified on Hemma.

   `docs/backlog/prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md:13`
   depends on HuleEdu `REV-TASK-0326-01`, but that retained provider review is currently
   `changes_requested`. The consumer slice should not be treated as implementation-ready while
   the upstream export/runtime identity contract is explicitly unapproved.

   **Fix:** keep `PR-0260` gated until HuleEdu `REV-TASK-0326-01` is approved, or amend
   `PR-0260` to say implementation begins only from the corrected provider export schema
   accepted by that review.

   **Proof requirement:** after the provider review is resolved, update this review with the
   accepted HuleEdu export/schema reference and run `pdm run docs-validate`.

2. **high: The consumed export schema is still too loose for the realm-aware projection key.**

   `docs/backlog/prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md:52`
   says the export includes stable account key, email, realm subject ID, product realm, and
   local role intent. That is directionally right, but it leaves implementers free to invent
   field names or accidentally key projections from the umbrella HuleEdu subject instead of
   `(product_identity_realm, realm_subject_id)`.

   **Fix:** before implementation, freeze the exact input schema in `PR-0260`: at minimum
   `stable_account_key`, `active_app=skriptoteket`,
   `active_product_identity_realm=skriptoteket_standalone`, `realm_subject_id`, `email`,
   `email_verified=true`, and an explicitly consumer-owned `skriptoteket_role_hint` or
   equivalent local role-matrix key. If `huleedu_subject_id` is present, label it diagnostic
   only and forbid projection lookup from it.

   **Proof requirement:** add schema/fixture tests that fail when `active_product_identity_realm`
   or `realm_subject_id` is missing, reject non-`skriptoteket` app values, and prove duplicate
   subject/email handling fails closed without inferred linking. Run the focused backend tests
   plus `pdm run docs-validate`.

3. **medium: The verification plan is not yet executable enough for a launch auth bootstrap.**

   `docs/backlog/prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md:69`
   lists focused tests and docs validation, but not the concrete command names, type/lint gates,
   or sanitized artifact location expected from the future command.

   **Fix:** once implementation files are named, update the test plan with exact focused
   `pdm run pytest ...` paths, `pdm run typecheck`, `pdm run lint`, `pdm run docs-validate`,
   `git diff --check`, and the gitignored artifact directory for sanitized bootstrap evidence.

   **Proof requirement:** record those command results and artifact redaction checks in
   `.agents/handoff.md` before requesting re-review.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] No alpha-user bulk import
- [x] Local-only role assignment
- [x] Sanitized provider export contract

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0260` | Initial review-ready consumer bootstrap slice |
| 2 | `ST-28-11` / `PR-0260` | Marked the story and PR blocked until HuleEdu `REV-TASK-0326-01` approves the corrected provider export contract |
| 3 | `PR-0260` | Froze the consumed export schema, including `stable_account_key`, `active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`, `realm_subject_id`, `email`, `email_verified=true`, and `skriptoteket_role_hint` |
| 4 | `PR-0260` | Explicitly labeled `huleedu_subject_id` diagnostic-only and forbidden as a projection lookup key |
| 5 | `PR-0260` | Added concrete focused backend test commands, type/lint/docs/diff gates, and the gitignored sanitized artifact directory `.artifacts/skriptoteket-auth-bootstrap/` |
| 6 | `PR-0260` | Recorded HuleEdu `TASK-0326` completion/deployment/proof state and marked the provider gate resolved |

## Re-review Decision 2026-04-13

Approved. `PR-0260` is now ready to implement. The provider gate has cleared and
the requested local clarifications are present:

- Provider approval and production bootstrap/export proof are recorded.
- The exact realm-aware input schema is now frozen locally.
- `huleedu_subject_id` is diagnostic only and cannot drive projection lookup.
- Missing realm/subject, wrong app, duplicate subject/email, unverified email,
  and inferred email linking all fail closed.
- Verification now names focused backend paths, type/lint/docs gates,
  `git diff --check`, and the sanitized artifact directory.
