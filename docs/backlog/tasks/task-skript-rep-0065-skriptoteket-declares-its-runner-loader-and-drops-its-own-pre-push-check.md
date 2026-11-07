---
type: task
id: TASK-SKRIPT-REP-0065
title: Skriptoteket declares its runner loader and drops its own pre-push check
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-07'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - "pyproject.toml declares `[[tool.repository-governance.quality.declared-loaders]]` with path `runner/_runner.py`, function `_load_module_from_path` and a reason, and `pdm run check --plan` with the runtime carrying TASK-SKILL-REP-0516 names no unresolved dynamic loader and prints a plan."
  - "The `hemma-pre-push-check` hook entry in `.pre-commit-config.yaml`, `scripts/hemma_pre_push_check.sh`, `scripts/pre_push_touches_migrations.sh`, `tests/unit/scripts/test_hemma_pre_push_check.py` and `tests/unit/scripts/test_pre_push_touches_migrations.py` no longer exist, and no file mentions them apart from this task file."
  - The installed pre-push hooks no longer run the removed script; the shared `check --pushed` hook remains the only pre-push check.
backlog_document_profile: contract-derived
---

## Implementation Contract

The released repository-governance runtime with TASK-SKILL-REP-0516 resolves
Skriptoteket's four package walks. The only remaining refused loader is
`runner/_runner.py:204` in `_load_module_from_path`, which loads a user tool
script from the runtime bundle directory and never a repository file. It is
declared in `pyproject.toml`:

```toml
[[tool.repository-governance.quality.declared-loaders]]
path = "runner/_runner.py"
function = "_load_module_from_path"
reason = "Loads the user tool entrypoint from the runtime bundle directory; never a repository module."
```

Skriptoteket's own pre-push check is removed with no replacement
(TASK-SKILL-REP-0497 D7): the hook entry, its two scripts, their tests and
every mention (`handoff.md` and
`.codex/skills/repo-code-map/references/platform-discovery-overview.md`
included). `pdm run setup` reinstalls the hooks afterwards.

## Contract Inputs

- TASK-SKILL-REP-0497 D7 (user, 7 Nov 2026) and TASK-SKILL-REP-0516 D2.

## Core Vertical And Performance

No product code changes.

## Validation

- `pdm run check --plan` once with the released runtime.
- `rg "hemma-pre-push-check|hemma_pre_push_check|pre_push_touches_migrations"` finds only this task file.

## Stop Conditions

- `check --plan` names a loader other than the declared one: stop and report it.

## Decided Contract Terms

| ID  | Decided contract term                                                                 |
| --- | ------------------------------------------------------------------------------------- |
| D1  | Skriptoteket has no pre-push check outside the shared package (user, 7 Nov 2026).     |
| D2  | The runner loader is declared in governance facts with its reason (user, 7 Nov 2026). |
