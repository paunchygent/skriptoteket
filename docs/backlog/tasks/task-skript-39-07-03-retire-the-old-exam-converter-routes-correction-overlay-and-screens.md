---
type: task
id: TASK-SKRIPT-39-07-03
title: Retire the old exam converter routes, correction overlay and screens
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - After the redesigned workspace offers the DigiExam import, the signed-in old exam converter routes, its correction sessions, correction overlay and screens are removed, the public guest exam converter stays, and no route or test refers to the removed code
story: ST-SKRIPT-39-07
backlog_document_profile: contract-derived
---

## Implementation Contract

Once DigiExam exams import into the exam workspace (TASK-SKRIPT-39-07-01),
get answer keys through its suggestion lane (TASK-SKRIPT-39-07-02) and the
redesigned workspace offers the DigiExam entry (TASK-SKRIPT-40-04-03), the
signed-in old exam converter has no remaining job. Under G21, G27 and E16 its
routes, correction overlay, correction sessions and screens retire. This task
removes them. The public guest exam converter (ADR-SKRIPT-0085) stays (R4).

This task starts only after TASK-SKRIPT-40-04-03 ships the DigiExam entry in
the `Öppna` drawer.

Removal rule: a module, route, table or file is removed when it belongs only to
the old converter and no remaining code imports or calls it. Anything the
workspace, the document converter, the transcript host or a kept public
surface still uses stays, or moves to a neutral home when its current
location names the old converter.

Signed-in old converter, removed (verified 2026-10-17):

- Routes in `src/skriptoteket/web/api/v1/apps_conversion_hub.py` under
  `/api/v1/apps/documents.conversion_hub/exam-converter/`: `POST conversions`, `GET jobs/{job_id}/result`, `GET jobs/{job_id}/artifacts`,
  `GET jobs/{job_id}/artifacts/{artifact_key}`, `POST jobs/{job_id}/artifacts/{artifact_key}/save`, `GET jobs/{job_id}/source-state`, `POST jobs/{job_id}/replay`.
- Correction sessions: the routes in
  `src/skriptoteket/web/api/v1/apps_conversion_hub_correction_sessions.py`
  (`GET`, `PUT` and `DELETE` on `exam-converter/jobs/{job_id}/correction-session`
  and its `intents`), the handler
  `application/curated_apps/handlers/exam_converter_correction_sessions.py`,
  `application/curated_apps/exam_converter_correction_sessions.py`,
  `protocols/exam_converter_correction_sessions.py`,
  `infrastructure/repositories/exam_converter_correction_sessions.py`, the
  model `infrastructure/db/models/exam_converter_correction_session.py` and its
  tables `exam_converter_correction_sessions` and
  `exam_converter_correction_intents`, dropped by a new migration.
- Conversion and product handlers:
  `application/curated_apps/handlers/exam_converter_conversions.py`,
  `application/curated_apps/handlers/exam_converter_product.py` and their
  wiring in `src/skriptoteket/di/exam_converter.py`.
- Correction overlay and the old DigiExam answer-key lane: the
  `digiexam_ingestion_overlay*`, `digiexam_effective_item_patch`,
  `digiexam_point_correction` domain modules,
  `application/curated_apps/exam_conversion_correction_source.py`,
  `exam_conversion_review_artifacts.py`,
  `handlers/exam_answer_key_enrichment_dxe_lane.py` and the `dxe` value of
  `ExamAnswerKeySourceKind` (today also the field default on
  `ExamAnswerKeyEnrichmentJob`), each under the removal rule.
