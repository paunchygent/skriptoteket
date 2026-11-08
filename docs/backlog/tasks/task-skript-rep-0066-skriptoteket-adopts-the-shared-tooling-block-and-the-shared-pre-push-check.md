---
type: task
id: TASK-SKRIPT-REP-0066
title: Skriptoteket adopts the shared tooling block and the shared pre-push check
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-07'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-08'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: >-
    Pi ruthless-reviewer 84b73b42-64ce-4ee0-aee3-af226b4a17e9 approved commit
    c8dd5e8a8 on 2026-11-08 with no findings (retained session
    01a1bc3d-275a-7fcc-a3b2-d4ffe4a7e9d9,
    discovery/ruthless-reviewer/84b73b42-64ce-4ee0-aee3-af226b4a17e9); its
    focused run over the changed governance and repository test files passed
    74 tests. All three acceptance criteria are met: the full default suite
    under a 16G cap passed 9024 tests with 59 skipped and 0 failed, and
    `pdm run check` reported failed_phases=none with bindings:complete
    exit=0; the shared pre-push hook is installed (`.git/hooks/pre-push`
    runs `pdm run check --pushed`); every differing ruff, pyrefly and pytest
    setting was moved or removed per user decisions D2-D12 with collection
    unchanged at 9083 selected of 9384. Residual: the pre-existing isolated
    timeout in test_vault_rename_races::test_overwrite_saved_during_lineage_rename
    (identical on unmodified main; passes in the full suite).
task_kind: repository
acceptance_criteria:
  - "`pdm run check` passes its bindings:complete phase: the reserved tooling dependency, tooling settings and pre-push hook markers each occur once and match the shared package."
  - "The shared pre-push hook (`check --pushed`) is installed, so a push to main runs the shared test selection."
  - "Each ruff, pyrefly and pytest setting that the shared block does not hold is either moved to a place the block offers or removed, by a user decision per setting."
backlog_document_profile: contract-derived
---

## Implementation Contract

Since TASK-SKRIPT-REP-0065 removed Skriptoteket's own pre-push check, the
repository has no pre-push test check: the shared pre-push block is part of
the bindings that `check` reports as drifted (bindings:complete fails on main
`9c67c78da` with tooling dependency drift, tooling settings drift in
`tool.ruff.exclude`, `tool.ruff.src`, `tool.ruff.lint.select`,
`tool.pyrefly.*` and `tool.pytest.ini_options`, and missing pre-push hook
markers). This task lists every differing setting, the user decides each, and
`repository-governance-bindings sync` then writes the shared block and the
pre-push hook.

## Contract Inputs

- TASK-SKRIPT-REP-0065 merge gate, 7 Nov 2026.
- User decision, 7 Nov 2026: consumer tooling adoption runs as its own task.

## Core Vertical And Performance

No product code changes.

## Validation

- `pdm run check` once after the sync.
- Compare collection before and after the shared defaults, preserving the producer marker filter.
- Run the full default backend suite with `pdm run test tests` and record elapsed time and memory.

## Implementation Evidence

- Baseline: `pdm run pytest --collect-only -q` selected 9083 of 9384 tests
  (301 deselected), in 10.13 seconds. Baseline `pdm run lint` passed and
  reported no applicable files.
- After sync and installation: collection with the producer's marker expression
  selected the same 9083 of 9384 tests (301 deselected), in 9.66 seconds.
  No newly collected non-test function needed renaming.
- Derived tooling facts: `testpaths = ["tests"]`,
  `pythonpath = ["src", ".", "runner"]`; all eight marker strings and all
  twelve Ruff exclude entries are unchanged. `lint-src = [".", "src"]`
  preserves Ruff's documented default first-party roots.
- Mypy declares no `files` or `packages`, so `typecheck-includes = []`.
  `mypy_path = "src:stubs"` gives `typecheck-search-paths = ["src", "stubs"]`.
  The `ignore_missing_imports` overrides give
  `untyped-modules = ["yaml.*", "pypdf.*", "pandas.*", "pypdfium2.*", "lxml.*", "testcontainers.*"]`.
  The scripts override has `follow_imports = "skip"`, not
  `ignore_missing_imports`, and is not included. Mypy remains the producer.
- Initial locking through the old `lock-multi` command succeeded but retained
  only its final platform. Setup then failed because the current host matches
  none of those targets. D13 corrects the route and glibc floor; the regenerated
  lock includes all three targets and the reserved tooling group.
- Setup initially omitted the reserved tooling group and removed pytest; the
  first suite attempt could not import pytest and ran no tests. D14 corrects
  the installed groups. Setup then succeeded, and imports of pytest, xdist,
  pytest_asyncio and pytest_timeout all passed.
