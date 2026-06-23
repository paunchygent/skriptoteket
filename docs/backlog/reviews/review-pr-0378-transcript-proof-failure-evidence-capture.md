---
type: review
id: REV-PR-0378
title: "Review: PR-0378 transcript proof failure evidence capture"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "codex-independent-reviewer"
prs:
  - PR-0378
links:
  - EPIC-37
  - ST-37-04
  - PR-0376
  - PR-0377
---

## TL;DR

PR-0378 is approved on pass 2. The retained evidence lane now parses structured JSON log lines, recursively redacts sensitive keyed values, applies the plain-text fallback redactor after serialization, and keeps the proof/root-cause objective without adding product UI retry behavior.

## Problem Statement

The retained transcript proof now reaches the real Gateway-backed polling path and can fail after HuleEdu Gateway plus Skriptoteket `web`/`worker` are recreated into the proof lane. Before implementing any product retry behavior, the launcher needs bounded, redacted, pre-cleanup runtime evidence from the actual containers so operators can classify the failure source.

## Proposed Solution

PR-0378 adds runtime evidence capture to `pdm run transcript-parity-proof remote-proof`: on proof failure after mutable runtime setup, the launcher captures container state and bounded logs for HuleEdu Gateway, Skriptoteket web, and Skriptoteket worker, writes artifacts under the launch run directory, links them from `failure-summary.json`, and then continues cleanup while preserving the primary proof failure.

## Artifacts to Review

| File | Focus |
|------|-------|
| `docs/backlog/prs/pr-0378-st-37-04-transcript-proof-failure-evidence-capture.md` | Governing objective, non-goals, validation claims |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Story linkage and PR-0377/PR-0378 boundaries |
| `scripts/transcript_parity_proof_launcher.py` | Capture gating, failure summary shape, cleanup ordering, primary-error preservation |
| `scripts/_transcript_parity_runtime_evidence.py` | Container targets, bounded log/inspect capture, artifact paths, classification |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Behavior proof for pre-cleanup capture and redaction |
| `.codex/handoff.md` | Current operator guidance |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep PR-0378 as proof failure evidence capture, not product retry behavior. | The observed `502` has not been classified as a safe transient UI condition. | [x] |
| Capture only after proof-lane mutation and before cleanup restores containers. | Evidence must represent the failing proof runtime, not restored state. | [x] |
| Capture Gateway, web, and worker runtime evidence. | The failure can originate at any of the three involved containers. | [x] |
| Retain bounded, redacted artifacts and structured summary links. | Operators need useful root-cause evidence without env dumps, secrets, or payloads. | [x] |

## Review Checklist

- [x] Governing PR-0378 doc exists and points to ST-37-04.
- [x] Corrected objective is evidence capture/root-cause observability, not product retry behavior.
- [x] Capture is gated to proof failure after mutable runtime setup.
- [x] Capture happens before cleanup restore/recreate commands.
- [x] Gateway, Skriptoteket web, and Skriptoteket worker are targeted.
- [x] Runtime evidence artifacts are bounded and linked from `failure-summary.json`.
- [x] Runtime evidence redaction is strong enough for JSON-shaped production logs.
- [x] Cleanup runs afterward and primary proof failure is preserved.
- [x] PR-0377 proof-script surface remains closed/intact.

## Review Feedback

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Decision

`approved`

PR-0378 keeps the corrected root-cause evidence objective, avoids product UI retry behavior, and now satisfies the retained-evidence redaction contract for line-oriented JSON production logs. No unresolved findings remain.

### Findings

None.

### Pass 1 Finding Resolution

