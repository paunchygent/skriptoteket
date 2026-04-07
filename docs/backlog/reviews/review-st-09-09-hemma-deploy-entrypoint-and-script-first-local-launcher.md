---
type: review
id: REV-ST-09-09
title: "Review: ST-09-09 Hemma deploy entrypoint and script-first local launcher"
status: approved
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
reviewer: "lead-developer"
stories:
  - ST-09-09
adrs:
  - ADR-0081
links:
  - EPIC-09
  - ADR-0053
  - PR-0122
  - PR-0146
---

## TL;DR

`ST-09-09` proposes one canonical local operator entrypoint for Hemma deploys:
`pdm run hemma-deploy`.

The key boundary is that this must standardize launch, not duplicate deploy
logic. The existing on-host script
`scripts/hemma_deploy_and_verify_seating_export.sh` should remain the single
deploy/readiness implementation, while the new local launcher must provide a
quoting-safe, detached remote-start path from the local repo into that remote
script. Any optional live monitor should remain a best-effort filtered tail of
the authoritative raw remote log rather than a second source of deploy truth.

## Problem Statement

Skriptoteket already has a real Hemma deploy/readiness script, but the local
operator path is still effectively a raw SSH recipe.

That leaves a reliability gap:

- remote command composition can drift into nested quoting mistakes
- operators can improvise detached launches or ad hoc diagnostics outside the
  canonical path
- the repo has no stable `pdm run ...` deploy entrypoint even though the
  project otherwise prefers script-first operational commands

The review needs to confirm that the new story tightens operator discipline
without creating a second deploy system or weakening the existing fail-closed
readiness gate.

## Proposed Solution

Approve a script-first two-layer deploy model:

1. Keep `scripts/hemma_deploy_and_verify_seating_export.sh` as the single
   on-host deploy/readiness implementation.
2. Add `pdm run hemma-deploy` as the canonical local launch path.
3. Require the local launcher to use the repo-approved, quoting-safe SSH model
   and to launch the on-host script as a detached remote process with PID and
   log breadcrumbs.
4. If a follow/monitor path is exposed, make it a lightweight filtered tail of
   the authoritative raw remote log using existing milestone markers and
   obvious failure patterns only.
5. Keep direct on-host script execution documented as the fallback/debug path,
   not as a competing primary operator entrypoint.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0081-hemma-deploy-entrypoint-and-script-first-local-launcher.md` | Decision boundary, supersession scope, and consequences | 6 min |
| `docs/backlog/stories/story-09-09-hemma-deploy-entrypoint-and-script-first-local-launcher.md` | Acceptance criteria, verification burden, and fallback rules | 6 min |
| `docs/backlog/epics/epic-09-security-hardening.md` | Epic fit and story placement | 3 min |
| `docs/backlog/prs/pr-0122-klassrumskartan-seating-export-production-wiring-and-hemma-deploy-orchestration.md` | Historical deploy-wrapper assumptions this review may deliberately narrow/supersede | 6 min |
| `docs/runbooks/runbook-home-server.md` | Current canonical deploy instructions and fallback/debug wording | 5 min |
| `scripts/hemma_deploy_and_verify_seating_export.sh` | Existing on-host deploy/readiness source of truth that must remain singular | 6 min |
| `pyproject.toml` | Future `pdm run hemma-deploy` entrypoint seam | 3 min |

**Total estimated time:** ~35 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the existing on-host script as the only deploy/readiness implementation | Prevents deploy-logic drift across laptop and server paths | [x] |
| Add `pdm run hemma-deploy` as the canonical local operator entrypoint | Gives one script-first launch path and reduces ad hoc SSH composition | [x] |
| Require quoting-safe detached remote start with PID + log breadcrumbs | Lets the deploy survive initiator-session loss without inventing a second deploy flow | [x] |
| Keep any monitor/follow output as a filtered view over the raw log only | Preserves one authoritative deploy record while still giving operators a readable stream | [x] |
| Keep direct on-host script execution as documented fallback/debug only | Preserves break-glass operability without competing with the canonical local path | [x] |
| Explicitly supersede the older “not a laptop-side SSH wrapper” assumption only at the launch layer | Allows a local launcher while keeping all actual deploy logic on Hemma | [x] |

## Review Checklist

- [x] Scope is bounded to operator entrypoint hardening rather than broader production-topology changes
- [x] `ADR-0081` keeps the deploy/readiness logic centralized in the existing on-host script
- [x] The story makes the canonical local path, the direct on-host fallback, and the detached remote-start contract explicit
- [x] The raw log remains the deploy truth and any follow/monitor path is documented as best-effort only
- [x] The review surface names the historical `PR-0122` assumption it is superseding so implementation does not inherit contradictory guidance
- [x] Verification requires a real Hemma launch through `pdm run hemma-deploy` plus recorded evidence in `.agents/handoff.md`

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-07`
**Verdict:** approved

Initial review opened with `changes_requested`; the redraft resolved those
planning issues, and the accepted package now unblocks implementation.

### Historical finding from the first review pass

The initial `changes_requested` verdict was correct at the time it was issued.
The earlier `ADR-0081` / `ST-09-09` draft incorrectly treated
foreground/non-detached SSH attachment as the desired operator model, which
conflicted with the real Hemma requirement that the on-host deploy must survive
loss of the initiating local or SSH session.