- The first runnable full suite failed: 25 failed, 8887 passed, 59 skipped,
  112 errors in 58.99 seconds (61.02 seconds command wall time; sampled peak
  aggregate process RSS 10,234,344 KiB). The module-cached database engine
  inherited the new function loop scope; it and its pooled sessions now keep
  explicit module loop ownership. Two governance assertions still expected
  the retired defaults and were updated. Unrelated FastAPI and PDF failures
  followed broad dependency upgrades from the old lock command. The parent
  authorized restoring the committed lock and adding `--update-reuse` to D13.
- The reuse lock changes only shared pins: coverage 7.13.5 to 7.17.2,
  pytest 9.0.2 to 9.2.0, pytest-asyncio 1.3.0 to 1.4.1.post1,
  pytest-mock 3.15.1 to 3.17.0, Ruff 0.15.9 to 0.17.4,
  testcontainers 4.14.2 to 4.15.0, and newly adds Pyrefly 1.4.1.
  No other package version changes or removals remain.
- Setup after reuse-lock generation failed while building tiktoken (no Rust
  compiler found by its build) and lxml (libxml2/libxslt development packages
  not found by its build). The baseline lock contains compatible CPython 3.14
  x86_64 wheels for these same versions; the newly combined lock omitted
  those artifacts. No host packages were changed. D13's final refresh restores
  compatible CPython 3.14 manylinux x86_64 wheels for lxml, tiktoken, NumPy
  and asyncpg, without any additional version changes. The full lock route
  followed by setup then succeeded without source builds.
- Focused repair proof through `pdm run test` on the two governance files,
  user repository, retired conversion routes, two AI gate files and PDF fill
  bands: 72 passed, 2 warnings in 24.03 seconds. The FastAPI and PDF failures
  disappeared after reinstalling the preserved dependency versions.
- `pdm run precommit-install` in the worktree reported that hooks are shared
  and installed from primary. Running that route from primary installed them;
  `.git/hooks/pre-push` line 39 contains `pdm run check --pushed`.
- D5 applied to the database tests: every test and async fixture in the nine
  test files that use the database fixtures runs on the module loop
  (`pytestmark = pytest.mark.asyncio(loop_scope="module")`;
  `pytest_asyncio.fixture(loop_scope="module")`). The cause: function-loop
  helper fixtures and tests shared `db_session`'s module-loop asyncpg
  connection ("attached to a different loop"; "another operation is in
  progress"; 44 failed and 44 errors).
- The full suite under a 16G memory cap: 9024 passed, 59 skipped, 0 failed,
  0 errors in 104.52 seconds; sampled peak aggregate process memory
  10.84 GB.
- `pdm run check` after the sync: `failed_phases=none`,
  `bindings:complete exit=0`. This satisfies acceptance criterion 1.
- Pre-existing and out of scope:
  `test_vault_rename_races::test_overwrite_saved_during_lineage_rename`
  times out (10 s) when run alone, identically on unmodified main with the
  old tooling, and passes in the full suite.

## Stop Conditions

- A setting changes which tests run by default: bring it to the user before removal.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Consumer tooling adoption runs as its own task (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| D2  | Move the marker filter into the backend-test producer arguments (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                |
| D3  | Replace `-n logical` with shared `-n auto` (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D4  | Keep `--import-mode=importlib` only in the shared block (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                        |
| D5  | Use function fixture loop scope; give fixtures a wider explicit loop only when needed (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                          |
| D6  | Keep `--durations=10` only in the shared block (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| D7  | Move INFO log capture into producer arguments as `--log-level=INFO` until TASK-SKRIPT-REP-0068 (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                 |
| D8  | Drop local warning filters (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D9  | Accept the shared 300-second timeout; report tests exceeding it instead of raising it (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                          |
| D10 | Adopt the Pyrefly table and pin; retain mypy as the checker until TASK-SKRIPT-REP-0067 (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                         |
| D11 | Remove reserved pin duplicates from monorepo-tools (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                                                                                             |
| D12 | Remove python_files, python_classes, python_functions, the Ruff format table and E203 ignore; compare collection counts and rename newly collected non-tests (user, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                   |
| D13 | lock-multi locks each platform target in its own pdm lock call with --append and --update-reuse to retain existing package versions; the x86_64 target is manylinux_2_39 so Hemma (glibc 2.39) matches. Finish with pdm lock --refresh: per-target append locking retains only the first target's artifact hashes; refresh refetches hashes for every target without changing versions (PDM cli/actions.py:64-77, repositories/base.py get_hashes and docs/usage/lockfile.md; parent, 7 Nov 2026). |
| D14 | Setup installs the reserved repository-governance-tooling group through the setup project groups, as skill-repository does (parent, 7 Nov 2026).                                                                                                                                                                                                                                                                                                                                                   |
