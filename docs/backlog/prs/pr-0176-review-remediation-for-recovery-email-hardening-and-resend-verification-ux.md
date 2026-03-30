---
type: pr
id: PR-0176
title: "Review remediation for recovery email hardening and resend verification UX"
status: done
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-02-10"
tags: ["identity", "email", "frontend", "review-remediation"]
acceptance_criteria:
  - "The resend-verification affordance no longer introduces a frontend-only cooldown contract that can drift from backend truth across emails or surfaces."
  - "Frontend regression coverage proves the resend flow does not block a different email in the same surface and does not rely on a per-surface cooldown to enforce backend semantics."
  - "The auth-recovery live-proof recorded in docs/handoff is rerunnable as an exact command or named script, with artifact output path documented."
  - "ST-02-10 and PR-0174 link this remediation task so the ruthless review findings remain traceable inside EPIC-02."
---

## Problem

The ruthless implementation review for the `ST-02-10` slice returned `changes_requested` on two
issues:

1. the new resend-verification affordance added a local per-component cooldown that can drift from
   the backend's normalized-email cooldown semantics, and
2. the handoff verification trail records the auth-recovery browser proof as an abbreviated heredoc
   placeholder instead of an exact rerunnable command.

Both issues are small, but they weaken the claim that the slice preserves the backend-owned resend
contract and that the verification trail is reproducible for the next session.

## Goal

Ship the narrow remediation that:

1. restores backend authority over resend cooldown semantics,
2. tightens regression coverage around resend behavior, and
3. records the live auth-recovery proof as an exact rerunnable command or script.

## Non-goals

- A new resend-verification backend contract.
- New identity or email-provider features.
- A broad redesign of the current `ST-02-10` auth recovery UX.

## Implementation plan

### 1. Frontend resend semantics

- Remove the current client-only cooldown or replace it with a shared normalized-email keyed
  mechanism.
- Prefer the simpler remediation: trust the existing backend cooldown and keep the frontend limited
  to submit-in-flight state plus generic success/error feedback.

### 2. Regression coverage

- Add or update frontend tests so the same view can resend for email A and then email B without a
  stale cooldown leak.
- Add or update coverage so the same address cannot rely on per-surface client cooldown behavior as
  the source of truth.

### 3. Verification trail

- Replace the abbreviated auth-recovery live-check placeholder in `.agents/handoff.md` with an
  exact command or a named script path plus artifact location.
- Keep the handoff within the enforced line budget.

## Execution notes

- Frontend remediation is intentionally minimal:
  - `frontend/apps/skriptoteket/src/composables/auth/useVerificationResend.ts` no longer starts or
    exposes a client cooldown timer.
  - `frontend/apps/skriptoteket/src/views/ForgotPasswordView.vue` and
    `frontend/apps/skriptoteket/src/components/auth/LoginModal.vue` now disable resend only while
    the request is in flight and otherwise defer cooldown truth to the backend.
- Regression coverage is tightened at the surface level:
  - `ForgotPasswordView.spec.ts` now proves the same view can resend for email A and then email B
    without a stale per-surface block.
  - `LoginModal.spec.ts` now proves the resend action stays available after a successful resend
    instead of swapping to a local countdown state.
- Live-proof reproducibility now uses a named Playwright entrypoint:
  - `scripts/playwright_pr_0176_auth_recovery_check.py`
  - artifacts: `.artifacts/pr-0176-auth-recovery-check/`

## Test plan

### Frontend

- `pdm run fe-test -- --run src/components/auth/LoginModal.spec.ts src/views/ForgotPasswordView.spec.ts src/stores/auth.spec.ts`

### Docs

- `pdm run docs-validate`

### Manual proof

- `pdm run python -m scripts.playwright_pr_0176_auth_recovery_check --base-url http://127.0.0.1:5173`
- Artifacts: `.artifacts/pr-0176-auth-recovery-check/`

## Rollback plan

- Revert the resend-remediation change if it introduces a worse UX regression.
- Leave the backend-owned resend-verification handler unchanged; this remediation should remain UI-
  and docs-scoped.
