---
type: task
id: TASK-SKRIPT-REP-0058
title: Sittplatser toolbar labels never wrap on a phone
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-29'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-29'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Light route, no review. Merged a58dc8ed8, deployed to production at ecf66f5e1 and again at dad31d98e. The user checked on their iPhone in production on 2026-10-29: Nytt and Avancerade inställningar each show on one line.'
task_kind: repository
acceptance_criteria:
  - At 390 px the Sittplatser toolbar button Nytt utkast shows its label on one line
  - At 390 px the Avancerade inställningar item in the Sittplatser toolbar overflow menu shows its label on one line
backlog_document_profile: contract-derived
---

## Implementation Contract

The Mac staging walk of TASK-SKRIPT-REP-0057 at `cbbf5d969` (390x844, touch) found two labels in Klassrumskartan's
Sittplatser toolbar that break onto two lines: the "Nytt utkast" button (79 px wide) and the "Avancerade
inställningar" item in the toolbar's overflow menu (190 px). `huleedu-ui-design` says button labels never wrap
and actions stay in one row.

- Actor: a teacher using Sittplatser on a phone.
- Change: both labels stay on one line at 390 px. The toolbar button follows the skill's narrow-width rule (label
  shortened or glyph carries the meaning, no wrap); the overflow menu is wide enough for its longest item, within
  the screen.
- Non-goals: other toolbars (the walk found no other wrap), desktop and tablet layouts.

## Contract Inputs

- Mac walk record `~/Repos/Skriptoteket/.artifacts/staging-walk-rep-0057-cbbf5d969/walk-record.md` (item 5).
- TASK-SKRIPT-REP-0057 D6; `huleedu-ui-design` visual-system button rules.

## Core Vertical And Performance

One junior unit: the Sittplatser phone toolbar and its overflow menu. CSS and markup only.

## Validation

- A focused Vitest spec for each control that asserts its no-wrap class or label.
- A Mac staging check at 390x844 that both labels are on one line.

## Stop Conditions

- Keeping the button label on one line needs a toolbar redesign rather than a fix.

## Decided Contract Terms

| ID  | Decided contract term                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------ |
| D1  | Both labels stay on one line at 390 px, following the existing huleedu-ui-design button rules (REP-0057 D6). |
| D2  | Proof is a focused spec and a Mac staging check; light route, no review.                                     |
