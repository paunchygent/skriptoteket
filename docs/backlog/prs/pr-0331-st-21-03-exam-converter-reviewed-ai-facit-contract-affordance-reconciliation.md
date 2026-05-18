---
type: pr
id: PR-0331
title: "ST-21-03 Exam Converter reviewed AI-facit contract and affordance reconciliation"
status: ready
owners: "Codex"
created: 2026-05-17
updated: 2026-05-18
stories:
  - "ST-21-03"
tags:
  - frontend
  - ux
  - authenticated
  - conversion-hub
  - sir-convert
  - reviewed-completion
  - artifact-contract
acceptance_criteria:
  - "Given a teacher explicitly accepts AI-suggested keys, when any later create-files, approve-current-state, download, save, or re-export path runs, then those accepted suggestions are never discarded, overwritten by source-only fallback state, or silently omitted from the reviewed apply evidence."
  - "Given a teacher accepts one or all valid AI-facit suggestions, when Skriptoteket submits the reviewed apply job, then retained proof shows the submitted overlay contains exactly the accepted `reviewed_completion_answer_key` entries with source binding and candidate lineage."
  - "Given the reviewed apply job returns, when Skriptoteket reloads artifacts, then the UI derives question state, missing-facit counts, file readiness, and download/save affordances from the reviewed apply job bundle, including `effective_ir_json` where present."
  - "Given accepted AI-facit suggestions are expected to unlock reviewed keyed export, when downloaded PDF or QTI artifacts are inspected, then retained proof shows all accepted keys are present for choice, matching, and gapped/open-cloze shapes; PDF may render gapped items as free text only when the accepted gapped key values are still included."
  - "Given teacher-facing artifacts are produced, when the PDF, QTI package, or import-facing content is inspected, then no internal fallback diagnosis such as `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.` appears in the exported artifact."
  - "Given Files is visible before, during, and after review, when a target is unavailable, then the UI shows a teacher-actionable explanation and never leaks raw producer reason codes such as `unsupported_target_shape` as primary copy."
  - "Given the screen has both accepted-current-state review and AI-facit review paths, when the teacher sees action buttons, then the labels, grouping, and enabled states make clear which action only records local review decisions and which action submits a reviewed apply job that can create new files."
  - "Given this task records local cleanup evidence, when it is evaluated for completion, then final acceptance requires a durable live Playwright proof against the authenticated Skriptoteket/HuleEdu public edge and Hemma Sir Convert runtime."
---

# PR-0331: ST-21-03 Exam Converter Reviewed AI-Facit Contract And Affordance Reconciliation

## Problem

The current authenticated Exam Converter flow has two intertwined problems:

1. The teacher-facing affordances are confusing. Local AI-facit selection,
   reviewed apply, Files-tab actions, and the older current-state export action
   all appeared close together, but they did not have the same effect.
2. The reviewed AI-facit contract is not proven end to end. A user can approve
   suggested keys, create files, and later download artifacts that still appear
   to lack trusted answer keys.
3. Internal fallback/diagnostic text has leaked back into teacher-facing
   exported artifacts, even though previous product direction forbade exposing
   internal parser/rendering issues in user-facing output.

The worst failure is that the teacher's explicit acceptance of AI-suggested
keys appears to be removed somewhere after approval. The product contract must
treat an accepted AI suggestion as durable reviewed teacher intent for that
conversion path until the teacher changes it or the upstream service rejects it
with a visible, actionable reason. It must not disappear into source-only
fallback export.

User-supplied evidence from 2026-05-17 shows the problematic sequence:

- The old AI-facit banner put review, bulk selection, and file creation in the
  same row, while the question list still showed `Facit` missing for the
  key-bearing items.
- The Files tab can show partial export state and raw producer reason text such
  as `Orsak: unsupported_target_shape`.
- After an additional approve/export step, the Files tab can show both PDF and
  QTI as export-ready, but the downloaded artifacts do not prove that reviewed
  AI-facit keys were applied.

This is not a layout problem and it is not an outside designer task.
`PR-0330` owns the separate small-screen layout strategy. `PR-0331` is a
Codex-owned engineering task for reviewed-key plumbing, exported artifact
integrity, and action semantics needed to prove accepted AI suggestions survive
the conversion flow.

## Current Evidence

