---
type: task
id: TASK-SKRIPT-REP-0001
title: Publish product context reference for external architect agents
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-07-31T15:48:06+02:00'
closeout_review:
  record: inline
  status: not_started
task_kind: repository
links:
  references:
    - REF-SKRIPT-GENERAL-product-context
acceptance_criteria:
- 'A governed reference publishes Skriptoteket''s durable product context: mission,
  identity, current aim, non-goals, load-bearing decisions, constraints, and glossary.'
- The reference states only current truth, links ADRs and PRDs instead of restating
  them, and carries a last-reconciled marker.
- Docs sync and docs validation pass for the new surfaces.
---

## Context

The product owner uses an external lead-architect assistant (a Custom GPT
reading through a read-only repository service) and fresh agent sessions that
need product grounding before planning. Skriptoteket's rationale layer —
mission, identity realms, current aim, rejected directions, load-bearing
decisions, constraints, vocabulary — is scattered across PRDs, ADRs, and dated
direction memos, and some of it exists only as owner knowledge. External
advisers reading code alone re-propose rejected directions and misread
implemented-but-`proposed` ADRs. This task publishes one governed
product-context reference as the durable entry point after the cross-repository
portfolio manifest.

## Impact And Escalation

The affected surface is governance prose: one new `general` reference in
`docs/reference/` and this governing task. No product behavior, backend,
frontend, or deploy changes. No escalation to an epic or story is required.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID      | Type   | Status | Question/Assumption                                     | Recommendation/Decision                                                                                                                                                                | Source                                        |
| ------- | ------ | ------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| SPC-001 | scope  | closed | What does the reference cover?                          | One `general` reference at `docs/reference/ref-skript-general-product-context.md`: mission, identity, deployment constraints, glossary, routing, current aim, non-goals, load-bearing decisions, metadata-drift caveats, reconciliation rule. | User approval in session chat, 2026-07-31     |
| SPC-002 | source | closed | Where do the facts come from?                           | Repository documentation (README, AGENTS.md, PRDs, ADRs, direction memos, backlog state, `.codex/handoff.md`) gathered by bounded read-only discovery; the single-operator constraint is owner-supplied and is labeled as such in the reference. | Retained discovery evidence, 2026-07-31       |
| SPC-003 | links  | closed | How are related documents referenced?                   | Governing-task and key document relations use contract-owned `links` frontmatter; in-body citations use markdown links to repo-relative paths, not bare code spans.                     | Plan Document Review finding 3 remediation    |
| SPC-004 | truth  | closed | How are unpublished or in-flight dependencies stated?   | Cross-repository documents not yet published at their canonical path are stated as pending drafts; EPIC-38 state is described per the current handoff (approved central review, user exception for PR-0417, slices gated on the PR-0418 migration). | Plan Document Review finding 2 remediation; `.codex/handoff.md`, 2026-07-31 |
| SPC-005 | proof  | closed | What proves this prose-only change?                     | Validator proof: `pdm run docs-sync`, scoped `pdm run docs-validate` over the two new files, `git diff --check`. The pre-existing tree-wide `docs/mockups/INDEX.md` failure is owned by the PR-0418 migration and is out of scope.               | Proof-selection rules; Plan Document Review residual-risk note |
| SPC-006 | gate   | closed | What gates publication?                                 | The reference stays `draft` and the task stays `proposed` until independent plan re-review returns `approved`; lifecycle transitions belong to their owners afterward.                   | Review-gates decision contract                 |

## Plan

Write the product-context reference with the Overview / Facts And Semantics /
Decisions And Interpretation shape from retained discovery evidence, honoring
SPC-002 through SPC-004; add contract-owned relationship metadata; stage the
coherent task-plus-reference change set; refresh generated indexes; run the
scoped validation; return for re-review.

## Implementation Steps

1. Scaffold this governing task and the `general` reference with
   `pdm run new-doc`.
2. Write the reference body from retained discovery evidence per the closed
   ledger.
