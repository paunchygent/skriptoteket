---
type: task
id: TASK-SKRIPT-REP-0038
title: Retire repository rules and route staging walks to staging-walk
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- The retired repository-rule directory is gone and no live surface references it, and every
  Skriptoteket staging or browser-proof passage is one routing line to the staging-walk
  skill with no Mac-local proof lane
backlog_document_profile: contract-derived
---

## Implementation Contract

Repository rules are retired and staging has one authority, the shared
`staging-walk` skill (TASK-SKILL-REP-0275). This task removes the Skriptoteket
copies.

- Delete the retired repository-rule directory. Repair every live reference: `AGENTS.md`,
  `.gitignore`, the two unit tests that read rule files
  (`tests/unit/web/test_openapi_contracts.py`,
  `tests/unit/scripts/test_playwright_script_surface.py`), `.codex/agents/*.toml`,
  `.codex/skills/` (`skriptoteket-backend-dev`, `skriptoteket-testing` and its
  references), the runbooks, and source comments in
  `src/skriptoteket/web/routes/` and `src/skriptoteket/observability/`.
- Replace every staging and browser-proof passage with one routing line to
  `staging-walk`: the `skriptoteket-testing` skill and its browser-automation
  reference, the staging runbook, the agent browser-automation runbook, the
  testing runbook UI walk section, and `AGENTS.md`.
- Remove the Mac-local proof lanes: the local shared-auth lane, the host Vite
  split lane, the upload-gated local dev stack and the Chrome profile launch
  for local proof. Staging runs only on Hemma.

Historical documents keep their rule mentions: backlog and PR records,
reference plans and reports, the changelog and long-term-memory entries.

## Contract Inputs

- Live reference audit of 2026-10-11 for the retired repository-rule directory and numbered rule routes.
- Staging inventory, skill-repository session
  `01a12b2b-d8bd-7fd4-b52c-76675362904a` evidence `staging-inventory.md`.
- TASK-SKILL-REP-0275 for the `staging-walk` skill name and scope.

## Core Vertical And Performance

Agent-surface and docs edits plus two unit-test repairs. No product behavior
changes.

## Validation

- `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, `git diff --check`.
- The two repaired unit tests pass.
- A reference audit for retired repository-rule routes over live surfaces returns nothing.

## Stop Conditions

- A rule holds a fact that no skill, runbook or code carries and a live
  workflow still needs.
- A test asserts product behavior through a rule file rather than only its
  presence.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Delete the retired repository-rule directory and repair every live reference; historical documents keep their mentions. |
| D2  | Every Skriptoteket staging and browser-proof passage is one routing line to `staging-walk`; Mac-local proof lanes are removed; staging runs only on Hemma. |