Downloaded artifacts supplied by the user:

- `/Users/olofs_mba/Downloads/examnet-import (1).pdf`
- `/Users/olofs_mba/Downloads/qti-package (1).zip`

Local inspection on 2026-05-17 found:

- `pdfinfo` reports `examnet-import (1).pdf` as a six-page WeasyPrint PDF.
- `pdftotext` shows the key-bearing questions are exported as `Typ: Fritext`
  with `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade
  värden.` or equivalent manual/free-text wording. This text is not acceptable
  artifact copy; it exposes internal fallback state and coincides with the
  accepted AI keys being absent from the exported artifact.
- `unzip -l` shows `qti-package (1).zip` contains `imsmanifest.xml`,
  `items/item_001.xml` through `items/item_008.xml`, and one image resource.
- Sampled QTI items do not contain `correctResponse` declarations. Lucktext
  items such as `item_001` and `item_005` use
  `<responseDeclaration identifier="RESPONSE" cardinality="single"
  baseType="string" />` plus `extendedTextInteraction`; `item_002` has a
  choice interaction but no declared correct alternatives.

The pre-cleanup code path also pointed to a projection mismatch:

- `useExamConverterAiFacitReview.ts` builds
  `reviewed_completion_answer_key` overlay items for accepted candidates.
- `useExamConverterReviewArtifacts.ts` loads optional `effective_ir_json` and
  parses `effectiveAnswerKeysByItem`.
- `digiexamIrReviewParser.ts` stores `effectiveAnswerKeysByItem` on the final
  projection, but the question rows are still projected only from the source IR
  plus advisory candidates.
- `digiexamIrQuestionReviewProjection.ts` derives missing `Facit` from manual
  follow-ups and does not consider effective answer keys from the reviewed
  apply bundle.
- `ExamConverterFilesReadinessList.vue` mapped a few reason codes to Swedish
  labels but fell back to raw `Orsak: ${reasonCode}` for unknown producer
  reasons before the second cleanup slice removed that fallback.

This means the UI can plausibly submit reviewed keys while still rendering the
post-apply bundle as if the original source IR were the only answer-key truth.
If the produced artifacts also lack keys, the producer handoff has drifted as
well; this slice must distinguish those cases with retained proof.

## Root-Cause Map

The starting root-cause analysis lives in:

- `docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md`

Current working diagnosis: bulk AI-facit selection and reviewed apply can build
and submit reviewed-completion overlay entries, but the post-apply Skriptoteket
projection still treats source-IR missing-facit state as current truth because
it does not consume `effective_ir_json` answer keys for question rows,
missing-facit counts, or accepted-current-state eligibility. That can expose
the current-state export path after reviewed apply. When used, that path
submits a new source-evidence/current-state overlay containing only
`review_decision` entries, not the prior `reviewed_completion_answer_key`
entries. Downloads then point at the later manual-unkeyed job, making the
teacher-approved AI suggestions disappear from the final artifacts.

## Implementation Progress

Initial cleanup started on 2026-05-17:

- focused frontend regression coverage now keeps source `ir_json` and
  `migration_manifest` immutable after reviewed apply, while the reviewed keys
  exist only in `effective_ir_json`;
- reviewed `effective_ir_json` keys are projected back into question rows so a
  reviewed `Lucktext` row no longer shows missing `Facit` or an AI-suggestion
  robot icon after apply;
- accepted-current-state approval is no longer offered from a reviewed apply
  bundle that contains effective answer keys, preventing the source-only
  `review_decision` overlay from replacing teacher-approved AI keys; and
- this does not close the full task. The remaining proof must still inspect the
  produced PDF/QTI artifacts and distinguish Skriptoteket projection drift from
  any Sir Convert target-renderer drift.

Second cleanup slice on 2026-05-17:

- removed the raw `Orsak: ${reasonCode}` fallback from the Files tab; known
  target blocker families now map to Swedish teacher-facing copy and unknown
  producer codes fall back to a generic teacher-facing message without exposing
  the code;
- removed generic approval language from the current-state export gate. That
  path now says `Skapa filer` and keeps the missing-facit consequences in
  adjacent status/help copy;
- removed generic approval language from AI-facit actions.
  Candidate decisions now say `Använd förslag`, bulk selection says
  `Använd alla förslag`, and the reviewed apply submit says
  `Skapa filer med facit`;
