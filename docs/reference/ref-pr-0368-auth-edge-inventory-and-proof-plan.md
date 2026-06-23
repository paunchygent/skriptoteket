---
type: reference
id: REF-pr-0368-auth-edge-inventory-and-proof-plan
title: "PR-0368 auth edge inventory and proof plan"
status: active
owners: "agents"
created: 2026-06-22
topic: "auth-edge-proof"
---

# PR-0368 Auth Edge Inventory And Proof Plan

This reference is the first retained implementation artifact for `PR-0368`.
It inventories the protected Exam Converter and Audio Transcription edge before
route-visible presentation changes split the teacher-facing app identities.

## Scope

`PR-0368` is a frontend route and presentation split only. Exam Converter and
Audio Transcription may receive canonical protected entrypoints, but they must
continue to use the existing authenticated runtime shell, HuleEdu Gateway edge,
Skriptoteket app-local access checks, Sir Convert producer boundary, replay,
polling, formatter, and artifact code.

The public Exam Converter route remains
`/public/apps/documents.conversion_hub/exam-converter`. Document Converter
remains inert and unlinked.

## Auth Edge Inventory

| Edge | Current authority | PR-0368 requirement |
|------|-------------------|---------------------|
| Browser session and CSRF | HuleEdu owns browser login/session issuance, product callback, and unsafe-action CSRF token handling. Skriptoteket proof enters through `/auth/login` and `scripts/_playwright_auth.py`. | Keep canonical protected proof on the HuleEdu browser-session ceremony. Do not use browser-authored identity headers, direct cookies, product-backend credential POST shortcuts, or host-only backend proof. |
| Gateway `/sir-convert` proxy | `frontend/apps/skriptoteket/src/api/sirConvertGateway/urls.ts` resolves protected conversion traffic to `/sir-convert/v2/convert` in local dev and `https://api.hule.education/sir-convert/v2/convert` in production. Vite shared-auth proof proxies `/sir-convert` through HuleEdu Gateway. | Keep both canonical app identities on this shared Gateway URL resolver and shared transport client. Do not add browser-direct Sir Convert calls or per-app Gateway clients. |
| Server-side Sir Convert key injection | HuleEdu Gateway injects protected Sir Convert authority server-side before proxying producer requests. Browser code only sends session credentials, CSRF-backed unsafe headers, correlation IDs, idempotency keys, files, and job specs through the Gateway. | Preserve server-side key injection. Do not expose `X-API-Key`, bearer credentials, or Sir Convert credentials in browser code. |
| Signed identity context | `src/skriptoteket/domain/identity/internal_identity_context.py` defines signed `InternalIdentityContextV1` headers and grants; `src/skriptoteket/infrastructure/security/huleedu_internal_identity.py` verifies detached RS256 signatures, timestamps, issuer, audience, and key id. | Presentation routes must not manufacture identity. Protected app/API access continues through the existing app projection dependency and signed context verifier. |
| Route grants and prefix stripping | HuleEdu Gateway strips and validates product/Gateway prefixes before protected app and `/sir-convert` traffic reaches Skriptoteket or Sir Convert, then forwards signed identity and route grants. | Canonical frontend routes must rely on the same protected app continuation and Gateway prefix behavior. No app-specific auth edge is introduced. |
| App-local access | `src/skriptoteket/web/api/v1/apps_conversion_hub_access.py` gates the existing `documents.conversion_hub` backend app id through the curated-app registry role. | Keep backend app id and access helper unchanged. The new teacher-facing identities are presentation aliases over the current shared backend app id. |

## Runtime Client Inventory

