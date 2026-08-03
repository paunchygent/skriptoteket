---
type: task
id: TASK-SKRIPT-REP-0029
title: Publish the Skriptoteket platform discovery overview
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-03'
status: in_progress
readiness_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-08-03T10:00:00+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directive of 2026-08-03 ordered the three remaining ST-SKILL-08-09 conformance slices; every ledger row derives from that accepted parent story (CON-003, CON-004, CON-005) and the Discovery Docs And Codemap Placement policy. No independent plan-document-reviewer ran in this session.
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The .codex/skills/ lane carries a codemap-style skill whose references publish the platform discovery overview covering the backend layers, curated apps, runner, frontend workspace, and docs topology
  - The overview is reachable from AGENTS.md routing without duplicating route tables
  - Docs validation, skills validation, markdown checks on changed files, and git diff --check pass
---

## Context

The Discovery Docs And Codemap Placement policy in the shared
`agent-docs-governance` skill requires every governed repo to carry one platform
discovery overview in its repo-local skills lane. Skriptoteket carries none.
`.codex/skills/` holds three narrow skills (`pinball-board-authoring`,
`skriptoteket-backend-dev`, `skriptoteket-testing`), and `docs/reference/`
holds domain-scoped codemaps for the frontend design system, the tool-editor
framework, and runner-tool modularization. No surface states the repository's
whole topology, so a fresh agent session has no single entry point.

The cross-repo sequence is organized in skill-repository story ST-SKILL-08-09;
this task executes only the Skriptoteket file mutation.

## Impact And Escalation

The affected surfaces are repository-governance prose: a new
`.codex/skills/repo-code-map/` lane and one route line in `AGENTS.md`. No
product behavior, backend, frontend, runner, migration, or deploy change. No
escalation to an epic or story is required.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID      | Type      | Status | Question/Assumption                                      | Recommendation/Decision                                                                                                                                                                          | Source                                                              |
| ------- | --------- | ------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| SDO-001 | target    | closed | Where does the overview live?                            | A new `.codex/skills/repo-code-map/` skill: `SKILL.md` router plus `references/platform-discovery-overview.md`, mirroring the hub's own lane and HuleEdu's `service-code-map` shape.             | Discovery Docs And Codemap Placement policy; ST-SKILL-08-09 CON-003 |
| SDO-002 | depth     | closed | Overview only, or a full codemap lane?                   | Overview only. Skriptoteket is one layered monolith, not a service fan-out, so the lane carries a single map.                                                                                    | ST-SKILL-08-09 CON-004                                              |
| SDO-003 | prior art | closed | What happens to the existing `docs/reference/` codemaps? | Scope around them: the overview links to them as existing depth maps and neither moves nor restates them. `docs/templates/template-codemap.md` stays the authoring template for those docs.      | ST-SKILL-08-09 CON-004 and its Non-Goals                            |
| SDO-004 | content   | closed | What does the overview cover, from where?                | Authored from repository state with an as-of marker: backend layers under `src/skriptoteket/`, curated apps, the sandboxed runner, the frontend workspace, docs topology, and delivery surfaces. | Docs Shape rules; discovery evidence 2026-08-03                     |
| SDO-005 | routing   | closed | How is the overview reachable?                           | One route line added to the `AGENTS.md` repo-specific route table.                                                                                                                               | Entrypoint-design reference; placement policy                       |
| SDO-006 | proof     | closed | What proves this prose-only slice?                       | Validator proof: `skills-validate` (it enumerates `.codex/skills/`, so the new lane is covered), `docs-validate`, `check-md` on changed files, and `git diff --check`.                           | ST-SKILL-08-09 CON-005; proof-selection rules                       |

## Plan

Create `.codex/skills/repo-code-map/` with a minimal `SKILL.md` router and
author `references/platform-discovery-overview.md` from repository state
(topology, ownership boundaries, delivery surfaces, links to existing
authoritative references instead of restated prose, an as-of marker), add one
`AGENTS.md` route line, and run the validation gates.

## Implementation Steps

1. Create `.codex/skills/repo-code-map/SKILL.md` as a minimal router to the
   overview reference.
2. Author `references/platform-discovery-overview.md` with an as-of marker;
   link to existing references rather than duplicating them.
3. Add one route line to the `AGENTS.md` repo-specific route table.
4. Run the validation commands listed below.

## Proof

- Proof mode: validator proof (SDO-006).
- Pre-change: `.codex/skills/` holds three skills and no discovery overview;
  `pdm run skills-validate` exit 0 and `pdm run docs-validate` exit 0 on the
  unchanged tree.
- Post-change: the lane and overview exist, are routed from `AGENTS.md`, and
  the same gates pass.

## Validation

- `pdm run skills-validate`
- `pdm run docs-validate`
- `pdm run check-md <changed files>`
- `git diff --check`

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Readiness

- Ledger closure: SDO-001 through SDO-006 all closed against the accepted
  ST-SKILL-08-09 contract and the Discovery Docs And Codemap Placement policy.
  No material choice was left to implementation.
- Authority evidence: user directive of 2026-08-03 to run the three remaining
  conformance slices, plus the parent story's approved readiness review.
- Permitted next step: implement the two-file lane and the one-line
  `AGENTS.md` route, then run the validation gates.
- Residual risk: no independent plan-document-reviewer ran in this session, so
  the readiness gate rests on user closure and parent-contract derivation
  alone.

## Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

- Supplied proof (implementer-reported, pending independent review):
  `.codex/skills/repo-code-map/` created with exactly the two contracted files;
  the `AGENTS.md` diff is one inserted route line; `pdm run skills-validate`
  enumerates the new lane as the fourth local skill; `pdm run docs-sync` and
  `pdm run docs-validate` exit 0; `pdm run check-md` exit 0 on all four changed
  files; `git diff --check` exit 0.
- Validation not run: repository quality gates (`lint`, `typecheck`, `test`)
  are not applicable — no Python or TypeScript source changed.
