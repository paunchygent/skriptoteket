---
type: pr
id: PR-0318
title: "ST-21-03 authenticated Exam Converter HuleEdu Sir Convert edge adapter"
status: done
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
stories:
  - "ST-21-03"
tags:
  - frontend
  - auth
  - conversion-hub
  - sir-convert
acceptance_criteria:
  - "Authenticated `documents.conversion_hub` DigiExam migration calls use the HuleEdu Gateway `/sir-convert/v2/convert/...` browser product edge, not direct `convert.hule.education`, direct Sir Convert service hosts, service API keys, or self-signed identity contexts."
  - "The adapter submits the governed `digiexam_dxe -> examnet_migration_bundle` multipart request with deterministic `Idempotency-Key` and one preserved `X-Correlation-ID` across submit, poll, result, artifact-list, named download, and user-file save handoff."
  - "The adapter exposes submit, job status, terminal result, artifact manifest listing, and named artifact download without parsing `.dxe`, inferring answer keys, rewriting Sir Convert warnings, inspecting workdirs, or hiding blocked/manual-follow-up states."
  - "Consumer tests prove the Gateway route prefix, multipart part names, deterministic headers, result/artifact endpoints, blocked/not-requested availability handling, and absence of Sir Convert API keys in browser requests."
---

# PR-0318: ST-21-03 Authenticated Exam Converter HuleEdu Sir Convert Edge Adapter

## Problem

Sir Convert Task 282 and the HuleEdu Gateway auth-edge slices expose the
authenticated DigiExam migration artifact-bundle route through the governed
browser/product edge. Skriptoteket still needs an owning consumer slice before
the `documents.conversion_hub` workflow can stop relying on the older direct
backend v2 conversion client shape.

## Goal

Add the first Skriptoteket-owned authenticated adapter layer for DigiExam
migration. The adapter must call the HuleEdu Gateway `/sir-convert/v2/convert`
route family from the browser session boundary, construct only the governed
multipart contract, preserve deterministic request headers, and expose typed
bundle/result/artifact metadata for the later UI and user-file persistence
slice.

## Non-goals

- Public anonymous Exam Converter entry or profile/ADR public-access changes.
- HuleEdu Gateway or Sir Convert runtime changes.
- Parsing `.dxe`, reading graded-result PDFs, deriving answer keys, or
  normalizing Sir Convert workdirs inside Skriptoteket.
- Exam.net upload automation or editable DOCX generation.
- Replacing the existing backend Sir Convert client used by internal
  non-browser conversion flows.

## Implementation Plan

1. Add a small frontend Sir Convert Gateway adapter package for authenticated
   DigiExam migration, split by contracts, JobSpec construction, request
   context, transport, response parsing, and save-metadata mapping.
2. Generate deterministic idempotency and correlation headers at the teacher
   action boundary and carry them across submit/read/download calls.
3. Build the exact governed `job_spec` and multipart part names:
   `file`, optional `graded_result_pdf`, optional `parity_pdf`, and `job_spec`.
4. Add typed helpers for status, result, artifact manifest, and named artifact
   download through `/sir-convert/v2/convert/jobs/...`.
5. Add focused Vitest coverage for route prefixing, multipart shape, header
   preservation, no browser API-key header, and bundle availability states.
6. Fail closed when `VITE_HULEEDU_SIR_CONVERT_BASE_URL` does not resolve to the
   HuleEdu Gateway `/sir-convert/v2/convert` route family, the local Gateway
   equivalent on port `8080`, or the explicit test host used by Vitest.
7. Keep Vite's `/sir-convert` dev proxy on a dedicated
   `VITE_DEV_SIR_CONVERT_GATEWAY_PROXY_TARGET` lane so local proof exercises the
   HuleEdu Gateway equivalent rather than the Skriptoteket app backend.

## Test Plan

- `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/client.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `git diff --check`
- Static production bundle grep for direct Sir Convert service credentials or
  reserved browser product host strings.

## Verification

- `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/client.spec.ts`:
  passed, 20 tests.
- `pdm run fe-type-check`: passed.
- `pdm run fe-lint`: passed.
- `pdm run fe-build`: passed.
- `node --input-type=module -e "import { loadConfigFromFile } from 'vite'; const loaded = await loadConfigFromFile({ command: 'serve', mode: 'development' }, './vite.config.ts'); console.log(loaded.config.server.proxy['/sir-convert'].target);"`
  from `frontend/apps/skriptoteket`: printed `http://localhost:8080`.
- `pdm run docs-validate`: passed.
- `git diff --check`: passed.
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010" src/skriptoteket/web/static/spa`:
  no matches in the production SPA bundle.

## Review Status

Retained review `REV-PR-0318` is `approved` in
`docs/backlog/reviews/review-pr-0318-authenticated-exam-converter-huleedu-sir-convert-edge.md`.
The retained blockers have remediation in the current implementation:
Gateway base-URL validation is fail-closed, local `/sir-convert` proxying uses
the dedicated HuleEdu Gateway proxy target, and blocked/failed/not-implemented
artifact entries now require `blocker_code`.

## Rollback Plan

Remove the frontend adapter module and its tests. No database migration or
backend runtime state is introduced in this slice.
