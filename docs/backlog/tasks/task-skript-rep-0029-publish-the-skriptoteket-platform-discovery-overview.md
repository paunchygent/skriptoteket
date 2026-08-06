---
type: task
id: TASK-SKRIPT-REP-0029
title: Publish the Skriptoteket platform discovery overview
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-03'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-08-03T10:00:00+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directive of 2026-08-03 ordered the three remaining ST-SKILL-08-09 conformance slices; every ledger row derives from that accepted parent story (CON-003, CON-004, CON-005) and the Discovery Docs And Codemap Placement policy. No independent plan-document-reviewer ran in this session.
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-code-review
  decided_at: '2026-08-06T19:57:01+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: /Users/olofs_mba/Documents/Repos/skill-repository/.orchestration/context/sessions/019fd7fc-7a82-7ba2-919a-9685e613c1f7/evidence/reviews/TASK-SKRIPT-REP-0029/ruthless-code-review.md
task_kind: repository
acceptance_criteria:
  - The .codex/skills/ lane carries a codemap-style skill whose references publish the platform discovery overview covering the backend layers, curated apps, runner, frontend workspace, and docs topology
  - The overview is reachable from AGENTS.md routing without duplicating route tables
  - Docs validation, skills validation, markdown checks on changed files, and git diff --check pass
contract_version: 2
---

## Implementation Contract

Publish one repository-local `.codex/skills/repo-code-map/` router and platform
overview for Skriptoteket. The overview maps the backend layers, curated apps,
sandboxed runner, frontend workspace, governed docs, ownership boundaries, and
delivery surfaces from date-bound repository state. `AGENTS.md` provides one
route to the local skill.

Keep this slice overview-only. Link the existing frontend design-system,
tool-editor, runner-modularization, and exam-converter depth maps at their
current repository-relative paths. Do not move them, restate their detail, or
change product, runtime, migration, or deployment behavior.

## Contract Inputs

- Accepted parent story `ST-SKILL-08-09`, especially CON-003 through CON-005
  and its overview-only non-goal.
- The shared Discovery Docs And Codemap Placement policy.
- Skriptoteket repository state and discovery evidence dated 2026-08-03.
- The existing `docs/reference/` depth maps and
  `docs/templates/template-codemap.md`.
- The existing retained execution-sequencing record at
  `.orchestration/context/sessions/019fd7fc-7a82-7ba2-919a-9685e613c1f7/evidence/planning/CLOSEOUT-RECONCILIATION/plan.md`
  in the Skill Repository. Planning evidence and alternatives remain there;
  this task carries only accepted contract terms.

## Proof

- Proof mode: validator proof (SDO-006).
- Pre-change: `.codex/skills/` holds three skills and no discovery overview;
  `pdm run skills-validate` exit 0 and `pdm run docs-validate` exit 0 on the
  unchanged tree.
- Post-change: the lane and overview exist, are routed from `AGENTS.md`, and
  the same gates pass.
- Initial implementation evidence: the lane was added with exactly its router
  and overview, `AGENTS.md` received one route, and `skills-validate`,
  `docs-sync`, `docs-validate`, changed-file `check-md`, and
  `git diff --check` exited 0 before independent review.
- Review repair evidence: the four promised depth-map paths are now direct
  Markdown links, and `migrations/versions/` contains 84 Python revision files
  for the overview's declared 2026-08-03 inventory.
- Repair validation: `format-md` selected both changed authored Markdown files;
  `docs-sync`, `skills-validate`, affected `docs-validate`, changed-authored-file
  `check-md`, and `git diff --check` exited 0. No CI or product tests ran.
- Same-reviewer closeout re-review approved the exact repair diff at
  `2026-08-06T19:57:01+02:00`; the retained review path is named by the
  `closeout_review.approval_evidence` mapping.

## Validation

- `pdm run skills-validate`
- `pdm run format-md <changed authored Markdown files>`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run check-md <changed files>`
- `git diff --check`

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.
- Stop if closeout would require changing the reviewer-owned verdict, marking
  the task done, or running product, runtime, deployment, or CI proof.

## Decided Contract Terms

| ID      | Decided contract term                                                                                                                                                                        |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDO-001 | The overview lives in `.codex/skills/repo-code-map/` as a minimal `SKILL.md` router plus `references/platform-discovery-overview.md`.                                                        |
| SDO-002 | The lane is overview-only because Skriptoteket is one layered product rather than a service fan-out.                                                                                         |
| SDO-003 | The overview links the four existing `docs/reference/` depth-map families and neither moves nor restates them; `docs/templates/template-codemap.md` remains their authoring template.        |
| SDO-004 | The overview covers backend layers, curated apps, the sandboxed runner, frontend workspace, docs topology, and delivery surfaces from repository state with an as-of marker.                 |
| SDO-005 | One `AGENTS.md` route makes the overview reachable.                                                                                                                                          |
| SDO-006 | Validator proof is `skills-validate`, `format-md` before `docs-sync`, affected `docs-validate`, changed-authored-file `check-md`, and `git diff --check`; product and CI gates are excluded. |

## Plan Document Review

Readiness is approved under `agent-planning:user-closure-gate`. The user
directive of 2026-08-03 ordered the remaining `ST-SKILL-08-09` consumer slices,
and SDO-001 through SDO-006 derive from that accepted parent contract and the
placement policy. No independent plan-document-reviewer ran, so readiness rests
on user closure and parent-contract derivation.

## Closeout Review

- Decided at: `2026-08-06T19:57:01+02:00`.
- Reviewer: `ruthless-code-review` (same fixed reviewer).
- Decision: `approved`.
- Reviewed scope: changed files since the initial review only, at diff digest
  `ead75bd01ffbf43f57d06bd1fe75ecacda3e5a38fead8e5bda40818f8c565be9`
  over clean current `main` `ffacab576dee317533fbabafd442412beee0d61d`.
- Findings: none. The v2 authority gap, missing depth-map links, and incorrect
  migration count from the initial review are resolved.
- Generated evidence: the broad `docs/repository-index.json` churn adds
  package-generated `retired_ids` projections and the source-set digest without
  changing document or per-type counts; normalized comparison found no other
  semantic delta.
- Validation inspected: supplied successful `format-md`, `docs-sync`,
  `skills-validate`, affected `docs-validate`, changed-authored-file `check-md`,
  and `git diff --check`. The reviewer did not duplicate these gates.
- Validation not run: CI, lint, typecheck, tests, browser, product runtime,
  deployment, database, Hemma, and repository-wide validation.
- Residual risk: approval relies on supplied current-package generator and
  validator evidence for the generated `retired_ids` projection; no product
  runtime changed.
- Permitted next step: the governing parent may preserve this decision, refresh
  generated projections after the approval mapping, validate affected docs and
  whitespace, and apply the separate terminal task transition under
  `agent-overseer:approved-review-closeout`.
