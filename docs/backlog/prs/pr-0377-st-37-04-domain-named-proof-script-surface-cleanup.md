---
type: pr
id: PR-0377
title: "ST-37-04 domain-named proof script surface cleanup"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - critical
  - testing
  - playwright
  - operator-surfaces
dependencies:
  - "PR-0376"
acceptance_criteria:
  - "Given retained proof scripts are reusable operator and validation surfaces, when a proof script remains active, then its module name, command name, artifact root, docstrings, comments, and tests use domain language rather than PR, task, ticket, or review identifiers."
  - "Given historical proof evidence still matters, when an old proof surface is renamed, then retained artifacts and historical backlog docs stay understandable without keeping meta-named compatibility shims in active code."
  - "Given this cleanup touches many script and test surfaces, when implementation runs, then it uses the overseer implementation review loop with a separate implementation specialist and fixed ruthless reviewer before the slice can close."
  - "Given proof scripts guard auth and runtime boundaries, when names change, then behavior, HuleEdu browser-session auth, artifact capture, script-surface allowlists, and focused tests remain green."
---

# PR-0377: ST-37-04 Domain-Named Proof Script Surface Cleanup

## Problem

Several retained proof scripts still encode PR/task identifiers in active module
names, artifact roots, comments, docstrings, and test surfaces. That makes
reusable operator proof lanes look disposable, encourages future agents to copy
meta-named patterns, and weakens discoverability by domain.

The transcript parity launcher work keeps its new command domain-named, but the
repository still needs a deliberate cleanup of the broader proof-script surface.

## Goal

Rename active reusable proof script surfaces to domain-owned names and update
their script-surface tests, docs references, artifact-root defaults, and focused
imports without changing product behavior.

## Non-goals

- No product UI, route, backend API, auth-edge, Gateway, Sir Convert, or Docker
  runtime behavior change.
- No deletion of retained historical proof artifacts.
- No compatibility shim that keeps a meta-named active Python module alive.
- No broad historical-doc rewrite beyond references needed to keep current
  operator instructions truthful.

## Required execution model

This slice must be implemented through the overseer implementation review loop:

1. A separate implementation specialist performs the scoped rename and test
   updates.
2. A fixed ruthless reviewer writes retained review evidence and either
   approves or requests changes.
3. Any requested changes return to the same implementation specialist with tests
   that would catch the accepted finding.
4. The slice closes only after the retained review is approved and required
   validation gates pass.

## Implementation plan

1. Inventory active proof scripts under `scripts/` and classify which are
   reusable operator surfaces versus historical one-off artifacts.
2. For reusable active surfaces, replace PR/task/ticket identifiers in module
   names, command names, artifact roots, docstrings, comments, and focused test
   names with domain language.
3. Update `tests/unit/scripts/test_playwright_script_surface.py` so the
   allowlist enforces the new naming policy for active retained proof scripts.
4. Update current operator docs and handoff references that tell agents which
   proof command to run.
5. Retain historical backlog evidence in place unless it is active run
   guidance.

## Test plan

- Red first:
  add or update a script-surface naming test that fails on active meta-named
  proof modules before the cleanup.
- Green:
  run the focused script-surface and renamed proof-helper tests.
- Close-out:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
  `pdm run docs-validate`
  `pdm run handoff-validate` if handoff changes
  `git diff --check`

## Rollback plan

Revert the naming cleanup and restore the previous proof script imports and
artifact-root defaults. Do not delete retained evidence directories during
rollback.

## Implementation summary

- Renamed active reusable proof modules without adding compatibility shims:
  - `scripts/playwright_pr_0349_transcript_parity_live.py` ->
    `scripts/audio_transcription_parity_live.py`
  - `scripts/playwright_pr_0363_conversion_mode_deeplink.py` ->
    `scripts/authenticated_app_identity_split.py`
  - `scripts/playwright_pr_0364_authenticated_home_work_apps.py` ->
    `scripts/authenticated_home_work_apps.py`
  - `scripts/playwright_pr_0365_authenticated_shell_navigation.py` ->
    `scripts/authenticated_shell_navigation.py`
- Updated active module docstrings, parser descriptions, manifest command
  strings, status labels, proof helper imports, launcher-generated module
  invocation, and focused helper test names to domain language.
- Updated future artifact-root defaults to:
  `.artifacts/audio-transcription-parity-live/`,
  `.artifacts/authenticated-app-identity-split/`,
  `.artifacts/authenticated-home-work-apps/`, and
  `.artifacts/authenticated-shell-navigation/`.
- Preserved historical retained `.artifacts/playwright-pr-*` evidence paths and
  historical backlog evidence; only current operator guidance was updated.
- Compacted older ST-37-04 handoff history to
  `.codex/long-term-memory/entries/session-2026-06-23-st-37-04-handoff-compaction.md`
  so `.codex/handoff.md` stays under the live-session budget.
- Review-fix pass renamed active proof summary metadata from
  `pr_0349_transcript_parity_live` to `audio_transcription_parity_live` for
  both successful live proof summaries and trust-lane preflight failure
  summaries.

## Validation

- Red first:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py` failed
  before cleanup with the expected active meta-named proof offenders:
  `playwright_pr_0349_transcript_parity_live.py`,
  `playwright_pr_0363_conversion_mode_deeplink.py`,
  `playwright_pr_0364_authenticated_home_work_apps.py`, and
  `playwright_pr_0365_authenticated_shell_navigation.py`.
- Focused green:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py` passed
  with 4 tests.
- Focused renamed helper/launcher green:
  `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_transcript_parity_proof_launcher.py`
  passed with 36 tests.
- Close-out:
  `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.
- Review-fix red first:
  `pdm run test tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py -k "active_proof_metadata_uses_domain_kind"`
  failed before implementation because `PROOF_KIND` was missing and active
  summary emitters still used `pr_0349_transcript_parity_live`.
- Review-fix green:
  `pdm run test tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_playwright_script_surface.py`
  passed with 36 tests.