- Frontend: the `/apps/exam-converter` route and the dev-only
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/:fixtureId`
  route in `frontend/apps/skriptoteket/src/router/routes.ts`,
  `views/apps/ExamConverterAuthenticatedView.vue` and its specs,
  `views/apps/exam-converter-authenticated/`, the old-converter parts of
  `views/apps/exam-converter/`, `api/examConverterLocal.ts`,
  `api/examConverterCorrectionSessions.ts`, and the `exam-converter-authenticated`
  entry in `components/help/helpTopicCatalog.ts`.

Kept or moved, because other code uses them (verified 2026-10-17):

- `views/apps/exam-converter/browserDownload.ts`: used by
  `useExamWorkspaceExports.ts`, the document converter and
  `ConversionHubTranscriptHost.vue`; it moves to a neutral location.
- `ConversionHubTranscriptHost.vue`: rendered today by
  `ExamConverterAuthenticatedView` in transcript mode; it stays.
- DigiExam parser, IR and every `digiexam_*` module the workspace imports
  (`examnet_qti_export.py`, `examnet_pdf_export.py`, `answer_key_prompts.py`,
  `answer_key_view.py`, `docx_ai_schema.py` and the DOCX build handlers import
  `digiexam_*` modules) and `parse_source_exam`, which TASK-SKRIPT-39-07-01
  uses.
- The generic Conversion Hub job routes (`GET routes`, `POST jobs`,
  `GET jobs/{job_id}`, `GET jobs/{job_id}/artifact`): the old converter
  frontend calls `GET jobs/{job_id}`; whether other callers exist is not yet
  verified, so they stay unless the task proves no other caller.

Entry points that open the old converter today and need a new target. They
point to the exam workspace, the main exam conversion and editing app (E16),
unless TASK-SKRIPT-40-04-02 or TASK-SKRIPT-40-04-03 has already changed them:

- The home `Provhantering` card (`components/home/homeWorkApps.ts`, used by
  `LandingAuthenticatedPreview.vue`) links to `/apps/exam-converter`.
- The authenticated host for `documents.conversion_hub` in
  `views/curatedAppHostRegistry.ts` loads `ExamConverterAuthenticatedView`, so
  `/apps/documents.conversion_hub` opens the old converter.

Kept: the public guest exam converter (ADR-SKRIPT-0085) stays with its routes
and modules; a later decision covers it (R4). Its surfaces:

- `POST /api/v1/public/apps/documents.conversion_hub/exam-converter/jobs` and
  its status, result, artifact and download routes in
  `web/api/v1/public_apps_exam_converter.py`; the exam-converter capability
  constants in `web/api/v1/public_apps.py`; the `exam_converter` public
  capability on `documents.conversion_hub` in
  `infrastructure/curated_apps/registry.py`.
- `application/curated_apps/public_exam_converter*.py`,
  `handlers/public_exam_converter_jobs.py`, `protocols/public_exam_converter.py`,
  `infrastructure/repositories/public_exam_converter_jobs.py` and the
  `public_exam_converter_jobs` table.
- Frontend `views/apps/ExamConverterPublicView.vue`,
  `views/apps/exam-converter-public/` and the public host entry in
  `views/curatedAppHostRegistry.ts`, reached through
  `/public/apps/documents.conversion_hub/exam-converter`.

Out of scope: any new workspace UI (G2), layout work on the old views (E16),
and the public guest exam converter (R4).

## Contract Inputs

- Story ST-SKRIPT-39-07 terms S1-S7; TASK-SKRIPT-39-07-01 and
  TASK-SKRIPT-39-07-02 done; TASK-SKRIPT-40-04-03 shipped with the DigiExam
  entry.
- Old converter surfaces as listed above; ADR-SKRIPT-0087 (correction
  sessions) and ADR-SKRIPT-0085 (public conversion exception), both
  `accepted`.
- Migrations that touch the removed tables:
  `migrations/versions/9b2f4c6d8e10_exam_converter_correction_sessions.py` and
  `migrations/versions/b3e7a1c9d4f2_remove_review_decision_correction_intents.py`.
- 27 test files under `tests/` refer to the old converter, its correction
  sessions, the public converter or the `dxe` lane (grep on 2026-10-17).

## Core Vertical And Performance

After removal, a teacher who opens `Provhantering` from home or the catalog
lands in the exam workspace and imports a DigiExam export from the `Öppna`
drawer. `/apps/exam-converter` and the authenticated `exam-converter` API
routes no longer exist, the correction-session tables are dropped, and the
workspace, document converter, transcript host and public guest exam converter
behave as before.

## Validation

- Focused backend tests for the remaining Conversion Hub and workspace routes
  that touched the removed code, and a test that the new migration drops
  the correction-session tables.
- Focused frontend tests: router specs for the removed and retargeted routes,
  the home card and host registry targets, and the specs of the modules that
  import the moved download helper.
- A grep over `src/` (excluding the built bundles under
  `src/skriptoteket/web/static/spa/`), `frontend/apps/skriptoteket/src/` and
  `tests/` shows no reference to the removed code; what the removal rule keeps
  for the public guest exam converter stays.
- Hemma staging browser walk: `Provhantering` from home opens the exam
  workspace; `/apps/exam-converter` no longer opens a converter; a DigiExam
  import from the `Öppna` drawer, the document converter, a workspace export
  and the public guest exam converter still work.

## Stop Conditions

- TASK-SKRIPT-40-04-03 has not shipped the DigiExam entry: do not start.
- ADR-SKRIPT-0087 (correction sessions) is `accepted` while this task removes
  the correction sessions: the implementer reconciles it through a docs update
  in this task before closeout.
- A listed module turns out to be used by the workspace, the document
  converter, the transcript host or a kept public surface: keep it and report
  it.
- `ConversionHubTranscriptHost` has no route or host other than
  `ExamConverterAuthenticatedView`: stop and report before removing that view;
  where transcript mode lives afterwards is a user decision.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R1  | The separate DigiExam converter views get no layout work and retire when ST-SKRIPT-39-07 lands; the exam workspace is the main exam conversion and editing app (EPIC-SKRIPT-39 E16, user 2026-10-12).                                                                                                        |
| R2  | The old correction overlay, correction sessions and their routes retire with the old converter (G21, user 2026-10-17).                                                                                                                                                                                       |
| R3  | The DigiExam entry in the Öppna drawer is built by ST-SKRIPT-40-04; this story ships no workspace UI (G2, user 2026-10-17).                                                                                                                                                                                  |
| R4  | The public guest exam converter (ADR-SKRIPT-0085) stays with its routes and modules; this story retires only the signed-in old converter, its correction overlay and correction sessions; a later decision covers the guest converter (user 2026-10-17, G27).                                                |
| R5  | Transcript mode leaves the old converter: `ConversionHubTranscriptHost` mounts directly on `/apps/audio-transcription`, the home transcript card stays `unavailable`, and `ExamConverterAuthenticatedView` is removed with the rest (user decision 2026-10-18, option (a) of the transcript stop condition). |

## Progress

- 2026-10-18, first commit (parent request, for an early staging rebuild): the
  home `Provhantering` card links to `/apps/exam-workspace`, and the signed-in
  `documents.conversion_hub` host opens the exam workspace; the public guest
  host is unchanged. The removals follow.
- 2026-10-18, removal commit: the signed-in `exam-converter` API routes, the
  correction-session routes, handlers, protocol, repository, model and domain
  module, the old conversion and product handlers, the correction overlay
  modules (`digiexam_ingestion_overlay*`, `digiexam_effective_item_patch`,
  `digiexam_point_correction`), `exam_conversion_correction_source.py`, the
  `dxe` enrichment lane and source kind, and the machine-proposed overlay
  records are removed. Migration `e8a3c5f1b7d2` drops
  `exam_converter_correction_sessions`, `exam_converter_correction_intents` and
  `exam_answer_key_proposed_overlays`, deletes `dxe` enrichment jobs, and drops
  `exam_answer_key_enrichment_jobs.conversion_job_id`, the `source_kind`
  default and `conversion_hub_jobs.submission_idempotency_key`; these became
  unused once the old converter was gone. The frontend old converter view, its
  modules, API clients, routes and help entry are removed;
  `/apps/audio-transcription` mounts `ConversionHubTranscriptHost` (R5).
  `browserDownload.ts` moved to `frontend/apps/skriptoteket/src/utils/`; the
  upload panel and target types moved into `views/apps/exam-converter-public/`.
  ADR-SKRIPT-0087 is superseded.
- Kept under the removal rule, because the public guest exam converter uses
  them: `InProcessExamConversionProducer` (now with only the public inputs) and
  `exam_conversion_review_artifacts.py` (public bundle and manifest). The
  generic Conversion Hub job routes stay: no frontend caller exists, but the
  document converter and transcript lanes share their `conversion_hub_jobs`
  handlers, so removing them is a separate decision.
- One public bundle change: the manual-follow-up `qti_validation_report_v1`
  inside the public bundle no longer carries `"retry_identity": null`; only the
  removed dxe lane set it, and no reader uses it.

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Work on main through merge `fc5b317d` (2026-10-18, guest converter polling and the missing-key notice `aff91a7e`, `31bd9b62`). No review verdict is recorded here.
- Owed: the Validation suites and the Hemma staging walk are not recorded as run; then closeout. The public guest converter that this task kept is removed by TASK-SKRIPT-41-02-03 (user ruling 2026-10-20).
