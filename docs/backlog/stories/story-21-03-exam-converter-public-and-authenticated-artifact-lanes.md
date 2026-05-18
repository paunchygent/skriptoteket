---
type: story
id: ST-21-03
title: "Exam converter public and authenticated artifact lanes"
status: in_progress
owners: "agents"
created: 2026-05-13
updated: 2026-05-18
epic: "EPIC-21"
dependencies:
  - "ADR-0066"
  - "ADR-0079"
  - "ADR-0085"
  - "ST-21-01"
  - "ST-32-03"
acceptance_criteria:
  - "Given the current public curated-app matrix keeps Conversion Hub authenticated-only, when this story moves to implementation, then the first slice updates the accepted public-access/profile authority so `documents.conversion_hub` explicitly allows the bounded Exam Converter public lane instead of relying on an undocumented exception."
  - "Given a teacher only needs a one-time conversion, when they use the public Exam Converter entry, then Skriptoteket offers a browser-backed workflow that accepts `.dxe`, optional sanitized graded result PDF, target selection, job progress, and direct artifact downloads without requiring login."
  - "Given the public Exam Converter lane handles uploads and conversion compute, when public endpoints are specified, then they live under a dedicated public namespace, ignore ambient account authority, enforce MIME/type validation, upload-size caps, request-time budgets, concurrency limits, rate limits, structured reason codes, and short artifact TTLs before calling the conversion backend."
  - "Given the public lane is unauthenticated, when artifacts are produced, then Skriptoteket provides direct download only and never creates Vault/MyFiles records, owner-scoped job rows, recoverable guest jobs, or account history before login."
  - "Given a signed-in teacher uses the authenticated Exam Converter lane, when they upload `.dxe`, optional sanitized graded result PDF, choose targets, submit, poll, list artifacts, download, or save to user files, then Skriptoteket routes through the HuleEdu Gateway `/sir-convert/v2/convert/...` product edge and preserves the Sir Convert named artifact manifest."
  - "Given Sir Convert supports advisory local-LLM completion for missing machine-marked answer keys, when a signed-in teacher uses the authenticated Exam Converter lane, then Skriptoteket treats suggestions as AI-suggested facit that require explicit teacher review and reviewed-overlay resubmission before export readiness can change."
  - "Given authenticated conversion work is user-originated, when Skriptoteket calls Sir Convert, then it does not self-sign identity, forward a `skriptoteket` audience context, embed Sir Convert service credentials in browser code, or call direct `convert.hule.education` product traffic; it relies on the HuleEdu auth edge to mint `aud=sir-convert-a-lot` with route-appropriate grants."
  - "Given public and authenticated lanes share the same teacher-facing converter, when limits and failures are surfaced, then both lanes use the same validation taxonomy, target vocabulary, manual-follow-up states, artifact manifest labels, and correlation-id display while allowing authenticated quotas and save-to-files affordances to be stricter or richer than the public baseline."
  - "Given Sir Convert supports target-selective artifact generation, when the teacher selects targets, then Skriptoteket sends `conversion.targets` and shows `not_requested`, blocked, partial, and manual-follow-up outcomes without inventing missing artifacts or hiding Sir Convert warnings."
  - "Given HuleEdu Gateway owns the protected Sir Convert edge, when this story is implemented, then Skriptoteket references the HuleEdu `ST-01-07` / `TASK-0561` contract and proves submit, poll, result, artifact manifest, named download, and save-to-user-files through the Gateway path."
  - "Given `convert.hule.education` is reserved/fail-closed for browser product traffic, when either lane is reviewed, then browser code never treats that host as the direct product entry; public and authenticated traffic enter through Skriptoteket/Gateway-owned routes."
ui_impact: "Yes (new Exam Converter public entry plus authenticated Conversion Hub workflow with target selection, progress, artifacts, and save-to-files affordances)."
data_impact: "Yes (public lane transient job/artifact state only; authenticated lane owner-scoped conversion job mapping and optional Vault/MyFiles artifact persistence)."
---

## Context

Teachers need two related but distinct product paths for exam conversion:

- a public, no-login path for colleagues who only need a one-time conversion of
  an Exam.net/DigiExam-style test without being forced into the authenticated
  app; and
- an authenticated path for teachers who want owner-scoped job continuity,
  downloads, and saving generated artifacts to their user files.

This story belongs under `EPIC-21` because Conversion Hub is the existing
Skriptoteket product owner for Sir Convert-backed conversions. `EPIC-32` and
`ST-32-03` provide the public curated-app namespace and abuse-control precedent,
but they do not reopen themselves for this app. The first implementation slice
must therefore update the accepted public-access/profile authority before
opening anonymous conversion uploads.

## Existing Authority

