---
type: pr
id: PR-0389
title: "ST-37-04 shared-auth local proof path cleanup"
status: done
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-04"
tags: ["auth", "local-dev", "docs", "cleanup"]
dependencies:
  - "PR-0283"
  - "PR-0364"
  - "PR-0388"
acceptance_criteria:
  - "Given local authenticated Skriptoteket proof uses the HuleEdu shared-auth lane, when docs, skills, runbooks, and proof scripts reference the provider export, then the only active local export path is `local-shared-verify-export.json`."
  - "Given unsupported HuleEdu subject-export names may target older local Identity DB generations, when an operator or proof script attempts to use one, then the active proof lane fails closed with a clear diagnostic instead of producing `identity_linking_required` confusion."
  - "Given retained review docs may contain historical command evidence, when this cleanup closes, then no retained doc leaves a runnable-looking stale local proof command without a current replacement."
  - "Given route-visible authenticated proof depends on local projection/RBAC truth, when preflight is documented or invoked, then it verifies against the current shared export and reports green without requiring manual tribal knowledge."
---

# PR-0389: ST-37-04 Shared-Auth Local Proof Path Cleanup

## Problem

The current local auth lane has one correct shared provider export:
`local-shared-verify-export.json`. Older docs and proof defaults could point to
obsolete local export artifacts from a different HuleEdu Identity DB generation
and reproduce a false `identity_linking_required` failure in Skriptoteket.

This creates exactly the wrong operator contract: a developer can follow a
runnable-looking command from a trusted repo surface and end up debugging stale
state instead of the real local browser-session ceremony.

## Goal

Make the current shared-auth local proof path singular and fail-closed:

- active docs, runbooks, skills, and proof scripts point to
  `local-shared-verify-export.json`;
- unsupported HuleEdu subject-export names are rejected by active proof tooling
  with an operator-readable message;
- historical retained docs either use the current command or clearly stop
  presenting the old path as runnable guidance.

## Non-goals

- No auth contract redesign.
- No HuleEdu Identity mutation from Skriptoteket.
- No local DB reset or migration.
- No new browser login behavior.
- No production credential, session, CSRF, or Gateway signing changes.

## Implementation plan

1. [x] Update active Skriptoteket docs and skill surfaces to use
   `local-shared-verify-export.json`.
2. [x] Update the PR-0254 auth-cutover proof default artifact path.
3. [x] Add a guard that rejects unsupported HuleEdu subject-export names when
   passed through the active proof script.
4. [x] Update focused tests for the current default and unsupported-name
   rejection.
5. [x] Patch retained review command examples so they do not remain
   runnable-looking stale guidance.

## Implementation notes

- The existing worktree already contained the production/script behavior change
  this slice needed: `scripts/playwright_pr_0254_auth_cutover.py` now defaults
  to `local-shared-verify-export.json` and fails closed on unsupported
  HuleEdu subject-export names.
- The focused pytest coverage already present in
  `tests/unit/application/auth/test_pr_0254_auth_cutover_config.py` is
  sufficient for that behavior. The remaining work in this session was an audit
  plus docs/runbook/handoff hardening.
- Historical retained docs describe obsolete export failures without naming a
  deleted artifact path as a runnable input.

## Verification notes

- Repo audit confirmed no active repo command, script default, runbook, repo
  skill, handoff note, or retained review command still endorses
  obsolete local export artifacts.
- No additional production-code edit was required after the audit, so there was
  no new red-first behavior change to land beyond the existing script/test work
  already in the worktree.
- Validation results:
  - `pdm run test tests/unit/application/auth/test_pr_0254_auth_cutover_config.py`: passed.
  - `pdm run test tests/unit/application/auth/test_pr_0254_provider_lane_preflight.py`: passed.
  - `pdm run docs-validate`: passed.
  - `pdm run skills-validate`: passed.
  - `pdm run handoff-validate`: passed after trimming `.codex/handoff.md` back under the 200-line budget.
  - `pdm run lint`: passed.
  - `pdm run typecheck`: passed.
  - `git diff --check`: passed.

## Scope clarifications

- This slice does not mutate HuleEdu runtime state, reset local databases, or
  redesign auth flows.
- The shared `local-devops` skill references in `skill-repository` were cleaned
  in the same hygiene pass so provider and consumer instructions agree on the
  current shared export artifact.
- HuleEdu-owned historical docs remain outside this Skriptoteket PR slice unless
  a later governed HuleEdu cleanup is explicitly opened.

## Test plan

- Focused pytest for the PR-0254 proof script configuration.
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert this cleanup only if HuleEdu intentionally promotes a new sanitized
export path and updates the shared-auth provider lane at the same time. Do not
restore obsolete local export artifacts as active defaults.
