---
type: review
id: REV-PR-0389
title: "Review: PR-0389 Shared-Auth Local Proof Path Cleanup"
status: approved
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
reviewer: "codex-independent-reviewer"
prs:
  - PR-0389
links:
  - ST-37-04
  - EPIC-37
  - PR-0364
  - PR-0388
---

# Review: PR-0389 Shared-Auth Local Proof Path Cleanup

## TL;DR

Independent review completed for the shared-auth local proof path cleanup. The
repo-scoped implementation removes obsolete local proof export guidance from
the reviewed Skriptoteket command, docs, runbook, handoff, and repo-local skill
surfaces, replaces active guidance with `local-shared-verify-export.json`, and
fails closed when an unsupported export name is passed to the PR-0254 proof
script. Focused code review, repo grep audit, and validation evidence support
approval.

## Problem Statement

The local shared-auth proof lane must have one authoritative subject-export
path. Leaving older local export artifacts active or runnable-looking in
trusted repo surfaces would send operators into a stale Identity DB lane and
recreate false `identity_linking_required` debugging. This review checks
whether `windsurf-project` now exposes exactly one active local export path and
does not preserve retired filenames as operator-facing concepts.

## Proposed Solution

Keep the cleanup narrow and fail-closed:

- point active repo-local skill, runbook, handoff, and governed PR guidance to
  `local-shared-verify-export.json`;
- update the PR-0254 Playwright proof default to the shared export path;
- reject unsupported HuleEdu subject-export names at artifact-resolution time
  with an operator-readable diagnostic; and
- describe historical export failures without preserving deleted filenames as
  runnable-looking guidance.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0389-st-37-04-shared-auth-local-proof-path-cleanup.md` | Governing scope, acceptance criteria, claimed validation, stop conditions | 20 min |
| `.codex/handoff.md` | Active worktree scope, local proof guidance, risk wording | 10 min |
| `.codex/skills/skriptoteket-backend-dev/SKILL.md` | Repo-local skill command surfaces for projection and preflight | 10 min |
| `docs/runbooks/runbook-user-management.md` | Operator-facing local bootstrap and preflight commands | 15 min |
| `scripts/playwright_pr_0254_auth_cutover.py` | Active proof default, fail-closed rejection path, CLI contract | 20 min |
| `tests/unit/application/auth/test_pr_0254_auth_cutover_config.py` | Behavioral proof for default path and unsupported-name rejection | 15 min |
| `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md` and `docs/backlog/reviews/review-pr-0364-authenticated-home-work-apps-surface.md` | Historical mention framing and stale-command cleanup | 15 min |
| `docs/index.md` | Docs-as-code discoverability for the new PR slice | 5 min |

**Total estimated time:** ~1.8 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `local-shared-verify-export.json` as the only active repo-scoped local proof export path. | Removes operator ambiguity and matches the governed PR-0389 cleanup contract. | [x] |
| Reject unsupported HuleEdu subject-export names in the active PR-0254 proof script instead of silently accepting them. | Fails closed on mismatched local Identity DB lanes and prevents misleading local auth proof. | [x] |
| Remove obsolete export identifiers from active tests and retained guidance. | Avoids keeping retired paths alive as operator concepts while preserving reviewable behavior. | [x] |
| Close the shared `local-devops` residual outside this checkout. | The user requested skill cleanup as part of the same hygiene pass. | [x] |

## Review Checklist

- [x] Governing PR-0389 acceptance criteria match the implemented cleanup scope.
- [x] The reviewed worktree removes active repo-scoped obsolete export command guidance.
- [x] The PR-0254 proof script defaults to `local-shared-verify-export.json`.
- [x] The active proof script fails closed on unsupported export names with operator-readable guidance.
- [x] Obsolete export identifiers are not preserved in active tests, handoff, runbooks, or retained review guidance.
- [x] Repo-local skill and runbook surfaces now use the shared export path.
- [x] Focused test coverage proves current default resolution and unsupported-name rejection through the config boundary.
- [x] The review created the required retained artifact for PR-0389.

## Findings

No findings. I did not identify any blocker, high, medium, low, or nit issue in
the reviewed PR-0389 repo scope.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-26`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions

None.

## Verification

- Reviewed `AGENTS.md`, `.codex/handoff.md`, `.codex/rules/070-testing-standards.md`,
  `.codex/rules/096-review-workflow.md`, `docs/index.md`, the routed
  `ruthless-code-review`, `testing`, `skriptoteket-testing`,
  `skriptoteket-backend-dev`, and `local-devops` guidance, plus the governing
  `PR-0389` doc.
