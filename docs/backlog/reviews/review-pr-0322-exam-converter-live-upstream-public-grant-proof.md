---
type: review
id: REV-PR-0322
title: "Review: PR-0322 Exam Converter live upstream public grant proof"
status: approved
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0322
links:
  - EPIC-21
  - ST-21-03
  - PR-0320
  - REV-PR-0320
  - PR-0321
  - REV-PR-0321
  - PR-0323
---

# Review: PR-0322 Exam Converter Live Upstream Public Grant Proof

## TL;DR

`PR-0322` is approved after the cross-repo runtime blockers were remediated by
Sir Convert `TASK-292` and Skriptoteket `PR-0323`.

The rerun used local live services, generated local-only signing material under
ignored `.artifacts/`, and real HTTP calls across the three runtime boundaries:

- Skriptoteket public API on `http://127.0.0.1:8000`.
- HuleEdu Gateway public grant authority on `http://127.0.0.1:8080`.
- Sir Convert v2 public verifier/read-lease runtime on `http://127.0.0.1:8085`.

No HuleEdu signing private key, Sir Convert API key, raw
`PublicConversionGrantV1`, raw `PublicArtifactReadLeaseV1`, or token payload was
retained in governed docs.

## Problem Statement

`PR-0322` needed to prove that the public Exam Converter path works against the
real cross-repo authority split instead of local contract assumptions. The
first proof attempt correctly failed closed because Skriptoteket still expected
HuleEdu to return read leases and Sir Convert did not yet have retained runtime
verifier/read-lease evidence.

## Proposed Solution

Approve `PR-0322` only after the proof consumes HuleEdu as grant-only authority,
Sir Convert as public grant verifier/read-lease issuer, and Skriptoteket as the
server-side consumer that withholds all upstream authority from browser-visible
responses.

## Artifacts to Review

| Artifact | Focus | Time |
|----------|-------|------|
| `docs/backlog/prs/pr-0322-st-21-03-exam-converter-live-upstream-public-grant-proof.md` | Proof scope and stop conditions | 5 min |
| `docs/backlog/prs/pr-0323-st-21-03-exam-converter-grant-only-consumer-alignment.md` | Skriptoteket grant-only consumer remediation | 5 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-292-implement-public-exam-converter-grant-verifier-and-read-leases.md` | Sir Convert runtime verifier/read-lease remediation | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/public_exam_converter_grants.py` | HuleEdu grant-only client | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/public_exam_converter_sir_convert_client_v2.py` | Public Sir Convert grant/read-lease client | 5 min |
| `src/skriptoteket/application/curated_apps/handlers/public_exam_converter_jobs.py` | Server-side authority retention and public projection | 5 min |

**Total estimated time:** ~30 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Treat HuleEdu as grant-only authority | Matches `TASK-0565` and prevents authority mixing | [x] |
| Treat Sir Convert as read-lease issuer | Leases are only valid after Sir Convert verifies the grant and owns the job/artifact boundary | [x] |
| Retain only sanitized local evidence | Prevents secrets, raw grants, and raw read leases from entering governed docs | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract

## Review Feedback

**Reviewer:** codex
**Date:** 2026-05-13
**Verdict:** approved

**Approved.** No blocking findings remain for `PR-0322`.

The original blockers were resolved:

- HuleEdu is treated as grant-only authority.
- Sir Convert verifies `PublicConversionGrantV1`, creates public-grant-owned
  jobs/artifacts, and issues read leases after the grant boundary.
- Skriptoteket keeps parent grants and read leases server-side and projects
  only local public handles/URLs to browsers.

## Proof Executed

Positive live proof:

- `POST /api/v1/public/apps/documents.conversion_hub/exam-converter/jobs`
  returned `200` and a local public job id
  `e1fabec5-9a0f-4f4c-8cfa-f3c82643076c`.
- `GET /jobs/{public_job_id}` returned `200` with `status=succeeded`.
- `GET /jobs/{public_job_id}/result` returned `200` with the local artifact
  manifest URL.
- `GET /jobs/{public_job_id}/artifacts` returned `200`, nine artifact entries,
  no raw public grant, and no raw artifact-read lease fields.
- `GET /jobs/{public_job_id}/artifacts/ir_json/download` returned `200`,
  `content-type=application/json`, filename `digiexam-ir.json`, and 22025
  bytes.

Cookie parity on the successful public job:

- Status with synthetic ambient cookie returned `200` and the same public job
  id/status.
- Manifest with synthetic ambient cookie returned `200`, nine artifact entries,
  and no raw grant/read-lease fields.
- Named download with synthetic ambient cookie returned `200` and 22025 bytes.

Negative proof:

- Unsupported target returned `422` with
  `public_exam_converter_invalid_target`.
- Missing `source_dxe` returned `422`.
- Unsupported public root returned `404`.
- Missing public job artifact manifest returned `404`.
- Anonymous status rate limit returned `200`, `200`, `200`, then `429`.
- Expired HuleEdu grant proof used a one-second local grant, waited beyond the
  Sir Convert skew window, and Sir Convert rejected public submit with `401`
  and `public_grant_expired`.

No-account-persistence proof:

- `conversion_hub_jobs` remained `0`.
- `tool_runs` remained `0`.
- Existing `user_vault_files` and `user_vault_usage` counts were unchanged by
  the public proof path.

Forbidden browser-authority proof:

- Production SPA build completed.
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010|PublicConversionGrantV1|PublicArtifactReadLeaseV1" src/skriptoteket/web/static/spa`
  returned no matches.

## Sanitized Local Evidence

Evidence retained under ignored `.artifacts/pr-0322-live-proof/`:

- `submit-response.json`
- `status-response.json`
- `result-response.json`
- `manifest-response.json`
- `ir-json-download.headers`
- `ir-json-download.body`
- `status-cookie-response.json`
- `manifest-cookie-response.json`
- `download-cookie.headers`
- `download-cookie.body`
- `negative-invalid-target.json`
- `negative-missing-dxe.json`
- `negative-public-root.json`
- `negative-missing-job.json`
- `rate-status-1.json` through `rate-status-4.json`
- `ttl-expired-grant-proof.json`

These files are local proof artifacts only and are not committed.

## Verification

- `pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py -q`
  (`6 passed`)
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts src/views/PublicAppHostView.spec.ts src/views/AppHostView.spec.ts`
  (`7 passed`)
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- Production-bundle forbidden-string grep listed above.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0322` | Marked live proof done after successful positive, negative, cookie-parity, TTL, no-account, and forbidden-browser-authority proof. |
| 2 | `REV-PR-0322` | Retained approved review with sanitized proof evidence and verification. |
| 3 | `ST-21-03` / `EPIC-21` / `.codex/handoff.md` | Synced the public lane from blocked to approved and pointed next work to authenticated proof. |