- Skriptoteket Conversion Hub authority:
  - `docs/backlog/epics/epic-21-curated-app-conversion-hub.md`
  - `docs/backlog/stories/story-21-01-curated-app-conversion-hub-v1.md`
  - `docs/adr/adr-0066-sir-convert-a-lot-v2-as-canonical-conversion-engine.md`
- Skriptoteket public curated-app boundary:
  - `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md`
  - `docs/adr/adr-0085-exam-converter-public-conversion-exception-for-conversion-hub.md`
  - `docs/backlog/stories/story-32-03-public-curated-app-api-namespace-and-anonymous-abuse-controls.md`
- HuleEdu auth-edge contract:
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0561-cut-skriptoteket-artifact-bundle-adapter-to-huleedu-sir-convert-edge.md`
- Sir Convert runtime and artifact contract:
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
- Public grant authority for the public Exam Converter lane:
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0563-define-public-exam-converter-grant-authority-for-sir-convert.md`
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/reference/ref-public-exam-converter-grant-v1-contract.md`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md`

## Lane Shape

### Public Lane

- Product entry is a Skriptoteket public curated-app route for one-time teacher
  conversion.
- Browser state may track the current upload, status, and downloadable artifact
  handles, but account persistence is unavailable.
- Backend calls remain mediated by Skriptoteket and/or HuleEdu-approved
  Gateway plumbing; the browser never receives Sir Convert service credentials.
- Public artifacts are direct-download only, TTL-bound, and not recoverable
  through Vault/MyFiles or owner history.
- Abuse controls mirror `ST-32-03`: public namespace, payload caps, MIME/type
  validation, rate limits, concurrency limits, request-time budgets, reason
  codes, privacy-safe telemetry, and no owner-scoped references.

### Authenticated Lane

- Product entry is the authenticated `documents.conversion_hub` app.
- Skriptoteket submits user-originated jobs through HuleEdu Gateway
  `/sir-convert/v2/convert/...`; the downstream Sir Convert routes remain
  `/v2/convert/...`.
- The flow supports `.dxe` upload, optional sanitized graded result PDF, target
  selection, deterministic job polling, result retrieval, artifact manifest
  listing, named artifact download, and save-to-user-files.
- The local product boundary remains Skriptoteket-owned: teacher-visible job
  ids, ownership checks, file-save metadata, and UI state do not depend on raw
  upstream job ids as the authorization boundary.

## Initial PR Slices

1. Public-profile and route-contract freeze (`PR-0319`, done):
   implemented the `ADR-0085` scoped registry/profile authority and froze the
   public Exam Converter route namespace, limit taxonomy, target vocabulary,
   artifact-manifest mapping, and no-runtime-conversion boundary. Retained
   review `REV-PR-0319` is approved.
2. Authenticated adapter slice (`PR-0318`, done):
   cut `documents.conversion_hub` exam migration calls to the HuleEdu
   `/sir-convert/v2/convert/...` edge, preserving idempotency, correlation,
   named artifacts, and save-to-user-files metadata. Retained review
   `REV-PR-0318` is approved after the Gateway base URL, local proxy, and
   blocked-artifact parser findings were resolved.
3. Public active-runtime metadata and grant contract (`PR-0321`, done and
   approved by `REV-PR-0321`):
   consumed the completed HuleEdu/Sir Convert public grant lane, governed the
   `runtime_status` transition beyond `contract_only`, defined active public
   action affordances, and specified the server-side grant/read-lease adapter
   boundary before runtime code ships. `REV-PR-0321` accepts completed Sir
   Convert `TASK-291` plus the updated Sir Convert contracts as upstream
   approval evidence for the bridge.
4. Public one-time runtime lane (`PR-0320`, done):
   added the backend public runtime and minimal public host wiring for
   transient upload/job/artifact state, browser-backed progress, direct
   downloads, short TTL, anonymous limits on each public action, cookie parity,
   and no Vault/MyFiles or recoverable job surface. The browser receives only
   Skriptoteket public handles and local artifact download URLs; HuleEdu grant
   and Sir Convert artifact-read authority remain server-side.
5. Live upstream public-grant proof slice (`PR-0322`, done and approved by
   `REV-PR-0322`):
   HuleEdu `TASK-0565`, Sir Convert `TASK-292`, and Skriptoteket `PR-0323`
   resolved the earlier grant/read-lease drift. The approved proof exercised
   submit, poll, result, artifact manifest, named download, cookie parity,
   invalid target, missing `.dxe`, unsupported public root, missing job
   artifact manifest, anonymous rate limiting, expired public grants,
   no-account-persistence, and forbidden browser-authority grep across local
   live HuleEdu Gateway, Sir Convert, and Skriptoteket services.