- added focused regression coverage that raw producer reason codes such as
  `unsupported_target_shape` and `qti_package_export_disabled` do not render in
  the teacher UI; and
- retained artifact inspection still shows the user-supplied PDF/QTI output is
  manual-unkeyed and lacks QTI `correctResponse`, but that evidence came from
  the pre-cleanup flow. The remaining producer proof must rerun or inspect a
  corrected reviewed-apply path before assigning renderer drift upstream.

## 2026-05-17 Correction Boundary

This section records the corrections and cleanup boundaries from the
2026-05-17 user review. It is not a decision record. Product decisions belong
in ADRs; broader execution work belongs in independent PR-sized backlog items.

1. `PR-0331` does not govern the full teacher-edit product contract for stems,
   prompts, answer keys, points, or teacher-authored item corrections. Earlier
   wording that treated teacher edit as a `PR-0331` product decision is docs
   drift. The independent authority is now:
   - proposed ADR:
     `docs/adr/adr-0086-exam-converter-teacher-owned-correction-overlay-boundary.md`;
   - independent PR slice:
     `docs/backlog/prs/pr-0332-st-21-03-exam-converter-teacher-owned-correction-overlay-contract.md`.
2. The old `Lämna` action was a bad label and a weak contract. It mapped to
   local-only `left_manual` state, was omitted from the reviewed-completion
   overlay, did not submit a rejected or manual-state decision to Sir Convert,
   and did not create artifacts. That fake reject branch is removed from the
   active UI/state path. Rejected suggestions and global rejection must be added
   only as an explicit, source-backed contract that cannot branch into confusing
   follow-up actions before PDF/QTI generation.
3. If corrected reviewed-apply proof shows `effective_ir_json` contains choice,
   matching, or gapped/open-cloze keys but PDF/QTI artifacts omit them, this is
   not a downstream warning-only state. The fix belongs at the source of the
   omission, including Sir Convert producer code when producer proof identifies
   the target adapter or renderer as the source.

## Goal

Make the reviewed AI-facit workflow coherent and provable:

- accepted suggestions become reviewed overlay entries;
- the reviewed apply submit sends the expected overlay and job spec;
- the second bundle is the only source for post-apply file readiness;
- `effective_ir_json` answer keys are either consumed by the UI or proven
  absent upstream;
- downloaded PDF/QTI artifacts are inspected for the expected reviewed keys;
- accepted AI-facit decisions survive every subsequent create/export path or
  fail visibly before artifact download;
- exported artifacts contain teacher-facing content only, not internal
  fallback diagnostics;
  and
- action labels and grouping tell the teacher what each step actually does.

## Non-goals

- No phone layout implementation or breakpoint strategy. That remains
  `PR-0330`.
- No new local answer-key inference in Skriptoteket.
- No automatic application of advisory candidates without teacher action.
- No provider/model/runtime changes in Skriptoteket.
- No teacher-owned correction editor, prompt/stem editor, point editor, or
  independent teacher-authored answer-key overlay. Those are governed by
  `ADR-0086` and `PR-0332`, not by `PR-0331`.
- No local workaround that weakens the target contract. If producer evidence
  proves reviewed keys are present in `effective_ir_json` but a PDF/QTI adapter
  drops choice, matching, or gapped/open-cloze keys, this slice must record the
  drift with request/response/artifact evidence and route the fix to the correct
  Sir Convert producer surface.
- No exposure of provider names, raw prompts, raw service reason codes, Docker
  details, idempotency internals, parser fallback diagnostics, credentials,
  student answers, or scores in teacher-facing UI or generated artifacts.

## Implementation Plan And Status

1. Done locally: reproduce the destructive source-only overwrite path in
   focused frontend tests. The regression fixture keeps source `ir_json` and
   `migration_manifest` source-missing after reviewed apply, while reviewed
   keys exist only in `effective_ir_json`.
2. Done locally: add reviewed-apply projection coverage. Question rows now
   consume reviewed effective keys, suppress stale missing `Facit` state for
   reviewed items, and avoid re-offering accepted-current-state approval as if
   the reviewed bundle were still source-missing.
