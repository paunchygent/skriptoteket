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

## Planning Re-review Decision 2026-04-13

Approved for implementation planning. The provider gate had cleared and the
requested local clarifications were present:

- Provider approval and production bootstrap/export proof are recorded.
- The exact realm-aware input schema is now frozen locally.
- `huleedu_subject_id` is diagnostic only and cannot drive projection lookup.
- Missing realm/subject, wrong app, duplicate subject/email, unverified email,
  and inferred email linking all fail closed.
- Verification now names focused backend paths, type/lint/docs gates,
  `git diff --check`, and the sanitized artifact directory.

## Implementation Review Decision 2026-04-13

Changes requested. The implementation is close and the layering is mostly
healthy: the application service owns the mutation, the CLI is only a
composition entrypoint, and Unit of Work commit semantics stay on the
application boundary. Two issues must be remediated before `PR-0260` can be
accepted:

1. The export boundary must not accept synthesized or unversioned input. Bare
   arrays and `{"accounts": [...]}` payloads must be rejected instead of being
   filled with default schema/app/realm values.
2. Blocked mapping audit behavior must be durable. Unsafe apply paths must roll
   back user/projection mutations but still record a sanitized local
   `identity_projection_events` audit row for the blocked outcome.

**Implementation review verification:** `pdm run pytest -q
tests/unit/application/identity/test_bootstrap_subject_export_schema.py
tests/unit/application/identity/test_bootstrap_projection_role_matrix.py`
passed; `pdm run consume-huleedu-subject-export --help` confirmed command
registration; `pdm run typecheck` passed. The reviewer did not run
`pdm run lint`, `pdm run docs-validate`, or `git diff --check` in that pass.

## Changes Made For Implementation Review

| Change | Artifact | Description |
|--------|----------|-------------|
| 7 | `huleedu_subject_export_contract.py` | Made `schema_version`, `active_app`, and `active_product_identity_realm` required top-level export fields; stopped synthesizing them from defaults |
| 8 | schema tests | Added rejection coverage for bare arrays, unversioned accounts objects, missing contract fields, and failed provider envelopes |
| 9 | `huleedu_subject_export_consumer.py` | Added blocked-mapping handling that rolls back unsafe apply mutations and then records a sanitized local audit event in a clean Unit of Work |
| 10 | projection-role matrix tests | Asserted duplicate email/linking failures persist the expected `DUPLICATE_EMAIL_LINKING_REQUIRED` event |
| 11 | audit integration test | Added DB-backed proof that a blocked email-linking apply creates no user/projection mutation but does commit the audit event |

## Remediation Re-review Request 2026-04-13

`PR-0260` is ready for re-review after changes-requested remediation. The
consumer now accepts only either the HuleEdu provider envelope with
`status=ok`, no errors, and a versioned export object, or a fully versioned
export object. It rejects bare arrays, unversioned account objects, missing
top-level contract fields, failed provider envelopes, and any export whose app
or realm does not match the frozen Skriptoteket contract.

Blocked apply outcomes now align with the local projection event ledger model:
the unsafe mutation transaction rolls back, then a separate clean Unit of Work
records a sanitized `identity_projection_events` row for the blocked reason.
This keeps user/projection state all-or-nothing while preserving the operator
audit trail for fail-closed identity decisions.

## Remediation Re-review Decision 2026-04-13

Approved. The two required implementation-review changes are resolved:

- The export contract no longer synthesizes schema/app/realm values from bare
  arrays or unversioned `{"accounts": [...]}` payloads. `schema_version`,
  `active_app`, and `active_product_identity_realm` are required top-level
  fields, and focused schema tests prove those invalid shapes fail closed.
- Blocked apply paths now roll back unsafe user/projection mutations and then
  persist a sanitized local `identity_projection_events` row in a clean Unit of
  Work. The new DB-backed integration test proves the email-linking conflict
  retains the audit event without creating a projection or extra user row.

Dry-run reporting polish completed after the re-review discussion: result
artifacts now include explicit `would_create_users`,
`would_create_projections`, and `would_update_users` summary counters. The CLI
dry-run line reports those planned counters, while apply mode reports concrete
`created_users`, `created_projections`, and `updated_users` write counters.