6. Authenticated end-to-end proof slice (`PR-0324`, blocked by
   `REV-PR-0324`):
   the first proof preflight hit the slice's stop condition. The authenticated
   `documents.conversion_hub` host currently lacks a bespoke Exam Converter
   surface, the authenticated runtime API is still the generic Conversion Hub
   route set, and save-to-user-files is not wired for downloaded Sir Convert
   named artifacts.
7. Authenticated runtime UI and save remediation (`PR-0325`, implemented):
   added the authenticated Exam Converter host/runtime/save surface needed for
   `PR-0324` to prove submit, poll, result, artifact manifest, named download,
   save-to-user-files, missing-auth rejection, Gateway-only product traffic,
   and shared artifact taxonomy parity.
8. Authenticated LLM-enrichment consumer sync (`PR-0326`, done):
   added the two-pass reviewed-completion consumer flow behind auth. The first
   submit requests advisory local-LLM suggestions only, the teacher reviews AI-
   suggested facit explicitly in the right panel, reviewed suggestions become
   `reviewed_completion_answer_key` overlay entries, and the second submit
   applies that overlay through Sir Convert before PDF/QTI readiness can change.
9. Authenticated internal-browser UI inspection lane (`PR-0327`, done):
   added the governed dev/test-only fixture lane required for live Exam
   Converter UI inspection in the Codex internal browser. The lane renders real
   authenticated components after normal HuleEdu login, covers representative
   post-conversion states without unsupported file upload, guards fixture access
   out of production builds, and records desktop plus narrow-laptop
   navigator/inspector layout proof.
10. Advisory idempotency rerun (`PR-0328`, done):
   fixed the live `paunchygent@gmail.com` proof blocker where the authenticated
   UI replayed stale Sir Convert job `jobv2_c93420ae30f441cc8e4013cd2d`.
   Provider-only advisory failures now surface an explicit teacher retry action
   that changes only the client idempotency digest via a bounded
   `advisoryRetryAttempt`, preserves the same `.dxe` bytes and Sir Convert job
   spec, keeps retry state browser-runtime local, and does not automatically
   retry or expose provider/idempotency internals in the UI.
11. Reviewed AI-facit handoff (`PR-0329`, done):
   implemented the remaining authenticated UI handoff after the Task 320 live
   proof showed Qwen vision and the Sir Convert advisory report are working.
   The UI now renders valid `gap_fill` AI-facit suggestions as reviewable
   Lucktext rows, submits accepted suggestions as
   `reviewed_completion_answer_key` overlay entries through the second reviewed
   apply job, and proves file readiness is reloaded from the second Sir Convert
   bundle rather than from the first advisory job.
12. Small-screen AI-facit review layout strategy (`PR-0330`, ready):
    defines the phone layout as a separate reduced companion workflow below
    `768px`, keeps tablet/narrow-laptop on its own navigator/detail
    composition, and preserves desktop table/detail behavior. The strategy
    exists because the phone screenshot showed the `PR-0329` action panel and
    review surface inheriting a tablet/narrow-laptop grid instead of switching
    to a phone-specific branch.
13. Reviewed AI-facit contract and affordance reconciliation (`PR-0331`,
    in progress):
    captures the current blocker where teachers can approve AI-suggested keys
    and later create/download PDF/QTI artifacts where those accepted keys have
    been removed or omitted, while teacher-facing artifacts expose internal
    fallback text such as
    `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.`
    The first cleanup slice now prevents a reviewed apply bundle with effective
    keys from being re-projected as source-missing state and blocks the
    source-only accepted-current-state overwrite path. Remaining proof must
    inspect target readiness and downloaded PDF/QTI artifacts before UI labels
    or phone layouts can safely promise export readiness.
14. Teacher-owned correction overlay contract (`PR-0332`, in progress):
    separates the broader teacher edit workflow from `PR-0331`. It must map and
    implement source-bound correction overlays for stems/prompts, points, choice
    keys, and gapped/open-cloze accepted values. `ADR-0086` is accepted, Sir
    Convert Tasks 322/323 have landed, Sir Convert Task 333 and HuleEdu
    TASK-0567 now gate unified non-matching continuation, and matching remains
    blocked until Sir Convert Task 332 provides a real matching-capable
    producer.

## Notes

- The story intentionally changes the earlier `Conversion Hub remains
  authenticated-only` planning posture. That change must be made explicitly in
  docs and registry/profile code before public endpoints ship.
- Public and authenticated lanes should feel like one teacher product, not two
  unrelated APIs. The difference is persistence and authority, not conversion
  semantics.
- Exam.net PDF-to-QTI/DOCX authoring is adjacent but not in this first story
  unless Sir Convert exposes a governed artifact contract for those targets.