3. Done locally: reconcile action labels and remove local-only fake reject
   behavior. Active UI language now distinguishes local AI-facit selection
   (`Använd förslag`, `Använd alla förslag`) from reviewed apply submit
   (`Skapa filer med facit`), and the old `Lämna` / `left_manual` branch is no
   longer active UI/state code.
4. Done locally: remove raw producer reason-code leakage from the Files tab.
   Known target blockers map to Swedish teacher-facing copy, and unknown
   producer codes fall back to generic teacher-facing copy without rendering
   raw enum values.
5. Done locally: verify the current Sir Convert v2 generated consumer surface
   from the current producer snapshot. A fresh `openapi-typescript` generation
   on 2026-05-17 produced no diff against
   `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`, and the file
   contains the reviewed-completion lineage and overlay fields.
6. Done locally: add durable Playwright live-proof coverage in
   `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`, backed by
   `scripts/_pr_0331_reviewed_ai_facit_artifacts.py` and the retained script
   surface allowlist in `tests/unit/scripts/test_playwright_script_surface.py`.
   The proof logs in through the HuleEdu browser-session ceremony, uploads the
   governed DigiExam `.dxe`, records redacted Sir Convert request/response
   evidence, and, when suggestions exist, inspects `effective_ir_json`, PDF,
   and QTI output.
7. Done: harden the live proof harness so it cannot satisfy `PR-0331` with
   stale AI suggestions. The script now overrides Sir Convert POST
   idempotency keys per proof run, records `idempotent_replay`, and uses the
   Playwright request context for public-edge artifact fetches so retained
   `effective_ir_json` and `ingestion_overlay_report` evidence is not blocked
   by browser route/CORS behavior.
8. Done: complete the durable Hemma/public proof after Sir Convert commit
   `166fea9140ac2e5709aa30f5b432ffe1e53fe2c3` fixed OpenAI Responses vision
   image URLs. Retained proof in
   `.artifacts/playwright-pr-0331-reviewed-ai-facit-live/20260518T192044Z/`
   shows both POSTs were fresh (`idempotent_replay=false`), reviewed overlay
   accepted four suggestions (`item-001`, `item-002`, `item-003`, `item-013`),
   `effective_ir_json` retained reviewed choice and gap-fill lineage, PDF/QTI
   files unlocked and downloaded, exported artifacts contained no forbidden
   diagnostic text, and QTI retained correct responses.

## Test Plan

Focused frontend and artifact-contract coverage:

```bash
pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run python -m py_compile scripts/playwright_pr_0331_reviewed_ai_facit_live.py scripts/_pr_0331_reviewed_ai_facit_artifacts.py
pdm run python -m scripts.playwright_pr_0331_reviewed_ai_facit_live --base-url http://127.0.0.1:5173
pdm run python -m scripts.playwright_pr_0331_reviewed_ai_facit_live --base-url https://skriptoteket.hule.education --dotenv .env
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run lint
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Manual/live proof must include:

- a durable Playwright proof script in the sanctioned repo script/test
  location;
- live stack evidence from authenticated Skriptoteket, the HuleEdu auth edge,
  Sir Convert, and the tunneled LLM runtime together;
- retained overlay submit evidence for the reviewed apply job;
- retained evidence that accepted AI suggestions are not reset, overwritten, or
  omitted by later Files/create/approve paths;
- retained second-bundle artifact manifest and `effective_ir_json` evidence;
- retained PDF/QTI inspection evidence from downloaded artifacts;
- retained negative proof that exported artifacts do not expose internal
  fallback diagnostics;
- browser proof that UI copy no longer leaks raw reason codes; and
- proof that exported artifacts preserve accepted reviewed keys or fail with a
  retained upstream contract finding.

The 2026-05-18 Hemma/public proof for the ecology `.dxe` fixture satisfied
these manual/live proof requirements. The final manifest is
`.artifacts/playwright-pr-0331-reviewed-ai-facit-live/20260518T192044Z/manifest.redacted.json`.

## Rollback Plan

Revert only the UI/projection/action-model changes from this slice. Keep the
existing advisory submit, reviewed overlay builder, Gateway client, and Sir
Convert artifact loading intact. If upstream Sir Convert is proven to be the
source of missing reviewed keys, preserve the failing proof and create the
producer task rather than downgrading the UI to pretend reviewed keys were
exported.
