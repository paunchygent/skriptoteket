---
type: task
id: TASK-SKRIPT-40-03-09
title: Fold the remaining .codex/rules facts into their owning skills and route agent instruction through skills only
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (Sol) reviews in the retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/TASK-SKRIPT-40-03-09/: review afcdc94a (changes requested, F1 codemap rule-045 authority, F2 dead runbook paths), rereview a9a1bca3 (F2 cleared, F1 open on proposed ADR-0017), rereview 707c6992 approved. Shared-skill half merged to skill-repository main 4139f6d9. Accepted exceptions, accepted by the parent: 16 historical docs keep their rule references, the generated index quotes the task title, the .gitignore entry for the ignored rule-080 file stays until the user deletes that file, and the private rule-094 server values stay withheld as a user decision. The parent authorized closure.'
task_kind: story
acceptance_criteria:
  - Skriptoteket has no .codex/rules; every still-valid rule fact lives in the skill that owns its topic, and AGENTS.md and CLAUDE.md route agent instruction through skills only
story: ST-SKRIPT-40-03
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket is the only repository that still keeps agent rules beside its
skills. Skills are the only just-in-time instruction route, so this task
removes the rule system.

This task delivers:

- Every still-valid fact in the files under `.codex/rules` moves to the skill
  that owns its topic: a repo-local skill under `.codex/skills/`
  (`repo-code-map`, `skriptoteket-backend-dev`, `skriptoteket-testing`,
  `pinball-board-authoring`) or the Skriptoteket reference of the owning shared
  skill in the canonical skill repository (the shared skills that CLAUDE.md
  routes to). Facts that are no longer true are dropped.
- Rule 045 (`045-huleedu-design-system.md`) is not carried over:
  `huleedu-ui-design` owns presentation, and the `integrated-frontend-stack`
  Skriptoteket reference owns the local token and sync facts.
- `.codex/rules` is deleted: 22 tracked files and the ignored
  `080-home-server-deployment.md`, together with its `.gitignore` entry.
- Every rule reference in docs, skills and CLAUDE.md is deleted, except the
  ST-SKRIPT-40-03 story and task documents that state this removal. Today
  tracked files outside `.codex/rules` name `.codex/rules` in 53 backlog
  documents (this story included), 8 reference documents and 1
  long-term-memory entry. AGENTS.md and CLAUDE.md
  name no rule path today; they keep routing through skills only.
- CLAUDE.md names `huleedu-ui-design` for design work.

## Contract Inputs

- ST-SKRIPT-40-03 term S5; retained plan
  `.orchestration/context/sessions/01a13082-a8f9-7137-aa65-848f7e3c53c2/evidence/planning/ST-SKRIPT-40-03/plan.md`.
- The rule files: `.codex/rules/000-rule-index.md` through
  `.codex/rules/094-observability-infrastructure.md`.
- Repo-local skills in `.codex/skills/` and the Skriptoteket references of the
  shared skills routed in CLAUDE.md, edited in the canonical skill repository
  through the `skill-repository` alias.

## Core Vertical And Performance

An agent starts a Skriptoteket session, reads AGENTS.md and CLAUDE.md, and
reaches each Skriptoteket fact it needs (for example a migration or a testing
fact that used to live in a rule) through the skill that owns the topic. No
file names `.codex/rules`. No runtime code changes.

## Validation

- `pdm run skills-validate` and `pdm run docs-validate`.
- `git grep -n ".codex/rules"` finds no tracked reference outside the
  ST-SKRIPT-40-03 story and task documents, and `.codex/rules` does not exist.

## Stop Conditions

- A still-valid fact is a credential or a private server detail (the ignored
  `080-home-server-deployment.md` holds sensitive operational details): report
  to the user before writing it into any tracked skill.
- A fact has no owning skill: report to the user before creating a skill for it.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S5  | Every still-valid fact under `.codex/rules` moves to the skill that owns its topic (a repo-local `.codex/skills` skill or the Skriptoteket reference of the owning shared skill); then `.codex/rules`, the rule-index route in AGENTS.md and every rule reference in docs, skills and CLAUDE.md are deleted. Source: ST-SKRIPT-40-03 S5 (user 2026-10-12). |
| S5a | Rule 045's design content is not carried over: huleedu-ui-design owns presentation and the integrated-frontend-stack Skriptoteket reference owns the local token and sync facts; CLAUDE.md names huleedu-ui-design for design work. Source: ST-SKRIPT-40-03 S5 (user 2026-10-12).                                                                          |
| S7  | The rule replacement may run any time before TASK-SKRIPT-39-04-05; G1 replaces that task with ST-SKRIPT-40-04. It has no ordering constraint against the area refreshes. Source: ST-SKRIPT-40-03 S7 (user 2026-10-12); G1 (user 2026-10-17).                                                                                                               |
