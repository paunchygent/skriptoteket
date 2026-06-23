---
type: review
id: REV-PR-0375
title: "Review: PR-0375 Document Converter backend-backed MVP planning"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "skriptoteket_reviewer"
prs:
  - PR-0375
links:
  - ST-37-04
  - EPIC-37
  - REF-current-product-lanes-and-sir-convert-boundary-v1
  - REF-app-presentation-decomposition-and-naming-plan-v1
---

# Review: PR-0375 Document Converter Backend-Backed MVP Planning

## TL;DR

Approved. The planning package now defines a truthful backend-backed Document
Converter MVP boundary before any route, host, registry capability, runtime
link, or proof target is activated.

## Problem Statement

Document Converter is visible as a future lane, but it must not become another
facade over Exam Converter, Audio Transcription, or the generic compatibility
host. This review checks whether `PR-0375` closes the backend/Sir Convert/
artifact/save/replay planning contract before implementation.

## Proposed Solution

Keep Document Converter inert while approving a planning-only MVP contract:
authenticated-only, scoped under `documents.conversion_hub/document-converter`,
single-result artifact, server-authoritative download/save, retry/replay as new
submission by default, and separate backend/API versus route-visible proof.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md` | MVP contract, artifact/download/save/replay semantics, stop conditions | 25 min |
| `.codex/handoff.md` | Current-state truth, Hemma pause, next-step guidance | 10 min |
| `docs/backlog/prs/pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md` | Blocked-state consistency | 5 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Parent story status | 5 min |

**Total estimated time:** ~45 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Freeze MVP as single-result artifact per job. | Avoids fake artifact discovery and removes browser artifact-key authority. | [x] |
| Keep first backend slice under `documents.conversion_hub/document-converter`. | Avoids bootstrap/catalog/app-detail changes before a concrete need exists. | [x] |
| Keep `PR-0369` blocked. | No backend/API app-presentation split is proven by `PR-0375`. | [x] |
| Split backend/API proof from route-visible proof. | Prevents the backend slice from activating a Document Converter route prematurely. | [x] |

## Review Checklist

- [x] Governing docs authority exists and matches the planning slice.
- [x] No Document Converter route, host, registry capability, runtime link, or
  proof target is activated.
- [x] Artifact, download, save, and retry/replay semantics are reviewable.
- [x] Exam Converter and Audio Transcription scopes remain separate.
- [x] HuleEdu Gateway, CSRF, signed identity, server-side Sir Convert
  credentials, and route-grant boundaries are preserved.
- [x] `PR-0369` remains blocked unless later work proves a concrete contract
  need.
- [x] Handoff does not claim Hemma deploy success and does not instruct agents
  to run paused Hemma/server commands.

## Review Feedback

**Reviewer:** `skriptoteket_reviewer`
**Date:** `2026-06-23`
**Verdict:** approved

### Required Changes

Resolved before approval:

- Artifact contract was under-specified; fixed by freezing MVP as a
  single-result artifact contract.
- Backend namespace was ambiguous; fixed by choosing
  `documents.conversion_hub/document-converter` for the first backend slice.
- Proof plan mixed backend/API and route-visible obligations; fixed by splitting
  the proof plan by slice.
- Handoff listed `pdm run transcript-parity-proof remote-proof` as active while
  Hemma/server activity was paused; fixed by removing it from the active run
  list.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Single-result artifact contract.
- [x] Scoped compatibility backend namespace.
- [x] `PR-0369` remains blocked.
- [x] Backend/API proof and route-visible proof remain separate.

## Changes Made

- `PR-0375` now freezes the MVP as a single-result artifact contract.
- MVP download and save are addressed by local `job_id`; browser code does not
  choose or submit an `artifact_key`.
- The first backend slice is pinned to
  `/api/v1/apps/documents.conversion_hub/document-converter/...`, keeping
  `PR-0369` blocked unless later route-visible work proves a concrete
  bootstrap/catalog/app-detail need.
- Backend/API proof is separated from the later route-visible proof.
- `.codex/handoff.md` no longer lists the remote transcript proof as an active
  command and records Hemma/server activity as paused.

## Verification Reviewed

- Main-agent reported: `pdm run docs-validate`
- Main-agent reported: `pdm run handoff-validate`
- Main-agent reported: `git diff --check`

Residual risk: the reviewer did not rerun the gates independently; approval
relies on reported green local validation plus direct scoped review.