- `git diff -- .codex/handoff.md .codex/skills/skriptoteket-backend-dev/SKILL.md docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md docs/backlog/reviews/review-pr-0364-authenticated-home-work-apps-surface.md docs/index.md docs/runbooks/runbook-user-management.md scripts/playwright_pr_0254_auth_cutover.py tests/unit/application/auth/test_pr_0254_auth_cutover_config.py docs/backlog/prs/pr-0389-st-37-04-shared-auth-local-proof-path-cleanup.md`
  Confirmed the implementation scope matches the PR report and stays bounded to
  docs, repo skill, handoff, one active proof script, and focused tests.
- `rg -n "local-shared-verify-export\\.json|consume-huleedu-subject-export|auth-edge-bootstrap-preflight|skriptoteket-auth-bootstrap|shared-auth" .`
  Confirmed the active repo-local skill, runbook, handoff, and governed docs
  use `local-shared-verify-export.json` for local shared-auth proof guidance.
- Repo-wide literal audit for the obsolete export identifier and
  superseded-command meta wording confirmed neither remains in the active repo
  surface after the strict follow-up cleanup.

## Residual Risks

- I did not rerun the full HuleEdu browser-session proof lane in this review
  pass. Approval relies on the bounded repo audit, focused script/test surface,
  and the validation commands listed below.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0389` | Created the retained independent review record for PR-0389. |
| 2 | `REV-PR-0389` | Recorded the repo-scope audit, validation evidence, residual external risk, and approved verdict. |

## Addendum: Shared Skill Cleanup Narrow Pass

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-26`
**Scope:** External shared-skill cleanup only:
`/Users/olofs_mba/Documents/Repos/skill-repository/skills/local-devops/references/skriptoteket.md`
and
`/Users/olofs_mba/Documents/Repos/skill-repository/skills/local-devops/references/huleedu.md`.

### Addendum Findings

No findings. The narrow shared-skill follow-up satisfies the earlier
`including skills` residual without introducing stale runnable commands,
command-wrapping drift, or provider/consumer path mismatch.

### Addendum Decision

`approved`

### Addendum Verification

- Skill-repository literal audit confirmed the obsolete export identifier has
  no remaining matches, and the only current local proof export references are
  the expected `local-shared-verify-export.json` entries in the two reviewed
  `local-devops` files.
- `git -C /Users/olofs_mba/Documents/Repos/skill-repository diff -- skills/local-devops/references/skriptoteket.md skills/local-devops/references/huleedu.md`
  Confirmed the worker changed only the obsolete export reference in the
  provider/consumer instructions plus adjacent shared-auth Docker proof notes
  in `skriptoteket.md`; no unrelated command-surface drift appeared in the
  reviewed scope.
- Reviewed
  `/Users/olofs_mba/Documents/Repos/skill-repository/skills/local-devops/references/huleedu.md:182`
  through `:185` and
  `/Users/olofs_mba/Documents/Repos/skill-repository/skills/local-devops/references/skriptoteket.md:99`
  through `:102`.
  Verified the HuleEdu provider instruction now writes
  `local-shared-verify-export.json`, and the Skriptoteket consumer/preflight
  instructions read that same current artifact path.
- Worker-reported validation evidence for `skill-repository` remains coherent
  with the reviewed scope:
  `pdm run skills-validate`,
  `pdm run docs-validate`,
  and `git diff --check` passed.

### Addendum Residual Risk

The external shared-skill residual noted earlier is closed by this narrow pass.
The strict follow-up also removes the obsolete export identifier and the
superseded-command wording from the retained repo review itself.

## Addendum: Strict Follow-Up Verification

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-26`

- Re-ran literal residue audits in both `windsurf-project` and
  `skill-repository`. The retired export identifier and retired
  command-shape wording returned zero matches in the reviewed active surfaces.
- Re-ran the focused repo proof and validation gates:
  `pdm run test tests/unit/application/auth/test_pr_0254_auth_cutover_config.py`,
  `pdm run docs-validate`,
  `pdm run handoff-validate`,
  and `git diff --check`.
- Re-ran the shared-skill validation gates:
  `pdm run skills-validate`,
  `pdm run docs-validate`,
  and `git diff --check`.
- Re-checked `PR-0389` scope wording. It correctly states that shared
  `local-devops` cleanup was completed in the same hygiene pass, while any
  separate HuleEdu-owned historical-doc cleanup would need an explicit later
  governed slice.

**Decision remains:** `approved`
