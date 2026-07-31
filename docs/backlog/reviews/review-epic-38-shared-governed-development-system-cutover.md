---
type: review
id: REV-EPIC-38
title: "Review: Shared governed development system cutover"
status: pending
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
reviewer: "plan-document-reviewer"
epic: "EPIC-38"
stories:
  - "ST-38-01"
prs:
  - "PR-0417"
  - "PR-0418"
  - "PR-0419"
  - "PR-0420"
  - "PR-0421"
links:
  - "ST-SKILL-08-06"
---

## TL;DR

The repaired local cutover spine fits the approved central story. This legacy
review records that assessment but supplies no machine lifecycle authority:
the approved central ST-SKILL-08-06 review plus the user-approved one-time
exception authorize only PR-0417 bootstrap. PR-0418 through PR-0421 remain
blocked non-authorizing envelopes until their task-level gates close.

## Problem Statement

Skriptoteket needs a reviewed local authority spine for the central cutover
without treating blocked downstream slices as implementation-ready.

## Proposed Solution

Approve the repository-bounded five-slice plan shape. Preserve the local
legacy frontmatter/status unchanged and machine-nonauthoritative until PR-0418
migrates the nonterminal spine. Permit only the exact centrally authorized
PR-0417 bootstrap; keep PR-0418 through PR-0421 blocked on their recorded
dependencies and task-level admission facts.

## Artifacts to Review

- `EPIC-38`, `ST-38-01`, and PR-0417 through PR-0421.
- Skill Repository ST-SKILL-08-06 and TASK-SKILL-08-06-01/02.
- Retained session `019fb6e2-3384-79c1-9a74-ecfbae775f81`.

## Key Decisions

- One-time direct-main bootstrap, then governed worktrees.
- Bootstrap authority is limited to the user-approved one-time direct-`main`
  exception plus the approved central story review. The retained local review's
  legacy `pending` frontmatter and blocked lifecycle remain
  machine-nonauthoritative until PR-0418 semantically migrates the nonterminal
  spine.
- No local guard bypass, manual status transition, or retroactive authorization
  is permitted; the normal task/worktree lane resumes after bootstrap proof.
- Complete current corpus migration with terminal backlog preserved as history.
- Shared current validation plus historical-only read-only validation.
- Runtime-available disjoint specialists with parent-owned shared writes.
- Named-scope proof and no unscoped aggregate.

## Review Checklist

- [x] The local spine derives only from closed ST-SKILL-08-06 decisions.
- [x] The direct-main exception is exact and expires after worktree proof.
- [x] Terminal backlog remains historical and every governed source is
      dispositioned.
- [x] Current and historical validation have one noncompeting owner each.
- [x] Only PR-0417 is the first executable local slice under the approved
      central authority.

## Review Feedback

**Reviewer:** plan-document-reviewer
**Date:** 2026-07-31T09:35:49+02:00
**Verdict:** approved

### Required Changes

None for the local EPIC-38/ST-38-01/PR-0417 through PR-0421 plan shape.
PR-0417 now closes the exact immutable dependency/lock/installed identity,
schema-v3 facts, typed owner, setup groups, complete generated binding tuple,
tracked write set, focused proof, and exception expiry. PR-0418 through PR-0421
carry explicit non-authorizing task-admission gates.

### Permitted Next Step

The parent may apply the central ST-SKILL-08-06 and
TASK-SKILL-08-06-01 readiness transitions. After central story readiness, the
user-approved one-time PR-0417 direct-`main` bootstrap may execute exactly its
three-file tracked write set and setup/worktree proof. Do not change local
EPIC-38, ST-38-01, PR, or review frontmatter/status fields. Do not start
PR-0418 through PR-0421. TASK-SKILL-08-06-02 remains separately
`changes_requested` and must be repaired before its later readiness.

### Reviewed Scope And Authority

- Reviewed: EPIC-38, ST-38-01, PR-0417 through PR-0421, this review record,
  local AGENTS/docs contract/templates/review workflow/handoff routing, Skill
  Repository ST-SKILL-08-06 and TASK-SKILL-08-06-01/02, retained Skriptoteket
  discovery, and supplied validation evidence.
- Governing authority: EPIC-SKILL-08, verified ST-SKILL-08-05, user-approved
  SKR-001 through SKR-004R, the approved serialized direct-main exception, the
  approved central ST-SKILL-08-06 story review at
  `2026-07-31T09:35:49+02:00`, and the historical migration workflow/runbook.
  This retained local review remains a legacy machine-nonauthoritative record
  until PR-0418 semantically migrates the nonterminal spine.

### Residual Risk

- The review frontmatter remains `pending` and local lifecycle fields remain
  blocked and machine-nonauthoritative until PR-0418 migration. This body
  approval records plan fit only; no guard bypass, manual local status
  transition, or retroactive authorization is allowed.
- TASK-SKILL-08-06-02 still omits four old-path match dispositions. That later
  central task remains `changes_requested`; PR-0421 already gates on its
  terminal approved completion, so the gap does not authorize or block the
  exact PR-0417 bootstrap.
- No implementation test, installed 0.9.2 proof, migration phase, relocation,
  unscoped check, or broad repository suite ran. Supplied Skriptoteket
  `docs-validate`, `handoff-validate`, and diff-check results were accepted
  without duplication.
- The retained source inventory is a planning basis, not the final sealed
  corpus manifest. Corpus drift, an unresolved terminal-ancestry dependency,
  or a source without an authority-backed disposition remains a mandatory
  stop.

## Changes Made

The reviewer recorded body-only approval of the repaired local plan. The
user-approved one-time direct-`main` exception and approved central story
review authorize only PR-0417 bootstrap; local legacy frontmatter/lifecycle
stays pending/blocked and machine-nonauthoritative until PR-0418 migration. No
local lifecycle or implementation surface changed.
