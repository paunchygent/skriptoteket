---
type: task
id: TASK-SKRIPT-REP-0028
title: Expose local codex skills to the Claude harness via claude skills symlink
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-03'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-08-03T01:00:23+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User opened the symlink lane on 2026-08-03 and the ledger closes on that directive plus policy and discovery evidence; independent plan-document-reviewer subagent approved round 1 with no blocking findings.
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-code-review
  decided_at: '2026-08-03T01:58:29+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent closeout subagent (not the implementer) verified the symlink resolution, all three SKILL.md reads, gate exits, and scope; approved with zero blocking findings.
task_kind: repository
acceptance_criteria:
  - A committed relative symlink at .claude/skills resolves to .codex/skills so the Claude harness discovers local skills at session start
  - Every local skill SKILL.md is readable through the symlinked path
  - Docs validation and markdown gates pass and git diff --check is clean
---

## Context

The Claude Code harness discovers skills only under `.claude/skills/` and does
not load the repo's three local skills in `.codex/skills/`
(`pinball-board-authoring`, `skriptoteket-backend-dev`,
`skriptoteket-testing`). The shared Discovery Docs And Codemap Placement
policy delivers local skills to such harnesses by symlink from the local skill
source into the harness folder. `.claude/` does not exist yet and is not
gitignored.

## Impact And Escalation

The affected surface is one committed symlink under a new `.claude/`
directory. No product behavior, service, frontend, or deploy changes. No
escalation to an epic or story is required.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID      | Type      | Status | Question/Assumption                      | Recommendation/Decision                                                                                                              | Other highly plausible options               | Motivation                                                                                                                                                | Source                                      |
| ------- | --------- | ------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| SYM-001 | scope     | closed | Which skills are exposed to the harness? | All local `.codex/skills/` skills, via one link covering the whole folder.                                                           | Expose only actively used skills.            | Partial exposure recreates discovery drift; the user opened the lane for local-skill discovery as such.                                                   | User direction in session chat, 2026-08-03  |
| SYM-002 | mechanism | closed | Directory symlink or per-skill symlinks? | One committed relative symlink `.claude/skills -> ../.codex/skills`.                                                                 | Per-skill symlinks inside `.claude/skills/`. | A single durable link keeps one authored source and auto-covers future skills per the delivery policy; per-skill links only matter when sources mix.      | Discovery Docs And Codemap Placement policy |
| SYM-003 | tracking  | closed | Is the symlink committed?                | Yes, committed.                                                                                                                      | Leave it untracked as local machine state.   | `.claude` is unignored; a committed link serves every clone.                                                                                              | Discovery evidence, 2026-08-03              |
| SYM-004 | proof     | closed | What proves the change?                  | Validator proof: the link resolves, every `SKILL.md` is readable through it, docs and markdown gates pass, `git diff --check` clean. | Live harness-session discovery proof.        | Harness session start is manual; structural resolution through the link is the automatable observable. Live discovery is confirmed at next session start. | Proof-selection rules                       |

## Plan

Create `.claude/` with the relative symlink `.claude/skills -> ../.codex/skills`, commit it, and verify resolution and gates. Live harness
discovery is confirmed by the user's next Claude session in this repo.

## Implementation Steps

1. `mkdir .claude && ln -s ../.codex/skills .claude/skills` from the repo
   root.
2. Verify every local skill's `SKILL.md` is readable through the link.
3. Run the validation commands listed below.

## Proof

- Proof mode: validator proof (SYM-004).
- Pre-change: `.claude/` does not exist.
- Post-change: `ls .claude/skills/` lists the three skills and each
  `SKILL.md` reads through the link.

## Validation

- `pdm run docs-validate docs/backlog/tasks/task-skript-rep-0028-expose-local-codex-skills-to-the-claude-harness-via-claude-skills-symlink.md`
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

- Ledger closure: SYM-001 through SYM-004 closed; no open rows.
- Authority evidence: the user opened the symlink lane in the working session
  of 2026-08-03 (session chat; recorded here as the durable authority).
  Mechanism and delivery direction close on the shared placement policy.
- Plan review: round 1 approved (2026-08-03, delegated plan-document-reviewer
  subagent); all on-disk factual claims verified, both docs gates exit 0.
- Permitted next step: delegated implementation by a subagent that is not the
  reviewer, on explicit user implementation authority.
- Residual risk: live harness discovery is confirmed only at the user's next
  Claude session start in this repo.

## Closeout

- Supplied proof: `readlink .claude/skills` returns `../.codex/skills`; all
  three skills' `SKILL.md` read through the link; scoped `docs-validate` and
  `check-md` exit 0; `git diff --check` exit 0; `git check-ignore` exit 1
  proves committability. `.claude/` contains exactly the symlink.
- Findings: independent closeout review approved with zero blocking findings.
- Permitted next step: parent integration and push; live harness discovery
  confirmed at the user's next Claude session in this repo.
- Validation not run: none beyond the contract's deferral of live-session
  proof.
- Residual risk: none beyond the recorded live-discovery deferral.
