---
type: review
id: REV-PR-0377
title: "Review: PR-0377 domain-named proof script surface cleanup"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "codex-independent-reviewer"
prs:
  - PR-0377
links:
  - EPIC-37
  - ST-37-04
  - PR-0376
---

## TL;DR

PR-0377 is approved on pass 2. Active reusable proof modules, imports, current operator surfaces, and artifact roots are domain-named without active PR-named compatibility shims. The active Audio Transcription proof summaries now emit `proof_kind: audio_transcription_parity_live`, so new retained evidence no longer advertises the retired PR-0349 script identity.

## Problem Statement

The review checks whether reusable proof surfaces have been renamed from PR/task identifiers to durable domain names without keeping active compatibility shims, stale current operator guidance, broken imports, or weak script-surface tests.

## Proposed Solution

The implementation removes the active PR-named proof modules, adds domain-named replacements, updates focused imports/tests and command surfaces, preserves historical `.artifacts/playwright-pr-*` evidence as history, and writes domain-owned metadata for new active Audio Transcription proof summaries.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `AGENTS.md` | Review, testing, docs-as-code, auth-proof rules | 5 min |
| `.codex/handoff.md` | Current operator proof guidance | 5 min |
| `docs/backlog/prs/pr-0377-st-37-04-domain-named-proof-script-surface-cleanup.md` | Scope, acceptance criteria, implementation claims | 15 min |
| `pyproject.toml` | Active command surface | 5 min |
| `scripts/audio_transcription_parity_live.py` | Domain proof metadata, artifact root, HuleEdu auth path | 20 min |
| `scripts/_sir_convert_trust_lane_preflight.py` | Preflight failure proof metadata | 15 min |
| `scripts/authenticated_app_identity_split.py` | Domain module and artifact root | 5 min |
| `scripts/authenticated_home_work_apps.py` | Domain module and artifact root | 5 min |
| `scripts/authenticated_shell_navigation.py` | Domain module and artifact root | 5 min |
| `tests/unit/scripts/test_playwright_script_surface.py` | Active script-surface naming guard | 10 min |
| `tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py` | Active proof metadata guard | 10 min |

**Total estimated time:** ~100 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Remove active meta-named Python proof modules instead of keeping compatibility shims. | Matches the repo's clean-break posture for active surfaces. | [x] |
| Keep historical retained evidence paths intact. | Old `.artifacts/playwright-pr-*` directories are historical proof records, not active runtime aliases. | [x] |
| Use domain-named artifact roots for new proof runs. | Makes future proof output discoverable by product domain. | [x] |
| Remove PR/task identifiers from active retained proof metadata. | New artifacts should describe the active proof domain, not the retired PR-coded implementation. | [x] |

## Review Checklist

- [x] Active renamed modules exist under domain names.
- [x] Removed active PR-named Python modules are not retained as import shims.
- [x] Pyproject exposes the new `transcript-parity-proof` domain command.
- [x] Current handoff guidance names the new launcher and artifact roots.
- [x] Historical artifact references remain understandable.
- [x] HuleEdu browser-session helpers are still used.
- [x] Active retained proof summaries no longer emit PR-coded `proof_kind` metadata.

## Review Feedback

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Pass 1 Finding Resolution

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| `medium`: active Audio Transcription proof summaries still emitted `"proof_kind": "pr_0349_transcript_parity_live"`. | Resolved. `PROOF_KIND = "audio_transcription_parity_live"` now feeds both live proof summaries and preflight failure summaries. | `scripts/_sir_convert_trust_lane_preflight.py:69`, `scripts/_sir_convert_trust_lane_preflight.py:257`, `scripts/audio_transcription_parity_live.py:471` |
| Missing regression proof for active metadata naming. | Resolved. `test_active_proof_metadata_uses_domain_kind` asserts the domain proof kind and rejects `pr_` / `playwright_pr_` prefixes for active preflight failure summaries. | `tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py:70` |

### Findings

None.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Active module rename and no active Python shim.
- [x] Domain artifact-root defaults.
- [x] Updated current operator command guidance.
- [x] Historical proof evidence preservation.
- [x] Domain-owned active proof metadata.

## Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_playwright_script_surface.py` | Passed: 43 tests. |
| `rg -n "pr_0349\|playwright_pr_0349\|proof_kind" scripts/audio_transcription_parity_live.py scripts/_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py -S` | Passed: active `proof_kind` references use `PROOF_KIND`; no active `pr_0349`/`playwright_pr_0349` proof metadata remains in reviewed code. |
| Code review of renamed proof scripts | Passed: active reusable proof modules use domain filenames and artifact roots without active PR-named compatibility shims. |

`pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check` are recorded in final close-out for this pass.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0377` | Created retained pass-2 review record and approved the implementation after the active proof metadata finding was resolved. |