That earlier finding drove the redraft recorded below.

### Current re-review assessment

The current docs package is materially aligned on the critical launch boundary:

- `ADR-0081` now requires detached remote start
- `ST-09-09` now requires PID + remote log breadcrumbs
- the raw remote log is now explicitly the deploy truth
- any readable follow/monitor lane is now explicitly best-effort and
  raw-log-derived rather than a second source of truth

That inconsistency has now been corrected, and the retained review record is
aligned with the accepted detached-launch package.

### Goal Shape To Review Against

The approved implementation should leave Hemma deployment with one honest
operator model:

1. The real deploy/readiness work still happens in the checked-in on-host
   script.
2. The local repo has one canonical command to launch that work.
3. The launcher does not invent a second deploy flow.
4. The normal path must survive initiating-session loss rather than depending on
   a foreground SSH attachment.
5. Operators still retain an explicit direct-on-host fallback for debugging or
   break-glass recovery.

### Required Verification

- Run:
  - `pdm run docs-validate`
- Manual checks after implementation:
  - run `pdm run hemma-deploy` from the local repo
  - confirm the launcher invokes the checked-in remote script from the
    documented Hemma repo path
  - confirm the launcher starts the on-host deploy in a way that survives loss
    of the initiating local or SSH session
  - confirm the launcher prints the remote PID and remote log path
  - if a monitor/follow path is provided, confirm it tails the authoritative
    raw log and filters it to existing `==>` milestone lines plus obvious
    failure patterns rather than claiming separate deploy truth
  - confirm start-up failures propagate back as non-zero local exit status
  - confirm the runbook points to `pdm run hemma-deploy` as the canonical local
    path and keeps direct on-host script execution as fallback/debug only
  - record the exact verification method and any log/artifact path in
    `.agents/handoff.md`

### Pass Means

- operators no longer need to compose ad hoc SSH launch commands for the normal
  Hemma deploy path
- the deploy/readiness contract still lives in exactly one checked-in script
- the repo’s SSH guidance and the deploy docs no longer point in subtly
  different directions
- the canonical launch path no longer risks aborting the deploy when the
  initiating session disappears
- operators can optionally follow a readable filtered stream without weakening
  the raw remote log as the source of truth
- the fallback path is explicit without competing with the canonical entrypoint

### Initial Required Changes (Resolved)

The rewrite items from the first review pass are now addressed in the accepted
docs package:

- no local duplication of compose, migration, or readiness logic
- detached remote start is now the required launcher contract
- PID + remote log breadcrumbs are now explicit
- raw-log authority plus lightweight filtered monitor behavior are now explicit

Implementation should still keep the launcher thin:

- if a monitor/follow path is included, keep it intentionally lightweight:
  filtered `tail -F` over the raw log using existing `==>` milestone markers
  plus obvious failure patterns is sufficient for this slice
- no ambiguous split between “canonical local command” and “canonical on-host
  command” in the runbook wording

### Suggestions (Optional)

- Prefer a simple `nohup`/`setsid` launcher that starts the checked-in on-host
  script, prints the remote PID plus remote log path immediately, and leaves
  the deploy/readiness logic entirely on Hemma.
- Avoid inventing a structured second log format just to make the monitor
  prettier; the full raw log already exists on Hemma as the authority.

### Decision Approvals

- [x] Keep on-host deploy logic singular
- [x] Add canonical `pdm run hemma-deploy`
- [x] Require quoting-safe detached remote start with PID + log breadcrumbs
- [x] Keep any monitor/follow output best-effort and raw-log-derived
- [x] Preserve direct on-host fallback
- [x] Supersede the old launch-layer assumption only

### Re-review approval

**Reviewer:** `lead-developer`
**Date:** `2026-04-07`
**Verdict:** approved

The detached-launch model, PID/log breadcrumb contract, and lightweight
raw-log-derived monitor model are now clear enough to implement without
reopening the operator boundary.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-ST-09-09` | Created the retained story review record for the Hemma deploy-entrypoint lane. |
| 2 | `ADR-0081` | Governed the new deploy-entrypoint ADR through `adrs:` instead of inventing a standalone ADR-target review doc. |
| 3 | Review feedback | Sent the package back with changes requested because the ADR currently requires foreground/non-detached launch behavior that conflicts with the real deploy survivability requirement for Hemma. |
| 4 | `ADR-0081` | Redrafted the ADR so the canonical local launcher must start the on-host deploy as a detached remote process that survives initiating-session loss and prints PID + remote log breadcrumbs. |
| 5 | `ST-09-09` | Redrafted the story acceptance criteria and notes around detached remote start, start-up failure propagation, and PID/log follow-up breadcrumbs. |
| 6 | `ADR-0081` + `ST-09-09` | Clarified that the raw remote log remains authoritative and any optional human-readable monitor is only a best-effort filtered tail over that log using existing milestone/failure patterns. |
| 7 | Re-review request | The docs package now addresses the launcher survivability conflict and the lightweight monitor model, so the retained review is ready for another reviewer pass. |
| 8 | `REV-ST-09-09` | Rewrote the retained review feedback so it distinguishes the historical foreground-launch finding from the current post-redraft assessment and no longer lists already-addressed rewrite work as if it were still open. |
| 9 | Review closure | Updated the retained review to `approved` after the reviewer accepted the detached-launch redraft. |