3. Repair review findings: current-truth statements (SPC-004) and document
   links plus relationship metadata (SPC-003).
4. Stage the change set, refresh generated indexes, and run validation.
5. Return the change set for independent plan re-review.

## Proof

- Selected proof mode: validator proof (SPC-005). Applicability basis: the
  change set is prose-only governed documentation; contract conformance and
  index freshness are the complete observable behavior.
- Post-change commands and expected results: `pdm run docs-sync` regenerates
  indexes including the new reference; scoped
  `pdm run docs-validate docs/reference/ref-skript-general-product-context.md docs/backlog/tasks/task-skript-rep-0001-publish-product-context-reference-for-external-architect-agents.md`
  exits zero; `git diff --check` reports nothing.

## Validation

- `pdm run docs-sync`
- `pdm run docs-validate docs/reference/ref-skript-general-product-context.md docs/backlog/tasks/task-skript-rep-0001-publish-product-context-reference-for-external-architect-agents.md`
- `git diff --check`

Results 2026-07-31: scoped docs-validate passed for both files; docs-sync
regenerated the backlog and reference indexes; `git diff --check` clean. The
tree-wide `docs/mockups/INDEX.md` frontmatter failure pre-exists this change
set and belongs to the PR-0418 migration.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.
- A reference claim that cannot be traced to repository documentation or an
  explicitly labeled owner-supplied statement.

## Lessons Learned

The first review round failed on an unfilled task contract and two
current-truth defects: cross-repo dependencies must be stated as pending until
published, and in-flight governance state must be restated from the current
handoff, not paraphrased from memory.

## Notes

The reference is consumed outside this repository by the owner's external
lead-architect assistant through the portfolio manifest in the skill
repository; path stability of
`docs/reference/ref-skript-general-product-context.md` matters more than usual
for a reference.

## Readiness

- Ledger: SPC-001 through SPC-006 closed; no open material decisions.
- Authority: user approval in session chat 2026-07-31 plus this task contract.
- Evidence: Validation section results, 2026-07-31.
- Permitted next step: independent plan re-review of the tracked
  task-plus-reference change set.
- Residual risk: the "Current aim" section is a dated snapshot; the
  reference's reconciliation rule and last-reconciled marker bound that
  staleness.

## Plan Document Review

- Recorded: `2026-07-31T15:48:06+02:00` (`CEST`).
- Reviewer: `plan-document-reviewer`.
- Decision: `approved`.
- Reviewed scope:
  `docs/backlog/tasks/task-skript-rep-0001-publish-product-context-reference-for-external-architect-agents.md`
  and `docs/reference/ref-skript-general-product-context.md`, limited to the
  changes since the prior pass and the supplied scoped docs-validation and
  diff-hygiene evidence.
- Governing authority: this task's acceptance criteria, the canonical task and
  reference artifact shapes, the repository-task and reference templates, the
  open-question ledger, proof-selection rules, and
  `agent-docs-governance/references/review-gates-and-decision-records.md`.
- Findings: none. The repository-task contract is single-responsibility and
  decision-complete; SPC-001 through SPC-006 are closed; validator proof is
  appropriate for the prose-only change; the reference states the unpublished
  portfolio dependency and current EPIC-38 gate truthfully; and its metadata
  plus markdown links preserve backlog, ADR, PRD, and reference authority.
- Permitted next step: the owning parent may apply the task readiness transition
  and continue the owner-managed publication lifecycle for the reviewed
  reference.
- Status transition: this decision permits `proposed -> ready` for the task.
  Reference publication remains an owner-applied lifecycle action; this review
  does not change either lifecycle state.
- Residual risk: the reviewer did not rerun supplied mechanical gates. Supplied
  evidence says scoped `pdm run docs-validate` passes for the two new source
  files and `git diff --check` is clean. Tree-wide docs validation remains
  blocked by the pre-existing `docs/mockups/INDEX.md` frontmatter failure owned
  by the PR-0418 migration; that unrelated failure is not a required change for
  this task.

## Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.
