---
type: task
id: TASK-SKRIPT-41-02-03
title: The public guest DigiExam converter line is removed
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: in_progress
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-21'
task_kind: story
acceptance_criteria:
  - The public guest DigiExam jobs table, routes, worker, artifacts, planner, PDF builder, QTI adapter and view are removed with no remaining reference
  - DigiExam parsing is reached only through the workspace import
  - TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 are closed as superseded
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Remove the public guest DigiExam line under ST-SKRIPT-41-02 P6 once the guest URL opens the public workspace (TASK-SKRIPT-41-02-02). Removal rule: a module, route, table or file goes when only the guest line uses it and nothing else imports or calls it; `parse_source_exam`/`DigiExamDxeParser` stay for the workspace import. Generic Conversion Hub `.dxe` intake (`apps_conversion_hub.py`) goes too if no caller uses it.

## Contract Inputs

- ST-SKRIPT-41-02 P6; ADR-SKRIPT-0085; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- Guest-only modules: `public_exam_converter_jobs.py`, `public_exam_converter_local_execution.py`, `public_exam_converter_artifacts.py`, `exam_conversion_review_artifacts.py`, `digiexam_answer_key_completion.py`, `digiexam_examnet_qti_adapter.py`, `digiexam_examnet_pdf.py`, `workers/public_exam_converter.py`, table `public_exam_converter_jobs`, `ExamConverterPublicView.vue` and `views/apps/exam-converter-public/`.

## Core Vertical And Performance

The vertical is deletion plus one migration dropping `public_exam_converter_jobs`; the workspace DigiExam import keeps the parser. No performance concern.

## Validation

- The domain suites for curated apps and web pass; no import or route refers to removed code; migration test.
- Docs: ADR-SKRIPT-0085 marked superseded by EPIC-SKRIPT-41; the three docs of P6 closed; `pdm run docs-validate`.

## Stop Conditions

Stop and report if a removed module turns out to serve another caller, or if the generic hub `.dxe` intake has a live caller.

## Decided Contract Terms

| ID  | Decided contract term                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------ |
| X1  | ST-SKRIPT-41-02 P6 applies as written; no compatibility path or redirect for the old guest job routes. |

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Ready to start: TASK-SKRIPT-41-02-02 is `done`. The user confirmed the removal on 2026-10-20. The old guest DigiExam converter is subsumed by the exam workspace, where DigiExam is one input. The public workspace replaces the old converter as the demo that leads guests to an account. The earlier "guest converter stays" wording in EPIC-SKRIPT-39 and ST-SKRIPT-39-07 S8 now points here.

### Implementation 2026-10-21 (lead, branch codex/task-skript-41-02-03 from 66b3dc8e)

- Removed the guest line: job routes, worker loop, job handlers, local execution,
  artifacts, review artifacts, job store, model and protocol, the in-process
  producer, the Exam.net PDF builder (`digiexam_examnet_pdf`, `_items`, `_assets`),
  the DigiExam-to-QTI adapter, the `PUBLIC_EXAM_CONVERTER_*` settings,
  `ExamConverterPublicView.vue` and `views/apps/exam-converter-public/`.
  Migration `52f2fe74483a` drops `public_exam_converter_jobs`.
- Removed the dead Conversion Hub `.dxe` intake: no route accepted `dxe`, and
  only the guest worker wrote the local bundle store. The hub download branch,
  the bundle store and protocol, `application/curated_apps/exam_conversion.py`,
  the writer's `build_bundle_bytes` and the `dxe`/`examnet_bundle` hub formats
  are gone.
- Kept: `parse_source_exam` (moved with its module to `digiexam_source_parsing.py`)
  and `DigiExamDxeParser` for the workspace import; the Exam.net QTI writer and
  PDF renderer implementations, which `ExamWorkspacePublicProvider.export_renderer` builds for both export paths;
  the `exam_converter` public capability, which gates the public workspace. Its
  bootstrap now carries only scope, profile, frontend route, API namespace and
  runtime status, and takes title and summary from the registry.
- X1: the old guest job routes are unrouted and tested as retired.
- Scope addition (overseer, 2026-10-21 staging walk): `/apps/exam-converter`
  redirects to `/apps/exam-workspace` through one record in the existing
  `CANONICAL_CONVERSION_APP_ROUTES`; a signed-out visitor still goes to login
  with continuation to the workspace. The guest URL
  `/public/apps/documents.conversion_hub/exam-converter` still mounts the public
  workspace.
- Stop condition resolved (overseer decision B, 2026-10-21): the two answer-key
  output specs moved into `exam_workspace/answer_key_prompts.py`, their only
  caller; `digiexam_answer_key_completion.py`, its test and the last guest
  planner test are deleted.
- Closed as superseded: TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 (migrated to the
  current backlog profile); ADR-SKRIPT-0085 marked superseded by EPIC-SKRIPT-41.

### Review repair 2026-10-21 (review `evidence/reviews/review-ef65d98d.md`, retained root 01a15f53)

- F1: removed the unused `ExamNetExportWritersProvider`; the shared export
  renderer is the only composition path for the Exam.net writers.
- F2: removed the result-PDF answer-evidence path, the IR manifest and source
  fingerprint builders, the IR-specific answer-key payload builders and two
  orphaned PDF contracts; tests now assert workspace and intermediate-exam
  outcomes directly.

### Admission 2026-10-21 (Hemma orchestrator)

- Pi ruthless-reviewer `e81a0e99` reviewed `a7f61563..ef65d98d`: changes_requested, two medium findings F1 and F2, no runtime regression (retained root `01a15f53-3b1b-7dcd-8cae-f7e114f55406`, `evidence/reviews/review-ef65d98d.md`).
- Repairs `c204d880` and `bd7a57a7` admitted by the Hemma orchestrator on focused proof without rereview: lint, typecheck, domain/application/web/infrastructure tests, app factory (255 routes) and the removed-name search pass (`evidence/validation/repair-ef65d98d/`).
- Merged to main with `--no-ff` at `e6fee0d0`. Owed: the staging walk (signed-in and signed-out on `/apps/exam-converter`, guest on the `/public/...` converter URL) and the user's answer on where a signed-out visitor on `/apps/exam-converter` goes; then user closure.