| Prior finding | Resolution evidence | Status |
|---------------|---------------------|--------|
| High: runtime evidence redaction did not cover structured JSON log secrets. | `scripts/_transcript_parity_runtime_evidence.py:153` parses/redacts each log line before artifact writes; `scripts/_transcript_parity_runtime_evidence.py:166` through `scripts/_transcript_parity_runtime_evidence.py:176` parses JSON lines, recursively redacts them, serializes them, and then applies the launcher plain-text fallback redactor; `scripts/_transcript_parity_runtime_evidence.py:179` through `scripts/_transcript_parity_runtime_evidence.py:212` redacts nested mappings/lists for authorization, cookies, sessions, CSRF/XSRF, bearer/token, secrets, passwords, API keys, and private-key variants. | Resolved. |
| Missing behavior proof for JSON-shaped secrets. | `tests/unit/scripts/test_transcript_parity_proof_launcher.py:583` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:677` now exercises Gateway/web/worker JSON logs with fake authorization, cookie, set-cookie, API-key, password, token, CSRF, private-key, web-token, and worker-key values; it asserts raw values are absent from serialized `failure-summary.json` and every retained `*.logs.txt` artifact while preserving non-secret context and classification. | Resolved. |

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| Does PR-0378 preserve the proof/root-cause objective and avoid product UI retry behavior? | Approved | The PR non-goals explicitly defer UI polling retry behavior, current diffs do not modify `useTranscriptGatewayRuntime.ts`, and implementation is confined to launcher evidence capture plus docs/tests. |
| Does runtime evidence capture happen only after mutable proof lane setup and before cleanup? | Approved | `_should_capture_runtime_evidence(...)` returns true only for `transcript_parity_proof_failed` after both mutation flags are true; `main(...)` captures evidence in the `except` path before the `finally` cleanup restore commands. |
| Are the correct containers captured? | Approved | `RUNTIME_EVIDENCE_TARGETS` includes `huleedu_api_gateway_service`, `skriptoteket_web`, and `skriptoteket_worker`; the focused test asserts `docker inspect` and `docker logs --tail 160` for all three. |
| Are logs bounded, redacted, and env dumps avoided? | Approved | `docker logs --tail 160` plus the 4,000-character artifact cap bound retained logs; `docker inspect` uses only a state/health format; JSON and fallback redaction run before artifact writes. |
| Does `failure-summary.json` include useful structured evidence? | Approved | The summary includes `runtime_evidence` with status, classification, artifact root, per-container artifact paths, return codes, and truncation flags. |
| Does cleanup still run afterward and preserve the primary failure? | Approved | Existing cleanup paths still run from `finally`, and proof-failure tests preserve `transcript_parity_proof_failed` while filtering runtime-evidence commands out of restore-command assertions. |
| Are tests behavior-focused and red/green evidence sufficient? | Approved | The runtime-evidence tests assert retained artifacts, summary contents, ordering before cleanup, classification, and raw-secret absence from outputs; reported red-first evidence covers both capture absence and JSON redaction absence. |
| Are docs/handoff truthful, and does PR-0377 remain intact? | Approved | PR doc and handoff truthfully describe proof evidence capture, JSON redaction, and deferred UI retry behavior. `git diff --` shows no product UI runtime diff and no PR-0377 doc diff; adjacent PR-0377 proof-surface tests still pass. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"` | Passed: 2 selected tests. |
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 24 tests. |
| `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py` | Passed: 36 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| `git diff -- frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts` | No diff. |
| `git diff -- docs/backlog/prs/pr-0377-st-37-04-domain-named-proof-script-surface-cleanup.md docs/backlog/reviews/review-pr-0377-domain-named-proof-script-surface-cleanup.md` | No tracked diff. |
| Code review of `scripts/transcript_parity_proof_launcher.py` and `scripts/_transcript_parity_runtime_evidence.py` | Approved: evidence capture timing, target containers, bounded commands, cleanup ordering, primary-error preservation, and structured JSON/fallback redaction satisfy PR-0378. |

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0378` | Pass 1 retained review recorded one high structured-JSON redaction finding and `changes_requested`. |
| 2 | `REV-PR-0378` | Pass 2 retained review marks that finding resolved, records focused validation, and changes the decision to `approved`. |