| Flow | Current frontend boundary | Preserved behavior |
|------|---------------------------|--------------------|
| Exam conversion submit/poll/result | `useExamConverterAuthenticatedRuntime` delegates to `api/sirConvertGateway/client.ts` methods `submitDigiExamMigration`, `getDigiExamMigrationJob`, and `getDigiExamMigrationResult`. | Canonical Exam Converter route reuses the same runtime composable and client. |
| Exam correction replay | Exam correction UI uses `issueExamAuthoringCorrectionSourceState` and `applyExamAuthoringCorrections` through the same Sir Convert Gateway client. | No correction-session, replay, source-state, or answer-key contract changes. |
| Exam artifact download/save | Exam file actions use `downloadDigiExamMigrationArtifact` plus the existing Skriptoteket artifact save route for user files. | Artifact references, correlation IDs, job IDs, and owner scope are unchanged. |
| Transcript submission/polling/artifact readback | `ConversionHubTranscriptHost.vue` uses `useTranscriptGatewayRuntime.ts`, which delegates to `submitTranscriptJob`, `getTranscriptJob`, `getTranscriptResult`, `listTranscriptArtifacts`, `downloadTranscriptJson`, and `cancelTranscriptJob`. | Canonical Audio Transcription route reuses this transcript host and runtime. |
| Transcript persistence and speaker overlays | `api/conversionHubTranscriptSaves.ts` persists canonical transcript JSON and speaker overlays under `/api/v1/apps/documents.conversion_hub/transcripts`. | Saved transcript owner scope, local job registration, and overlay update routes are unchanged. |
| Transcript formatter replay/export | `api/conversionHubTranscriptFormatterExports.ts` requests and polls formatter export state; `api/conversionHubTranscriptFormatterArtifactActions.ts` downloads/saves formatter artifacts through Skriptoteket-owned authorization routes. | Formatter replay and artifact actions stay backend-mediated and product-owned. |
| Shared API/session handling | `api/client.ts`, `stores/auth`, route guards, and app projection dependencies own protected `/api` behavior. | No duplicate app-specific auth handling is added for either identity. |

## Existing Proof Surfaces

- `scripts/_playwright_auth.py` is the required login helper for retained
  protected browser proof.
- `scripts/_sir_convert_trust_lane_preflight.py` is the retained trust-lane
  preflight helper for Sir Convert remote proof coherence and must be referenced
  by live conversion/transcript proof when source upload or producer jobs are
  exercised.
- `pdm run dev-stack web-start` keeps Docker `skriptoteket_web` available to
  HuleEdu Gateway as `skriptoteket-web`.
- `pdm run fe-dev-shared-auth` keeps protected `/api` and `/sir-convert`
  traffic on HuleEdu Gateway while Vite serves the SPA.

## PR-0368 Proof Plan

Red-first focused Vitest command:

```bash
pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts
```

Expected red failures before production edits:

- Canonical protected Exam Converter and Audio Transcription routes do not
  exist yet.
- Home work-app entries still point at
  `/apps/documents.conversion_hub?mode=exam|transcript`.
- The authenticated host still presents `ConversionHubModeTabs` in normal app
  flow.

Green focused Vitest proof will use the same command and any additional
changed-surface specs needed for home or host behavior.

Live protected proof updates the existing retained PR-0363 script into the
PR-0368 route-visible proof lane rather than adding duplicate auth machinery:

```bash
pdm run python -m scripts.authenticated_app_identity_split
```

The script keeps using `login_via_auth_entry`, writes new retained artifacts
under `.artifacts/authenticated-app-identity-split/`, and covers both
canonical protected route identities:

- Exam Converter canonical entrypoint renders the exam workflow shell without
  `ConversionHubModeTabs` and without a `mode` query.
- Audio Transcription canonical entrypoint renders transcript workflow and
  workspace shells without `ConversionHubModeTabs` and without a `mode` query.
- `PR-0374` removes legacy `documents.conversion_hub?mode=...` presentation
  compatibility after this proof and keeps home/work-app links on canonical
  protected routes.

If the local shared-auth Docker/Gateway lane is unavailable, the proof must
stop at preflight or environment checks and record the exact blocker. A
shortcut proof through direct cookies, credential POSTs, host-only backend, or
browser-authored identity headers is invalid.
